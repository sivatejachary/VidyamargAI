"""
Platform Adapter Registry.
Maps platform keys to adapter classes and provides URL-based platform detection.
LinkedIn is intentionally absent from the registry — it is discovery-only.
"""
import re
from typing import Type, Optional

from app.services.auto_apply.adapters.base import BaseApplicationAdapter

# Ordered URL detection rules: (regex pattern, platform_key)
# Evaluated top-to-bottom — first match wins.
_DETECTION_RULES = [
    (r"boards\.greenhouse\.io|app\.greenhouse\.io", "greenhouse"),
    (r"jobs\.lever\.co", "lever"),
    (r"myworkdayjobs\.com|workday\.com/en-US/careers", "workday"),
    (r"jobs\.ashbyhq\.com", "ashby"),
    (r"jobs\.smartrecruiters\.com", "smartrecruiters"),
    (r"icims\.com", "icims"),
    (r"jobs\.jobvite\.com|jobvite\.com/careers", "jobvite"),
    (r"successfactors\.com|sapsf\.com", "successfactors"),
    (r"taleo\.net", "taleo"),
    (r"oraclecloud\.com.*hcm|oracle\.com.*recruit", "oracle_hcm"),
    (r"bamboohr\.com/careers", "bamboohr"),
    (r"teamtailor\.com", "teamtailor"),
    (r"recruitee\.com", "recruitee"),
    (r"comeet\.co", "comeet"),
    (r"zohorecruit\.com|recruit\.zoho\.com", "zoho_recruit"),
    (r"docs\.google\.com/forms", "google_forms"),
    (r"forms\.office\.com|forms\.microsoft\.com", "microsoft_forms"),
    (r"typeform\.com", "typeform"),
    (r"^mailto:", "email_apply"),
]


def detect_platform(url: str) -> str:
    """
    Detect the ATS platform from a job application URL.
    Returns a platform key string. Returns 'generic' if no pattern matches.
    LinkedIn URLs return 'linkedin' but LinkedInAdapter is NOT in the registry.
    """
    if not url:
        return "generic"
    url_lower = url.lower().strip()
    if "linkedin.com" in url_lower:
        return "linkedin"  # Not in registry — handled as redirect-only
    for pattern, key in _DETECTION_RULES:
        if re.search(pattern, url_lower):
            return key
    return "generic"


def load_adapter(platform: str) -> "BaseApplicationAdapter":
    """
    Load the adapter instance for a given platform key.
    Falls back to GenericWebsiteAdapter for unknown/unsupported platforms.
    LinkedIn is excluded — always falls back to generic.
    """
    from app.services.auto_apply.adapters.greenhouse import GreenhouseAdapter
    from app.services.auto_apply.adapters.lever import LeverAdapter
    from app.services.auto_apply.adapters.workday import WorkdayAdapter
    from app.services.auto_apply.adapters.ashby import AshbyAdapter
    from app.services.auto_apply.adapters.smartrecruiters import SmartRecruitersAdapter
    from app.services.auto_apply.adapters.icims import ICIMSAdapter
    from app.services.auto_apply.adapters.jobvite import JobviteAdapter
    from app.services.auto_apply.adapters.successfactors import SuccessFactorsAdapter
    from app.services.auto_apply.adapters.taleo import TaleoAdapter
    from app.services.auto_apply.adapters.oracle_hcm import OracleHCMAdapter
    from app.services.auto_apply.adapters.bamboohr import BambooHRAdapter
    from app.services.auto_apply.adapters.teamtailor import TeamtailorAdapter
    from app.services.auto_apply.adapters.recruitee import RecruiteeAdapter
    from app.services.auto_apply.adapters.comeet import ComeetAdapter
    from app.services.auto_apply.adapters.zoho_recruit import ZohoRecruitAdapter
    from app.services.auto_apply.adapters.google_forms import GoogleFormsAdapter
    from app.services.auto_apply.adapters.microsoft_forms import MicrosoftFormsAdapter
    from app.services.auto_apply.adapters.typeform import TypeformAdapter
    from app.services.auto_apply.adapters.email_apply import EmailApplicationAdapter
    from app.services.auto_apply.adapters.generic import GenericWebsiteAdapter

    PLATFORM_REGISTRY: dict[str, Type[BaseApplicationAdapter]] = {
        "greenhouse": GreenhouseAdapter,
        "lever": LeverAdapter,
        "workday": WorkdayAdapter,
        "ashby": AshbyAdapter,
        "smartrecruiters": SmartRecruitersAdapter,
        "icims": ICIMSAdapter,
        "jobvite": JobviteAdapter,
        "successfactors": SuccessFactorsAdapter,
        "taleo": TaleoAdapter,
        "oracle_hcm": OracleHCMAdapter,
        "bamboohr": BambooHRAdapter,
        "teamtailor": TeamtailorAdapter,
        "recruitee": RecruiteeAdapter,
        "comeet": ComeetAdapter,
        "zoho_recruit": ZohoRecruitAdapter,
        "google_forms": GoogleFormsAdapter,
        "microsoft_forms": MicrosoftFormsAdapter,
        "typeform": TypeformAdapter,
        "email_apply": EmailApplicationAdapter,
        "generic": GenericWebsiteAdapter,
        # "linkedin" intentionally absent — discovery only, no auto-apply
    }
    adapter_class = PLATFORM_REGISTRY.get(platform, GenericWebsiteAdapter)
    return adapter_class()