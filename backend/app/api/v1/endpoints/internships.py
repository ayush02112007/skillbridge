"""Internship endpoints."""
from app.api.v1.endpoints._opportunity_routes import build_router
from app.models.enums import OpportunityType
from app.schemas.opportunity import InternshipCreate

router = build_router(
    prefix="/internships",
    tag="Internships",
    opportunity_type=OpportunityType.INTERNSHIP,
    create_schema=InternshipCreate,
    label="internship",
    list_description=(
        "Published internships. Students see their personal match score on every "
        "row; `sort_by=match` orders by best fit rather than recency."
    ),
    create_description=(
        "Creates an internship for the recruiter's company. If no skills are "
        "supplied but a `job_role_id` is, the role's canonical skill profile is "
        "copied in so the posting is matchable from the moment it is published."
    ),
)
