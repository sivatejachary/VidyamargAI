"""
Comeet Adapter — Auto Apply implementation for Comeet.
"""
import logging
from typing import Optional
from app.services.auto_apply.adapters.base import BaseApplicationAdapter

logger = logging.getLogger(__name__)


class ComeetAdapter(BaseApplicationAdapter):
    adapter_version: str = "comeet:1.0"
    platform_key: str = "comeet"
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
        """Create new account on Comeet."""
        logger.info(f"{self.platform_key}: Account creation not yet automated — returning empty.")
        return {}

    async def upload_resume(self, page, resume_bytes: bytes, filename: str) -> bool:
        """Upload resume to Comeet file upload field."""
        try:
            # Common resume upload selectors across ATS platforms
            upload_selectors = [
                "input[type='file']",
                "input[accept*='pdf']",
                "input[accept*='.pdf']",
                "[data-testid*='resume']",
                "[aria-label*='resume' i]",
                "[aria-label*='cv' i]",
            ]
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=f"_{filename}", delete=False) as f:
                f.write(resume_bytes)
                tmp_path = f.name
            try:
                for selector in upload_selectors:
                    try:
                        await page.set_input_files(selector, tmp_path)
                        logger.info(f"{self.platform_key}: Resume uploaded via {selector}")
                        return True
                    except Exception:
                        continue
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"{self.platform_key}: Resume upload failed: {e}")
        return False

    async def fill_personal_details(self, page, profile: dict) -> bool:
        """Fill personal details on Comeet."""
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
        """Fill education fields on Comeet."""
        education = profile.get("education", "")
        if not education:
            return True  # No education data — skip
        selectors = ["input[name*='degree' i]", "input[placeholder*='degree' i]", "[name*='education' i]"]
        for sel in selectors:
            if await self._safe_fill(page, sel, str(education)):
                return True
        return True  # Non-blocking

    async def fill_experience(self, page, profile: dict) -> bool:
        """Fill experience fields on Comeet."""
        return True  # Platform-specific implementation in subclasses

    async def fill_projects(self, page, profile: dict) -> bool:
        """Fill projects fields on Comeet."""
        return True  # Non-blocking

    async def fill_skills(self, page, profile: dict) -> bool:
        """Fill skills on Comeet."""
        skills = profile.get("skills", [])
        if skills:
            skills_text = ", ".join(skills[:10])
            selectors = ["[name*='skill' i]", "textarea[placeholder*='skill' i]"]
            for sel in selectors:
                if await self._safe_fill(page, sel, skills_text):
                    return True
        return True

    async def fill_certifications(self, page, profile: dict) -> bool:
        """Fill certifications on Comeet."""
        return True  # Non-blocking

    async def answer_screening(self, page, questions: list, engine, cover_letter_text: Optional[str] = None) -> bool:
        """Answer screening questions on Comeet."""
        return True  # Platform-specific in subclasses

    async def submit(self, page) -> bool:
        """Submit application on Comeet."""
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Send Application')",
            "[data-testid*='submit' i]",
        ]
        for selector in submit_selectors:
            if await self._safe_click(page, selector):
                logger.info(f"{self.platform_key}: Application submitted via {selector}")
                return True
        return False

    async def capture_confirmation(self, page) -> dict:
        """Capture confirmation from Comeet."""
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
        """Detect OTP/CAPTCHA/email verification on Comeet."""
        return await self._detect_otp_patterns(page)