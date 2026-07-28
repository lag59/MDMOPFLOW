"""
Billing Service for Invoice Generation

Handles:
- Rate configuration (per truck, material, etc.)
- Invoice generation from tickets
- Line item calculation
- Invoice totals
"""

from decimal import Decimal
from enum import Enum
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models import Ticket, Project


class RateType(str, Enum):
    """Rate types for billing."""
    PER_TON = "per_ton"
    PER_CUBIC_YARD = "per_yard"
    PER_LOAD = "per_load"
    FLAT = "flat"


class BillingService:
    """Service to calculate invoices from tickets."""

    @staticmethod
    def calculate_line_item(
        ticket: Ticket,
        rate_per_ton: Decimal | None = None,
        rate_per_yard: Decimal | None = None,
        rate_per_load: Decimal | None = None,
    ) -> dict:
        """
        Calculate line item for a single ticket.
        
        Applies rates in priority order:
        1. rate_per_ton (if tons available)
        2. rate_per_yard (if yards available)
        3. rate_per_load (if available)
        4. Use revenue field as fallback
        
        Returns dict with:
        - description: str
        - quantity: Decimal
        - unit: str
        - rate: Decimal
        - amount: Decimal
        - rate_type: str
        """
        amount = Decimal("0.00")
        rate_type = "unknown"
        quantity = Decimal("1.00")
        unit = "load"

        if rate_per_ton and ticket.tons and ticket.tons > 0:
            amount = ticket.tons * rate_per_ton
            quantity = ticket.tons
            unit = "tons"
            rate_type = "per_ton"

        elif rate_per_yard and ticket.volume_yards and ticket.volume_yards > 0:
            amount = ticket.volume_yards * rate_per_yard
            quantity = ticket.volume_yards
            unit = "cubic yards"
            rate_type = "per_yard"

        elif rate_per_load:
            amount = rate_per_load
            quantity = Decimal("1.00")
            unit = "load"
            rate_type = "per_load"

        else:
            # Fallback to ticket revenue
            amount = ticket.revenue or Decimal("0.00")
            rate_type = "revenue"
            unit = "ticket"

        description = f"{ticket.material} - {ticket.truck} (Ticket #{ticket.ticket_number})"

        return {
            "ticket_id": ticket.id,
            "description": description,
            "quantity": quantity,
            "unit": unit,
            "rate": amount / quantity if quantity > 0 else Decimal("0.00"),
            "amount": amount,
            "rate_type": rate_type,
        }

    @staticmethod
    def generate_invoice_line_items(
        db: Session,
        project_id: str,
        rate_per_ton: Decimal | None = None,
        rate_per_yard: Decimal | None = None,
        rate_per_load: Decimal | None = None,
        status_filter: str = "approved",
    ) -> dict:
        """
        Generate invoice line items for all tickets in a project.
        
        Args:
        - project_id: Project to invoice
        - rate_per_ton: Rate per ton (priority 1)
        - rate_per_yard: Rate per cubic yard (priority 2)
        - rate_per_load: Rate per load (priority 3)
        - status_filter: Only include tickets with this status (default: approved)
        
        Returns dict with:
        - project_id: str
        - invoice_date: datetime
        - line_items: list[dict]
        - subtotal: Decimal
        - tax_rate: float (0.00-1.00)
        - tax_amount: Decimal
        - total: Decimal
        """
        query = select(Ticket).where(
            and_(
                Ticket.project_id == project_id,
                Ticket.status == status_filter,
            )
        )

        tickets = db.scalars(query).all()

        line_items = []
        subtotal = Decimal("0.00")

        for ticket in tickets:
            line_item = BillingService.calculate_line_item(
                ticket,
                rate_per_ton=rate_per_ton,
                rate_per_yard=rate_per_yard,
                rate_per_load=rate_per_load,
            )
            line_items.append(line_item)
            subtotal += line_item["amount"]

        # TODO: Get tax rate from project or config
        tax_rate = 0.0
        tax_amount = subtotal * Decimal(str(tax_rate))
        total = subtotal + tax_amount

        return {
            "project_id": project_id,
            "line_items": line_items,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total": total,
            "item_count": len(line_items),
        }

    @staticmethod
    def estimate_invoice_amount(
        db: Session,
        project_id: str,
        rate_per_ton: Decimal | None = None,
        rate_per_yard: Decimal | None = None,
        rate_per_load: Decimal | None = None,
    ) -> Decimal:
        """
        Quick estimate of invoice total using standard rates.
        
        Useful for dashboard preview without generating full invoice.
        """
        invoice_data = BillingService.generate_invoice_line_items(
            db,
            project_id,
            rate_per_ton=rate_per_ton,
            rate_per_yard=rate_per_yard,
            rate_per_load=rate_per_load,
        )
        return invoice_data["total"]
