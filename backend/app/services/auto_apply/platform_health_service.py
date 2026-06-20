"""
Platform Health Service — Tracks success/failure rates per ATS platform.
Auto-disables adapters when success_rate drops below the configured threshold.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)


class PlatformHealthService:
    """
    Records application attempt results and evaluates platform health.
    Auto-disables platforms with < PLATFORM_DISABLE_THRESHOLD success rate
    after PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK attempts.
    """

    def record_attempt(
        self,
        platform: str,
        success: bool,
        db: Session,
        duration_seconds: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """Record one application attempt result for a platform."""
        try:
            from app.models.auto_apply_models import PlatformHealth
            health = db.query(PlatformHealth).filter_by(platform=platform).first()
            if not health:
                health = PlatformHealth(
                    platform=platform,
                    total_attempts=0,
                    total_successes=0,
                    total_failures=0,
                    success_rate=1.0,
                    avg_duration_seconds=0.0
                )
                db.add(health)

            health.total_attempts += 1
            if success:
                health.total_successes += 1
                health.last_success = datetime.utcnow()
            else:
                health.total_failures += 1
                health.last_failure = datetime.utcnow()
                if error:
                    health.last_error = str(error)[:1000]

            # Recompute success_rate
            if health.total_attempts > 0:
                health.success_rate = health.total_successes / health.total_attempts

            # Running average for duration
            if duration_seconds > 0:
                n = health.total_attempts
                health.avg_duration_seconds = (
                    (health.avg_duration_seconds * (n - 1) + duration_seconds) / n
                )

            db.commit()
            self.evaluate_and_auto_disable(platform, db)
        except Exception as e:
            logger.error(f"Failed to record platform health for {platform}: {e}")

    def evaluate_and_auto_disable(self, platform: str, db: Session) -> None:
        """Check if this platform should be auto-disabled."""
        try:
            from app.models.auto_apply_models import PlatformHealth
            health = db.query(PlatformHealth).filter_by(platform=platform).first()
            if not health or health.is_disabled:
                return

            threshold = getattr(settings, "PLATFORM_DISABLE_THRESHOLD", 0.20)
            min_attempts = getattr(settings, "PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK", 10)

            if (health.total_attempts >= min_attempts
                    and health.success_rate < threshold):
                health.is_disabled = True
                health.disabled_at = datetime.utcnow()
                health.disabled_reason = (
                    f"Auto-disabled: success rate {health.success_rate:.1%} "
                    f"< {threshold:.0%} threshold after {health.total_attempts} attempts."
                )
                db.commit()
                logger.warning(
                    f"Platform '{platform}' auto-disabled: {health.success_rate:.1%} success rate."
                )
                self._send_admin_alert(platform, health)
        except Exception as e:
            logger.error(f"Failed to evaluate platform health for {platform}: {e}")

    def is_platform_enabled(self, platform: str, db: Session) -> bool:
        """Returns True if platform is healthy and not disabled."""
        try:
            from app.models.auto_apply_models import PlatformHealth
            health = db.query(PlatformHealth).filter_by(platform=platform).first()
            if not health:
                return True  # New platform — assume healthy
            return not health.is_disabled
        except Exception:
            return True  # Fail open

    def re_enable(self, platform: str, db: Session) -> None:
        """Manually re-enable a disabled platform."""
        try:
            from app.models.auto_apply_models import PlatformHealth
            health = db.query(PlatformHealth).filter_by(platform=platform).first()
            if health:
                health.is_disabled = False
                health.disabled_at = None
                health.disabled_reason = None
                # Reset counters to give a fresh start
                health.total_attempts = 0
                health.total_successes = 0
                health.total_failures = 0
                health.success_rate = 1.0
                db.commit()
        except Exception as e:
            logger.error(f"Failed to re-enable platform {platform}: {e}")

    def _send_admin_alert(self, platform: str, health) -> None:
        """Log admin alert. Can be extended to send email/Slack/webhook."""
        logger.error(
            f"[ADMIN ALERT] Platform '{platform}' has been auto-disabled. "
            f"Success rate: {health.success_rate:.1%}, "
            f"Attempts: {health.total_attempts}, "
            f"Last error: {health.last_error}"
        )


# Module-level singleton
platform_health_service = PlatformHealthService()