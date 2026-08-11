"""
AI assist endpoint for estimates.
Separated into its own module to guarantee Railway picks it up on next deploy.
"""
from fastapi import APIRouter, Depends, HTTPException
import json

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import AuditLog, Estimate
from app.schemas import EstimateAuditLogResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(tags=["Estimator"])


def _get_estimate(db: Session, tenant_id: str, estimate_id: str) -> Estimate:
    est = db.scalar(select(Estimate).where(Estimate.id == estimate_id, Estimate.tenant_id == tenant_id))
    if est is None:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return est


def _require_tenant(context: RequestContext) -> str:
    tid = context.membership.tenant_id if context.membership else context.tenant_id
    if not tid:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tid


@router.post(
    "/api/estimates/{estimate_id}/ai-assist",
    operation_id="estimate_ai_assist",
    summary="AI-assisted field pre-fill for estimate",
)
def ai_assist_estimate(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
) -> dict:
    """Return AI-suggested values for estimate fields. All fields are labelled AI-generated."""
    from app.core.config import settings

    tenant_id = _require_tenant(context)
    estimate = _get_estimate(db, tenant_id, estimate_id)

    prompt = (
        "You are a construction estimating assistant. "
        f"Given this estimate context, suggest realistic values for the fields listed below. "
        f"Respond ONLY with a valid JSON object — no prose, no markdown fences.\n\n"
        f"Estimate name: {estimate.estimate_name}\n"
        f"Project name: {estimate.project_name or 'unknown'}\n"
        f"Project type: {estimate.project_type or 'unknown'}\n"
        f"Customer: {estimate.customer_name or 'unknown'}\n"
        f"Contract type: {estimate.contract_type or 'unknown'}\n"
        f"Notes: {estimate.notes or ''}\n\n"
        "Fields to suggest (return only these keys):\n"
        "  target_margin_percent   (number as string)\n"
        "  default_overhead_percent (number as string)\n"
        "  default_contingency_percent (number as string)\n"
        "  estimate_type           (Conceptual/Preliminary/Budgetary/Detailed/Bid/Change-order estimate)\n"
        "  contract_type           (Lump sum/Unit price/Cost plus/Time and materials/GMP/Design-build)\n"
        "  suggested_line_items    (array of up to 5: {description,category,unit,quantity,unit_cost})\n"
        "  rationale               (one short sentence)"
    )

    suggestions: dict = {}
    ai_generated = bool(settings.OPENAI_API_KEY)

    if ai_generated:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.3,
            )
            raw = (response.choices[0].message.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            suggestions = json.loads(raw)
        except Exception:
            ai_generated = False

    if not ai_generated:
        pt = (estimate.project_type or "").lower()
        margin = "16" if "civil" in pt else "14" if ("site" in pt or "grading" in pt) else "15"
        contingency = "7" if "civil" in pt else "5"
        suggestions = {
            "target_margin_percent": margin,
            "default_overhead_percent": "8",
            "default_contingency_percent": contingency,
            "estimate_type": "Bid" if "bid" in (estimate.estimate_type or "").lower() else "Detailed",
            "contract_type": estimate.contract_type or "Lump sum",
            "suggested_line_items": [
                {"description": "Mobilization & site setup", "category": "General", "unit": "LS", "quantity": "1", "unit_cost": "25000"},
                {"description": "Clearing & grubbing", "category": "Earthwork", "unit": "AC", "quantity": "10", "unit_cost": "3500"},
                {"description": "Unclassified excavation", "category": "Earthwork", "unit": "CY", "quantity": "5000", "unit_cost": "12"},
                {"description": "Subgrade preparation", "category": "Earthwork", "unit": "SY", "quantity": "8000", "unit_cost": "4"},
                {"description": "Erosion control & SWPPP", "category": "Environmental", "unit": "LS", "quantity": "1", "unit_cost": "8000"},
            ],
            "rationale": "Template defaults based on project type. Configure OPENAI_API_KEY for AI-generated suggestions.",
        }

    db.add(AuditLog(
        tenant_id=tenant_id, actor_user_id=context.user.id,
        action="ai_assist", resource_type="estimate", resource_id=estimate.id,
        details="AI assist suggestions generated", created_by=context.user.id,
    ))
    db.commit()

    return {
        "estimate_id": estimate.id,
        "ai_generated": ai_generated,
        "suggestions": suggestions,
        "disclaimer": (
            "These values were suggested by AI based on the estimate context. "
            "They are not verified data. Review and edit each field before saving."
        ) if ai_generated else (
            "These are template defaults based on project type — NOT generated by AI. "
            "Edit each field to match your actual scope before saving."
        ),
    }
