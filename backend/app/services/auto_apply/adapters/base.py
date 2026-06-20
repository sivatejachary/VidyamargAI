"""
Base Application Adapter — Abstract interface for all ATS platform adapters.
Every platform adapter inherits from this class and implements all abstract methods.
"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.auto_apply_models import ApplicationAccount


class BaseApplicationAdapter(ABC):
    """
    Abstract base for all ATS/job portal application adapters.

    Class attributes:
        adapter_version (str): Semantic version string, frozen into ApplicationTask at submission.
                               Format: "platform_key:major.minor" e.g. "greenhouse:1.0"
        platform_key (str):    The registry key for this adapter (e.g. "greenhouse").
        requires_password_storage (bool): True only for platforms with no session persistence
                                          (Workday, Taleo, SuccessFactors, Oracle HCM).
    """
    adapter_version: str = "unknown:1.0"
    platform_key: str = "unknown"
    requires_password_storage: bool = False

    @abstractmethod
    async def login(self, context, account) -> bool:
        """
        Restore session from cookies/tokens, or perform fresh login.
        Returns True on success, False on failure.
        context: Playwright BrowserContext
        account: ApplicationAccount model instance
        """

    @abstractmethod
    async def create_account(self, context, profile: dict, platform: str) -> dict:
        """
        Create a new account on the platform using the candidate profile.
        Returns dict with: {username, password (if needed), session_cookies}
        context: Playwright BrowserContext
        """

    @abstractmethod
    async def upload_resume(self, page, resume_bytes: bytes, filename: str) -> bool:
        """
        Upload resume PDF to the platform's file upload field.
        Returns True on success.
        """

    @abstractmethod
    async def fill_personal_details(self, page, profile: dict) -> bool:
        """Fill name, email, phone, address fields."""

    @abstractmethod
    async def fill_education(self, page, profile: dict) -> bool:
        """Fill education/qualification fields."""

    @abstractmethod
    async def fill_experience(self, page, profile: dict) -> bool:
        """Fill work experience / employment history fields."""

    @abstractmethod
    async def fill_projects(self, page, profile: dict) -> bool:
        """Fill projects section if present."""

    @abstractmethod
    async def fill_skills(self, page, profile: dict) -> bool:
        """Fill skills / competencies fields."""

    @abstractmethod
    async def fill_certifications(self, page, profile: dict) -> bool:
        """Fill certifications/licenses fields if present."""

    @abstractmethod
    async def answer_screening(self, page, questions: list, engine, cover_letter_text: Optional[str] = None) -> bool:
        """
        Detect and answer screening/qualifying questions.
        engine: ScreeningAnswerEngine instance
        cover_letter_text: Previously generated cover letter for context.
        Returns True if all questions answered.
        """

    @abstractmethod
    async def submit(self, page) -> bool:
        """Find and click the final submit button. Returns True on success."""

    @abstractmethod
    async def capture_confirmation(self, page) -> dict:
        """
        Capture submission confirmation data.
        Returns dict with: {confirmation_number, message, screenshot_base64 (optional)}
        """

    @abstractmethod
    async def detect_verification_required(self, page) -> Optional[str]:
        """
        Detect if the page is requesting user verification.
        Returns: "otp" | "email" | "phone" | "mfa" | "captcha" | None
        """

    # ── Default helpers ─────────────────────────────────────────────────────

    async def _safe_fill(self, page, selector: str, value: str) -> bool:
        """Attempt to fill a field; returns True on success, False silently on missing field."""
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.fill(value)
                return True
        except Exception:
            pass
        return False

    async def _safe_click(self, page, selector: str) -> bool:
        """Attempt to click an element; returns True on success."""
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.click()
                return True
        except Exception:
            pass
        return False

    async def _detect_otp_patterns(self, page) -> Optional[str]:
        """Common OTP/verification detection patterns shared across adapters."""
        try:
            content = await page.content()
            cl = content.lower()
            if any(p in cl for p in ["enter the code", "verification code", "otp", "one-time"]):
                return "otp"
            if any(p in cl for p in ["verify your email", "check your inbox", "email verification"]):
                return "email"
            if any(p in cl for p in ["verify your phone", "sms code", "text message"]):
                return "phone"
            if any(p in cl for p in ["two-factor", "2fa", "authenticator"]):
                return "mfa"
            if any(p in cl for p in ["captcha", "i'm not a robot", "recaptcha"]):
                return "captcha"
        except Exception:
            pass
        return None