"""Domain enumerations.

All enum columns are persisted as VARCHAR with a CHECK constraint
(``native_enum=False``) so migrations stay simple and the schema is portable
between PostgreSQL and SQLite.
"""
from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    STUDENT = "STUDENT"
    ACADEMICIAN = "ACADEMICIAN"
    INDUSTRY_RECRUITER = "INDUSTRY_RECRUITER"
    INDUSTRY_ADMIN = "INDUSTRY_ADMIN"
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class UserStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class ProficiencyLevel(StrEnum):
    NONE = "NONE"
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"

    @property
    def score(self) -> int:
        return PROFICIENCY_SCORE[self]

    @classmethod
    def from_score(cls, value: float) -> ProficiencyLevel:
        """Map a 0-100 score onto a proficiency band."""
        if value < 20:
            return cls.NONE
        if value < 45:
            return cls.BEGINNER
        if value < 70:
            return cls.INTERMEDIATE
        if value < 88:
            return cls.ADVANCED
        return cls.EXPERT


PROFICIENCY_SCORE: dict[ProficiencyLevel, int] = {
    ProficiencyLevel.NONE: 0,
    ProficiencyLevel.BEGINNER: 1,
    ProficiencyLevel.INTERMEDIATE: 2,
    ProficiencyLevel.ADVANCED: 3,
    ProficiencyLevel.EXPERT: 4,
}


class SkillSource(StrEnum):
    SELF_REPORTED = "SELF_REPORTED"
    ASSESSMENT = "ASSESSMENT"
    CERTIFICATION = "CERTIFICATION"
    PROJECT = "PROJECT"
    RESUME = "RESUME"
    ENDORSEMENT = "ENDORSEMENT"
    WORK_EXPERIENCE = "WORK_EXPERIENCE"


