"""Aggregate router for API v1."""
from fastapi import APIRouter

api_router = APIRouter()

# Endpoint modules are registered here; each owns its prefix and tags.
from app.api.v1.endpoints import (  # noqa: E402
    academician,
    admin,
    analytics,
    applications,
    assessments,
    auth,
    companies,
    documents,
    events,
    health,
    institutions,
    internships,
    jobs,
    learning,
    mentorship,
    messaging,
    notifications,
    opportunities,
    portfolio,
    projects,
    recommendations,
    research,
    search,
    skills,
    students,
)

api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(academician.router)
api_router.include_router(academician.faculty_opportunities_router)
api_router.include_router(skills.router)
api_router.include_router(skills.roles_router)
api_router.include_router(assessments.router)
api_router.include_router(opportunities.router)
api_router.include_router(internships.router)
api_router.include_router(jobs.router)
api_router.include_router(projects.router)
api_router.include_router(applications.router)
api_router.include_router(recommendations.router)
api_router.include_router(learning.router)
api_router.include_router(mentorship.router)
api_router.include_router(events.router)
api_router.include_router(research.router)
api_router.include_router(companies.router)
api_router.include_router(institutions.router)
api_router.include_router(documents.router)
api_router.include_router(portfolio.router)
api_router.include_router(portfolio.resumes_router)
api_router.include_router(notifications.router)
api_router.include_router(messaging.router)
api_router.include_router(search.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(health.router)
