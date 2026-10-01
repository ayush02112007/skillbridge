"""Job and placement endpoints."""
from app.api.v1.endpoints._opportunity_routes import build_router
from app.models.enums import OpportunityType
from app.schemas.opportunity import JobCreate

router = build_router(
    prefix="/jobs",
    tag="Jobs",
    opportunity_type=OpportunityType.JOB,
    create_schema=JobCreate,
    label="job",
    list_description=(
        "Published jobs. Students see their personal match score on every row; "
        "`sort_by=match` orders by best fit rather than recency."
    ),
    create_description=(
        "Creates a job posting for the recruiter's company. Run "
        "`POST /opportunities/analyse-description` first to turn a free-text "
        "description into structured skill requirements you can review."
    ),
)
