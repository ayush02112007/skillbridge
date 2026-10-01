"""Live industry project endpoints."""
from app.api.v1.endpoints._opportunity_routes import build_router
from app.models.enums import OpportunityType
from app.schemas.opportunity import LiveProjectCreate

router = build_router(
    prefix="/projects",
    tag="Live Projects",
    opportunity_type=OpportunityType.LIVE_PROJECT,
    create_schema=LiveProjectCreate,
    label="live project",
    list_description="Real-world problems published by industry for student teams.",
    create_description=(
        "Publishes a live project. Teams, milestones, tasks and submissions are "
        "managed through the project execution endpoints below."
    ),
)
