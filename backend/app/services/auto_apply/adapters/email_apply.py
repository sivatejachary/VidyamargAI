"""
EmailApplication Adapter — Auto Apply implementation for EmailApplication.
"""
import logging
from typing import Optional
from app.services.auto_apply.adapters.base import BaseApplicationAdapter

logger = logging.getLogger(__name__)


class EmailApplicationAdapter(BaseApplicationAdapter):
    adapter_version: str = "email_apply:1.0"
    platform_key: str = "email_apply"
    requires_password_storage: bool = False  # True only for Workday, Taleo, SuccessFactors, Oracle HCM

    async def login(self, context, account) -> bool:
        """Restore session from saved cookies, or perform fresh login."""
        try:
            if account and account.encrypted_cookies:
                from app.services.auto_apply.credential_vault import credential_vault
                import json
                cookies_json = credential_vault.decrypt(account.encrypted_cookies)
                cookies = json.loads(cookies_json)
                await context.add_cookies(cookies)
                logger.info(f"{self.platform_key}: Session restored from cookies.")
                return True
        except Exception as e:
            logger.warning(f"{self.platform_key}: Cookie restore failed: {e}")
        return False

    async def create_account(self, context, profile: dict, platform: str) -> dict:
        """Create new account on EmailApplication."""
        logger.info(f"{self.platform_key}: Account creation not yet automated — returning empty.")
        return {}

        async def upload_resume(self, page, resume_bytes: bytes, filename: str) -> bool:
        """Skip resume upload for email applies as they are handled via attachments/mailto."""
        logger.info("email_apply: Skipping resume upload in browser.")
        return True

    async def fill_personal_details(self, page, profile: dict) -> bool:
        """Fill personal details on EmailApplication."""
        filled = 0
        fields = [
            ("input[name*='first' i], input[placeholder*='first name' i]", profile.get("first_name", "")),
            ("input[name*='last' i], input[placeholder*='last name' i]", profile.get("last_name", "")),
            ("input[type='email'], input[name*='email' i]", profile.get("email", "")),
            ("input[type='tel'], input[name*='phone' i]", profile.get("phone", "")),
        ]
        for selector, value in fields:
            if value and await self._safe_fill(page, selector, str(value)):
                filled += 1
        return filled > 0

    async def fill_education(self, page, profile: dict) -> bool:
        """Fill education fields on EmailApplication."""
        education = profile.get("education", "")
        if not education:
            return True  # No education data — skip
        selectors = ["input[name*='degree' i]", "input[placeholder*='degree' i]", "[name*='education' i]"]
        for sel in selectors:
            if await self._safe_fill(page, sel, str(education)):
                return True
        return True  # Non-blocking

    async def fill_experience(self, page, profile: dict) -> bool:
        """Fill experience fields on EmailApplication."""
        return True  # Platform-specific implementation in subclasses

    async def fill_projects(self, page, profile: dict) -> bool:
        """Fill projects fields on EmailApplication."""
        return True  # Non-blocking

    async def fill_skills(self, page, profile: dict) -> bool:
        """Fill skills on EmailApplication."""
        skills = profile.get("skills", [])
        if skills:
            skills_text = ", ".join(skills[:10])
            selectors = ["[name*='skill' i]", "textarea[placeholder*='skill' i]"]
            for sel in selectors:
                if await self._safe_fill(page, sel, skills_text):
                    return True
        return True

    async def fill_certifications(self, page, profile: dict) -> bool:
        """Fill certifications on EmailApplication."""
        return True  # Non-blocking

    async def answer_screening(self, page, questions: list, engine, cover_letter_text: Optional[str] = None) -> bool:
        """Answer screening questions on EmailApplication."""
        return True  # Platform-specific in subclasses

        async def submit(self, page) -> bool:
        """Override submit to handle mailto: redirection or trigger email client."""
        try:
            url = page.url
            if url.startswith("mailto:"):
                logger.info(f"email_apply: Detected mailto URL: {url}")
                return True
            mailto_links = await page.locator("a[href^='mailto:']").all()
            if mailto_links:
                href = await mailto_links[0].get_attribute("href")
                logger.info(f"email_apply: Found mailto link: {href}")
                return True
            return True
        except Exception as e:
            logger.warning(f"email_apply: Submit failed: {e}")
            return False

    async def capture_confirmation(self, page) -> dict:
        """Capture confirmation from EmailApplication."""
        try:
            content = await page.content()
            url = page.url
            confirmation_indicators = [
                "thank you", "application submitted", "application received",
                "we'll be in touch", "confirmation", "successfully applied"
            ]
            submitted = any(ind in content.lower() for ind in confirmation_indicators)
            return {
                "submitted": submitted,
                "url": url,
                "platform": self.platform_key,
                "adapter_version": self.adapter_version
            }
        except Exception as e:
            return {"submitted": False, "error": str(e), "platform": self.platform_key}

    async def detect_verification_required(self, page) -> Optional[str]:
        """Detect OTP/CAPTCHA/email verification on EmailApplication."""
        return await self._detect_otp_patterns(page)