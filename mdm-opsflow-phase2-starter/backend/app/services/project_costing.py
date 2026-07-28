"""
Project Costing and Profitability Service

Handles:
- Aggregation of ticket costs by project
- Project profitability calculations
- Project financial summaries
- Cost tracking and variance analysis
"""

from decimal import Decimal
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Project, Ticket


class ProjectCostAggregation:
    """Service to aggregate and calculate project costs and profitability."""

    @staticmethod
    def get_project_costs(db: Session, project_id: str) -> dict:
        """
        Get aggregated costs for a project.
        
        Returns dict with:
        - total_tickets: int (count of approved/active tickets)
        - total_revenue: Decimal
        - total_fuel_cost: Decimal
        - total_net_tons: Decimal
        - total_cubic_yards: Decimal
        - total_loads: Decimal (estimated from tons / truck capacity)
        - avg_revenue_per_ton: Decimal
        """
        query = select(
            func.count(Ticket.id).label("total_tickets"),
            func.sum(Ticket.revenue).label("total_revenue"),
            func.sum(Ticket.fuel_cost).label("total_fuel_cost"),
            func.sum(Ticket.tons).label("total_net_tons"),
            func.sum(Ticket.volume_yards).label("total_cubic_yards"),
        ).where(
            and_(
                Ticket.project_id == project_id,
                Ticket.status.in_(["approved", "active", "completed"]),
            )
        )

        result = db.execute(query).one()

        total_revenue = result.total_revenue or Decimal("0.00")
        total_fuel_cost = result.total_fuel_cost or Decimal("0.00")
        total_net_tons = result.total_net_tons or Decimal("0.00")
        total_cubic_yards = result.total_cubic_yards or Decimal("0.00")

        # Avoid division by zero
        avg_revenue_per_ton = Decimal("0.00")
        if total_net_tons > 0:
            avg_revenue_per_ton = total_revenue / total_net_tons

        return {
            "total_tickets": result.total_tickets or 0,
            "total_revenue": total_revenue,
            "total_fuel_cost": total_fuel_cost,
            "total_net_tons": total_net_tons,
            "total_cubic_yards": total_cubic_yards,
            "avg_revenue_per_ton": avg_revenue_per_ton,
        }

    @staticmethod
    def get_project_profitability(db: Session, project_id: str) -> dict:
        """
        Get project profitability summary.
        
        Compares contract/budget vs actual costs from tickets.
        
        Returns dict with:
        - contract_amount: Decimal
        - budgeted_cost: Decimal
        - actual_cost: Decimal (fuel_cost from tickets)
        - actual_revenue: Decimal (revenue from tickets)
        - contract_variance: Decimal (contract_amount - actual_revenue)
        - budget_variance: Decimal (budget - actual_cost)
        - gross_profit: Decimal (actual_revenue - actual_cost)
        - profit_margin: float (gross_profit / actual_revenue * 100)
        - cost_overrun: bool
        - revenue_shortfall: bool
        """
        # Get project
        project = db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get ticket costs
        costs = ProjectCostAggregation.get_project_costs(db, project_id)

        contract_amount = project.contract_amount or Decimal("0.00")
        budgeted_cost = project.budget or Decimal("0.00")
        actual_cost = costs["total_fuel_cost"]
        actual_revenue = costs["total_revenue"]

        contract_variance = contract_amount - actual_revenue
        budget_variance = budgeted_cost - actual_cost
        gross_profit = actual_revenue - actual_cost

        profit_margin = Decimal("0.00")
        if actual_revenue > 0:
            profit_margin = (gross_profit / actual_revenue) * Decimal("100")

        cost_overrun = actual_cost > budgeted_cost if budgeted_cost > 0 else False
        revenue_shortfall = actual_revenue < contract_amount if contract_amount > 0 else False

        return {
            "contract_amount": contract_amount,
            "budgeted_cost": budgeted_cost,
            "actual_cost": actual_cost,
            "actual_revenue": actual_revenue,
            "contract_variance": contract_variance,
            "budget_variance": budget_variance,
            "gross_profit": gross_profit,
            "profit_margin": float(profit_margin),
            "cost_overrun": cost_overrun,
            "revenue_shortfall": revenue_shortfall,
            "ticket_count": costs["total_tickets"],
            "total_tons": costs["total_net_tons"],
            "total_cubic_yards": costs["total_cubic_yards"],
        }

    @staticmethod
    def get_all_project_summaries(db: Session, tenant_id: str) -> list[dict]:
        """
        Get profitability summary for all projects in a tenant.
        
        Useful for dashboard showing which projects are profitable.
        """
        projects = db.execute(
            select(Project).where(Project.tenant_id == tenant_id)
        ).scalars().all()

        summaries = []
        for project in projects:
            try:
                summary = ProjectCostAggregation.get_project_profitability(db, project.id)
                summary["project_id"] = project.id
                summary["project_name"] = project.project_name
                summary["status"] = project.status
                summaries.append(summary)
            except ValueError:
                # Project might not exist yet
                continue

        return summaries
