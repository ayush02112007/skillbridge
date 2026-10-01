"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""
from app.core.database import Base
from app.models.application import (
    Application,
    ApplicationStatusHistory,
    Interview,
)
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentOption,
    AssessmentQuestion,
    AttemptSkillScore,
)
from app.models.audit import AuditLog, SavedSearch
from app.models.document import Document, DocumentAccessGrant
from app.models.enums import *
from app.models.event import Event, EventRegistration
from app.models.learning import (
    Certification,
    CourseModule,
    Enrollment,
    LearningPath,
    LearningProgram,
    ModuleProgress,
    ProgramSkill,
    StudentCertification,
)
from app.models.mentorship import MentorProfile, MentorshipRequest, MentorshipSession
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.notification import EmailLog, Notification, NotificationPreference
from app.models.opportunity import (
    FacultyOpportunity,
    Internship,
    Job,
    LiveProject,
    Opportunity,
    OpportunitySkill,
    SavedOpportunity,
)
from app.models.organization import Company, Department, IndustryPartnership, Institution
from app.models.portfolio import Badge, Portfolio, Resume, ResumeAnalysis, StudentBadge
from app.models.profile import (
    AcademicianProfile,
    Achievement,
    EducationRecord,
    ExperienceRecord,
    RecruiterProfile,
    StudentProfile,
    StudentProject,
)
from app.models.project import (
    ProjectMilestone,
    ProjectSubmission,
    ProjectTask,
    ProjectTeam,
    ProjectTeamMember,
)
from app.models.recommendation import Recommendation, RecommendationFeedback
from app.models.research import ResearchApplication, ResearchProject
from app.models.skill import (
    JobRole,
    RoleSkill,
    Skill,
    SkillCategory,
    SkillEndorsement,
    SkillGapAnalysis,
    SkillGapItem,
    StudentSkill,
)
from app.models.user import (
    OneTimeToken,
    Permission,
    Role,
    User,
    UserSession,
    role_permissions,
    user_roles,
)

__all__ = [
    "AcademicianProfile",
    "Achievement",
    "Application",
    "ApplicationStatusHistory",
    "Assessment",
    "AssessmentAnswer",
    "AssessmentAttempt",
    "AssessmentOption",
    "AssessmentQuestion",
    "AttemptSkillScore",
    "AuditLog",
    "Badge",
    "Base",
    "Certification",
    "Company",
    "Conversation",
    "ConversationParticipant",
    "CourseModule",
    "Department",
    "Document",
    "DocumentAccessGrant",
    "EducationRecord",
    "EmailLog",
    "Enrollment",
    "Event",
    "EventRegistration",
    "ExperienceRecord",
    "FacultyOpportunity",
    "IndustryPartnership",
    "Institution",
    "Internship",
    "Interview",
    "Job",
    "JobRole",
    "LearningPath",
    "LearningProgram",
    "LiveProject",
    "MentorProfile",
    "MentorshipRequest",
    "MentorshipSession",
    "Message",
    "ModuleProgress",
    "Notification",
    "NotificationPreference",
    "OneTimeToken",
    "Opportunity",
    "OpportunitySkill",
    "Permission",
    "Portfolio",
    "ProgramSkill",
    "ProjectMilestone",
    "ProjectSubmission",
    "ProjectTask",
    "ProjectTeam",
    "ProjectTeamMember",
    "Recommendation",
    "RecommendationFeedback",
    "RecruiterProfile",
    "ResearchApplication",
    "ResearchProject",
    "Resume",
    "ResumeAnalysis",
    "Role",
    "RoleSkill",
    "SavedOpportunity",
    "SavedSearch",
    "Skill",
    "SkillCategory",
    "SkillEndorsement",
    "SkillGapAnalysis",
    "SkillGapItem",
    "StudentBadge",
    "StudentCertification",
    "StudentProfile",
    "StudentProject",
    "StudentSkill",
    "User",
    "UserSession",
    "role_permissions",
    "user_roles",
]
