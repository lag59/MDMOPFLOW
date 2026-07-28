"""
AI-powered ticket assignment service.

This service automatically assigns tickets to projects based on location matching.
It uses fuzzy string matching to handle variations in address formatting and location names.
"""

import difflib
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Ticket, Project


class TicketLocationMatcher:
    """Matches ticket destinations to project addresses using fuzzy location matching."""

    # Similarity threshold (0-1) for considering a match
    SIMILARITY_THRESHOLD = 0.70

    # Common location abbreviations and variations
    LOCATION_VARIATIONS = {
        "st": ["street", "st.", "st"],
        "ave": ["avenue", "ave.", "ave"],
        "rd": ["road", "rd.", "rd"],
        "dr": ["drive", "dr.", "dr"],
        "blvd": ["boulevard", "blvd.", "blvd"],
        "ln": ["lane", "ln.", "ln"],
        "ct": ["court", "ct.", "ct"],
        "pl": ["place", "pl.", "pl"],
        "pkwy": ["parkway", "pkwy.", "parkway"],
        "cir": ["circle", "cir.", "cir"],
        "apt": ["apartment", "apt.", "apt", "#"],
        "suite": ["suite", "ste.", "ste", "#"],
        "bldg": ["building", "bldg.", "bldg"],
        "north": ["n", "n.", "north"],
        "south": ["s", "s.", "south"],
        "east": ["e", "e.", "east"],
        "west": ["w", "w.", "west"],
    }

    @staticmethod
    def normalize_location(location: str) -> str:
        """
        Normalize a location string for comparison.
        
        Converts to lowercase, removes extra whitespace, and normalizes common abbreviations.
        """
        if not location:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = location.lower().strip()
        
        # Remove extra spaces
        normalized = " ".join(normalized.split())
        
        return normalized

    @staticmethod
    def extract_address_components(location: str) -> list[str]:
        """
        Extract address components (city, street, etc.) from a location string.
        
        Returns a list of meaningful components.
        """
        normalized = TicketLocationMatcher.normalize_location(location)
        
        # Split by common delimiters
        components = []
        for part in normalized.split(","):
            part = part.strip()
            if part:
                components.append(part)
        
        # If no commas, split by spaces and group into meaningful chunks
        if not components:
            words = normalized.split()
            components = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
        
        return [c for c in components if c]

    @staticmethod
    def calculate_location_similarity(location1: str, location2: str) -> float:
        """
        Calculate similarity between two locations.
        
        Returns a value between 0 and 1, where 1 is an exact match.
        """
        if not location1 or not location2:
            return 0.0
        
        loc1 = TicketLocationMatcher.normalize_location(location1)
        loc2 = TicketLocationMatcher.normalize_location(location2)
        
        # Exact match (after normalization)
        if loc1 == loc2:
            return 1.0
        
        # Check if one is substring of the other
        if loc1 in loc2 or loc2 in loc1:
            return 0.85
        
        # Use difflib for fuzzy matching on full strings
        full_match_ratio = difflib.SequenceMatcher(None, loc1, loc2).ratio()
        
        # Also check component-wise matching
        components1 = TicketLocationMatcher.extract_address_components(location1)
        components2 = TicketLocationMatcher.extract_address_components(location2)
        
        component_matches = 0
        total_components = max(len(components1), len(components2))
        
        if total_components > 0:
            for comp1 in components1:
                for comp2 in components2:
                    # Use sequence matcher on components
                    ratio = difflib.SequenceMatcher(None, comp1, comp2).ratio()
                    if ratio > 0.85:  # High threshold for component match
                        component_matches += 1
                        break
            
            component_similarity = component_matches / total_components
        else:
            component_similarity = 0.0
        
        # Weight the full match and component match
        # Give more weight to full string match but also consider component matching
        final_similarity = (full_match_ratio * 0.6) + (component_similarity * 0.4)
        
        return final_similarity

    @staticmethod
    def find_best_project_match(
        ticket_destination: str,
        projects: list[Project],
    ) -> Optional[tuple[Project, float]]:
        """
        Find the best matching project for a ticket destination.
        
        Returns (project, confidence_score) or None if no good match found.
        """
        if not ticket_destination or not projects:
            return None
        
        best_match = None
        best_score = 0.0
        
        for project in projects:
            if not project.address:
                continue
            
            score = TicketLocationMatcher.calculate_location_similarity(
                ticket_destination, project.address
            )
            
            if score > best_score:
                best_score = score
                best_match = project
        
        # Only return match if above threshold
        if best_score >= TicketLocationMatcher.SIMILARITY_THRESHOLD:
            return (best_match, best_score)
        
        return None


