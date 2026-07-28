from __future__ import annotations

import warnings
from uuid import uuid4

from sqlalchemy.exc import SAWarning

from app.db import Base
from app.models import Project, Ticket, Tenant, User
from app.services.ai_ticket_assignment import AITicketAssignment
from tests.conftest import TestingSessionLocal, engine


def _reset_database() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Can't sort tables for DROP; an unresolvable foreign key dependency exists between tables: document_extractions, tickets;.*",
            category=SAWarning,
        )
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_test_data() -> tuple[str, str, str, str]:
    _reset_database()

    tenant_id = str(uuid4())
    user_id = str(uuid4())
    matching_project_id = str(uuid4())
    alternate_project_id = str(uuid4())

    with TestingSessionLocal() as db:
        db.add(
            Tenant(
                id=tenant_id,
                name=f"Test Tenant {tenant_id[:8]}",
                company_type="General Contractor",
                selected_modules="Projects,Intake",
            )
        )
        db.add(
            User(
                id=user_id,
                email=f"user-{tenant_id[:8]}@example.com",
                password_hash="hash",
                display_name="Test User",
            )
        )
        db.add(
            Project(
                id=matching_project_id,
                tenant_id=tenant_id,
                project_name="Downtown Plaza",
                project_number="P-100",
                customer="Acme",
                address="123 Main Street, Austin, TX",
                project_manager="Manager One",
                status="active",
                created_by=user_id,
            )
        )
        db.add(
            Project(
                id=alternate_project_id,
                tenant_id=tenant_id,
                project_name="North Yard",
                project_number="P-200",
                customer="Acme",
                address="900 Industrial Way, Dallas, TX",
                project_manager="Manager Two",
                status="active",
                created_by=user_id,
            )
        )
        db.add(
            Ticket(
                tenant_id=tenant_id,
                project_id=None,
                ticket_number="T-1",
                truck="TRK-1",
                driver="Driver One",
                material="Dirt",
                origin="",
                destination="123 Main Street, Austin, TX",
                status="draft",
                notes="",
                created_by=user_id,
            )
        )
        db.commit()

    return tenant_id, user_id, matching_project_id, alternate_project_id


def test_auto_assign_uses_llm_choice_when_available(monkeypatch) -> None:
    tenant_id, _, _, alternate_project_id = _create_test_data()

    class FakeOpenAIClient:
        def __init__(self) -> None:
            self.available = True

        def generate_json(self, **kwargs):
            return {
                "project_id": alternate_project_id,
                "confidence": 0.93,
                "reason": "Model selected the alternate project",
            }

    monkeypatch.setattr("app.services.ai_ticket_assignment.OpenAILLMClient", FakeOpenAIClient)

    with TestingSessionLocal() as db:
        result = AITicketAssignment.auto_assign_unassigned_tickets(db=db, tenant_id=tenant_id, confidence_threshold=0.75)
        ticket = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).one()

    assert result["assigned"] == 1
    assert result["assignments"][0]["project_id"] == alternate_project_id
    assert result["assignments"][0]["match_info"] == "Model selected the alternate project"
    assert ticket.project_id == alternate_project_id


def test_auto_assign_falls_back_to_deterministic_match_without_llm(monkeypatch) -> None:
    tenant_id, _, matching_project_id, _ = _create_test_data()

    class FakeOpenAIClient:
        def __init__(self) -> None:
            self.available = False

        def generate_json(self, **kwargs):
            raise AssertionError("LLM should not be called when unavailable")

    monkeypatch.setattr("app.services.ai_ticket_assignment.OpenAILLMClient", FakeOpenAIClient)

    with TestingSessionLocal() as db:
        result = AITicketAssignment.auto_assign_unassigned_tickets(db=db, tenant_id=tenant_id, confidence_threshold=0.75)
        ticket = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).one()

    assert result["assigned"] == 1
    assert result["assignments"][0]["project_id"] == matching_project_id
    assert result["assignments"][0]["match_info"].startswith("Deterministic match:")
    assert ticket.project_id == matching_project_id