class SkillImportance(StrEnum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    OPTIONAL = "OPTIONAL"


class AssessmentType(StrEnum):
    MCQ = "MCQ"
    SCENARIO = "SCENARIO"
    TECHNICAL = "TECHNICAL"
    SELF_ASSESSMENT = "SELF_ASSESSMENT"
    APTITUDE = "APTITUDE"
    SOFT_SKILL = "SOFT_SKILL"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTI_CHOICE = "MULTI_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    LIKERT = "LIKERT"


class Difficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

    @property
    def weight(self) -> float:
        return {"EASY": 1.0, "MEDIUM": 1.5, "HARD": 2.25}[self.value]


class AttemptStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    EVALUATED = "EVALUATED"
    ABANDONED = "ABANDONED"
    EXPIRED = "EXPIRED"


class OpportunityType(StrEnum):
    INTERNSHIP = "INTERNSHIP"
    JOB = "JOB"
    LIVE_PROJECT = "LIVE_PROJECT"
    FACULTY_OPPORTUNITY = "FACULTY_OPPORTUNITY"


class OpportunityStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class WorkMode(StrEnum):
    ONSITE = "ONSITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    APPRENTICESHIP = "APPRENTICESHIP"


class FacultyOpportunityKind(StrEnum):
    FACULTY_INTERNSHIP = "FACULTY_INTERNSHIP"
    FDP = "FDP"
    INDUSTRIAL_TRAINING = "INDUSTRIAL_TRAINING"
    CONSULTANCY = "CONSULTANCY"
    RESEARCH_COLLABORATION = "RESEARCH_COLLABORATION"
    GUEST_LECTURE = "GUEST_LECTURE"


class ApplicationStatus(StrEnum):
    APPLIED = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW = "INTERVIEW"
    OFFERED = "OFFERED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_APPLICATION_STATUSES


TERMINAL_APPLICATION_STATUSES = frozenset(
    {ApplicationStatus.SELECTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}
)

# Explicit state machine - transitions outside this map are rejected by the
# service layer so application history can never become incoherent.
APPLICATION_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.APPLIED: {
        ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED,
        ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.SHORTLISTED, ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.INTERVIEW, ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.OFFERED, ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFERED: {
        ApplicationStatus.SELECTED, ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SELECTED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}

# Ordered pipeline used by the application-tracking timeline in the UI.
APPLICATION_PIPELINE = [
    ApplicationStatus.APPLIED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.SHORTLISTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFERED,
    ApplicationStatus.SELECTED,
]


class ProgramType(StrEnum):
    COURSE = "COURSE"
    CERTIFICATION = "CERTIFICATION"
    WORKSHOP = "WORKSHOP"
    BOOTCAMP = "BOOTCAMP"
    MENTORSHIP_PROGRAM = "MENTORSHIP_PROGRAM"
    TRAINING = "TRAINING"


class EnrollmentStatus(StrEnum):
    ENROLLED = "ENROLLED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"


class MentorshipStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EventType(StrEnum):
    WORKSHOP = "WORKSHOP"
    GUEST_LECTURE = "GUEST_LECTURE"
    HACKATHON = "HACKATHON"
    INDUSTRY_VISIT = "INDUSTRY_VISIT"
    WEBINAR = "WEBINAR"
    CAREER_SESSION = "CAREER_SESSION"
    INNOVATION_CHALLENGE = "INNOVATION_CHALLENGE"
    PANEL_DISCUSSION = "PANEL_DISCUSSION"


class RegistrationStatus(StrEnum):
    REGISTERED = "REGISTERED"
    WAITLISTED = "WAITLISTED"
    ATTENDED = "ATTENDED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"


class DocumentType(StrEnum):
    RESUME = "RESUME"
    CERTIFICATE = "CERTIFICATE"
    MARKSHEET = "MARKSHEET"
    INTERNSHIP_CERTIFICATE = "INTERNSHIP_CERTIFICATE"
    PROJECT_REPORT = "PROJECT_REPORT"
    IDENTITY = "IDENTITY"
    OFFER_LETTER = "OFFER_LETTER"
    PROFILE_PHOTO = "PROFILE_PHOTO"
    COMPANY_LOGO = "COMPANY_LOGO"
    OTHER = "OTHER"


class ScanStatus(StrEnum):
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    SKIPPED = "SKIPPED"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Visibility(StrEnum):
    PUBLIC = "PUBLIC"
    INSTITUTION_ONLY = "INSTITUTION_ONLY"
    PRIVATE = "PRIVATE"


class NotificationCategory(StrEnum):
    APPLICATION = "APPLICATION"
    OPPORTUNITY = "OPPORTUNITY"
    LEARNING = "LEARNING"
    MENTORSHIP = "MENTORSHIP"
    EVENT = "EVENT"
    ASSESSMENT = "ASSESSMENT"
    MESSAGE = "MESSAGE"
    SYSTEM = "SYSTEM"


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class ResearchProjectType(StrEnum):
    RESEARCH = "RESEARCH"
    CONSULTANCY = "CONSULTANCY"
    JOINT_PUBLICATION = "JOINT_PUBLICATION"
    INNOVATION = "INNOVATION"
    SPONSORED_RESEARCH = "SPONSORED_RESEARCH"


class CollaborationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MilestoneStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditAction(StrEnum):
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"  # noqa: S105 - audit action name
    PASSWORD_RESET = "PASSWORD_RESET"  # noqa: S105 - audit action name
    PROFILE_UPDATE = "PROFILE_UPDATE"
    OPPORTUNITY_CREATE = "OPPORTUNITY_CREATE"
    OPPORTUNITY_UPDATE = "OPPORTUNITY_UPDATE"
    OPPORTUNITY_DELETE = "OPPORTUNITY_DELETE"
    APPLICATION_SUBMIT = "APPLICATION_SUBMIT"
    APPLICATION_STATUS_CHANGE = "APPLICATION_STATUS_CHANGE"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_ACCESS = "DOCUMENT_ACCESS"
    DOCUMENT_DELETE = "DOCUMENT_DELETE"
    ADMIN_ACTION = "ADMIN_ACTION"
    ROLE_CHANGE = "ROLE_CHANGE"
    EXPORT = "EXPORT"
    ASSESSMENT_SUBMIT = "ASSESSMENT_SUBMIT"


class BadgeCode(StrEnum):
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    PROFILE_COMPLETE = "PROFILE_COMPLETE"
    FIRST_CERTIFICATION = "FIRST_CERTIFICATION"
    FIRST_INTERNSHIP = "FIRST_INTERNSHIP"
    PROJECT_BUILDER = "PROJECT_BUILDER"
    INDUSTRY_READY = "INDUSTRY_READY"
    TOP_SKILL_PERFORMER = "TOP_SKILL_PERFORMER"
    MENTORSHIP_GRADUATE = "MENTORSHIP_GRADUATE"


class Degree(StrEnum):
    SECONDARY = "SECONDARY"
    HIGHER_SECONDARY = "HIGHER_SECONDARY"
    DIPLOMA = "DIPLOMA"
    BACHELORS = "BACHELORS"
    MASTERS = "MASTERS"
    DOCTORATE = "DOCTORATE"