class AITicketAssignment:
    """Main service for AI-powered ticket assignment."""

    @staticmethod
    def auto_assign_unassigned_tickets(
        db: Session,
        tenant_id: str,
        confidence_threshold: float = 0.75,
    ) -> dict:
        """
        Automatically assign unassigned tickets to projects based on location matching.
        
        Args:
            db: Database session
            tenant_id: Tenant ID to process
            confidence_threshold: Minimum confidence score to auto-assign (0-1)
        
        Returns:
            Dictionary with assignment results:
            {
                "total_unassigned": int,
                "assigned": int,
                "assignments": [
                    {"ticket_id": str, "project_id": str, "confidence": float, "match_info": str}
                ],
                "skipped_low_confidence": int,
                "skipped_no_destination": int,
            }
        """
        # Get all unassigned tickets for this tenant
        unassigned_tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.project_id.is_(None),
        ).all()
        
        # Get all active projects for this tenant
        active_projects = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status.in_(["active", "planning"]),
        ).all()
        
        result = {
            "total_unassigned": len(unassigned_tickets),
            "assigned": 0,
            "assignments": [],
            "skipped_low_confidence": 0,
            "skipped_no_destination": 0,
        }
        
        if not active_projects:
            return result
        
        for ticket in unassigned_tickets:
            # Skip if no destination
            if not ticket.destination:
                result["skipped_no_destination"] += 1
                continue
            
            # Find best matching project
            match_result = TicketLocationMatcher.find_best_project_match(
                ticket.destination,
                active_projects,
            )
            
            if not match_result:
                result["skipped_low_confidence"] += 1
                continue
            
            project, confidence = match_result
            
            # Only assign if above threshold
            if confidence < confidence_threshold:
                result["skipped_low_confidence"] += 1
                continue
            
            # Assign ticket to project
            ticket.project_id = project.id
            db.add(ticket)
            
            result["assigned"] += 1
            result["assignments"].append({
                "ticket_id": ticket.id,
                "project_id": project.id,
                "confidence": float(confidence),
                "match_info": f"{ticket.destination} → {project.address}",
            })
        
        # Commit all assignments
        if result["assigned"] > 0:
            db.commit()
        
        return result

    @staticmethod
    def get_project_suggestions_for_ticket(
        db: Session,
        ticket_id: str,
        tenant_id: str,
        top_n: int = 5,
    ) -> list[dict]:
        """
        Get ranked project suggestions for a specific ticket.
        
        Useful for UI to show user the top matching projects for manual confirmation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            tenant_id: Tenant ID
            top_n: Number of top suggestions to return
        
        Returns:
            List of suggestions sorted by confidence score:
            [
                {
                    "project_id": str,
                    "project_name": str,
                    "address": str,
                    "confidence": float,
                    "match_reason": str
                },
                ...
            ]
        """
        # Get the ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == tenant_id,
        ).first()
        
        if not ticket or not ticket.destination:
            return []
        
        # Get all active projects
        projects = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status.in_(["active", "planning"]),
        ).all()
        
        # Score all projects
        scores = []
        for project in projects:
            if not project.address:
                continue
            
            score = TicketLocationMatcher.calculate_location_similarity(
                ticket.destination,
                project.address,
            )
            
            if score > 0.5:  # Include even lower confidence for suggestions
                scores.append({
                    "project_id": project.id,
                    "project_name": project.project_name,
                    "address": project.address,
                    "confidence": float(score),
                    "match_reason": f"Location match: {ticket.destination} similar to {project.address}",
                })
        
        # Sort by confidence descending
        scores.sort(key=lambda x: x["confidence"], reverse=True)
        
        return scores[:top_n]
