import json
import re
import urllib.request
from job_agent import extract_fields, fetch_original_link, enrich_job_from_page


# Domains that are social/noise — never treat as apply links
_SKIP_DOMAINS = {
    "t.me", "telegram.me", "telegram.dog",
    "whatsapp.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "play.google.com",
    "youtube.com", "youtu.be",
    "yt.openinapp.co", "openinapp.co",
}


def _is_skippable_url(url: str) -> bool:
    url_lower = url.lower()
    if "/premium" in url_lower:
        return True
    return any(d in url_lower for d in _SKIP_DOMAINS)


def extract_urls(text: str) -> list:
    url_pattern = r'https?://[^\s\)\]>"\']+'
    urls = re.findall(url_pattern, text)
    seen = set()
    deduped = []
    for u in urls:
        u_clean = u.rstrip(".,;*\"-")
        if u_clean not in seen:
            seen.add(u_clean)
            deduped.append(u_clean)
    return deduped


def _is_url_only(text: str) -> bool:
    """Return True when the message body is essentially just one URL and nothing else."""
    stripped = text.strip()
    # Remove all URLs and see if meaningful text remains
    no_urls = re.sub(r'https?://\S+', '', stripped).strip()
    return len(no_urls) < 15  # fewer than 15 non-URL chars → URL-only message


def _scrape_job_from_url(url: str) -> dict:
    """
    When a message only contains a URL, resolve it and scrape the landing
    page to get title + company. Returns a job dict or empty dict.
    """
    try:
        resolved = fetch_original_link(url)
        if resolved == "unresolved":
            resolved = url
        job_stub = {
            "apply_link": url,
            "original_link": resolved,
            "title": "N/A", "company": "N/A", "location": "N/A",
            "experience": "N/A", "skills": "N/A", "salary": "N/A", "email": "N/A",
        }
        enriched = enrich_job_from_page(job_stub)
        return enriched
    except Exception:
        return {}


def extract_multiple_jobs_fallback(text: str) -> list:
    urls = extract_urls(text)
    if not urls:
        return []

    # ── URL-only messages: scrape the page directly ───────────────────────────
    if _is_url_only(text):
        jobs = []
        for url in urls:
            if _is_skippable_url(url):
                continue
            job = _scrape_job_from_url(url)
            if job and job.get("title") not in ("N/A", "", None):
                jobs.append(job)
        return jobs

    # ── Normal text messages: split into context blocks by URL positions ──────
    lines = text.split("\n")
    jobs = []

    # Map each URL to its first line index in the message text
    url_indices = []
    for url in urls:
        for idx, line in enumerate(lines):
            if url in line:
                url_indices.append((url, idx))
                break

    # Sort URLs by appearance order in text
    url_indices.sort(key=lambda x: x[1])

    last_idx = 0
    for i, (url, idx) in enumerate(url_indices):
        if _is_skippable_url(url):
            continue

        # Each job block spans from the end of the previous URL block to the current URL line
        if i < len(url_indices) - 1:
            next_idx = url_indices[i + 1][1]
            block_lines = lines[last_idx:next_idx]
            last_idx = next_idx
        else:
            block_lines = lines[last_idx:]

        block_text = "\n".join(block_lines)
        fields = extract_fields(block_text)
        fields["apply_link"] = url

        # Fall back to whole-text fields for any missing metadata
        whole_fields = extract_fields(text)
        for key in ["title", "company", "location", "experience", "skills", "salary", "email"]:
            if fields.get(key) in ("N/A", "", None):
                fields[key] = whole_fields.get(key, "N/A")

        jobs.append(fields)

    return jobs


def extract_job_details_with_ai(text: str, gemini_api_key: str = "") -> list:
    """
    Extracts structured job details (list of dicts) from text using the Gemini
    API. Falls back to deterministic rule-based parser when the key is absent
    or the call fails.
    """
    if not gemini_api_key:
        return extract_multiple_jobs_fallback(text)

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={gemini_api_key}"
    )
    headers = {"Content-Type": "application/json"}

    prompt = f"""
You are an expert job parser. Extract ALL individual job listings from the text below.

For URL-only messages (where the text is just a job link), return the URL as apply_link
and set title/company/location etc. to "SCRAPE" so the system knows to scrape the page.

For each job extract:
- title
- company
- location
- experience
- skills (comma-separated)
- salary
- apply_link (specific URL for this job)
- email

Rules:
- If a field is not present, use "N/A".
- Skip social/share links (LinkedIn posts, YouTube, WhatsApp, Telegram).
- Respond ONLY with a valid JSON array. No markdown, no backticks.

Text:
{text}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            json_text = (
                res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            )
            extracted = json.loads(json_text)
            if not isinstance(extracted, list):
                extracted = [extracted]

            required_keys = [
                "title", "company", "location", "experience",
                "skills", "salary", "apply_link", "email",
            ]
            for item in extracted:
                for key in required_keys:
                    if key not in item:
                        item[key] = "N/A"

            # If Gemini flagged title as "SCRAPE", scrape the page now
            result = []
            for item in extracted:
                if item.get("title") == "SCRAPE" and item.get("apply_link", "N/A") != "N/A":
                    scraped = _scrape_job_from_url(item["apply_link"])
                    if scraped and scraped.get("title") not in ("N/A", "", None):
                        result.append(scraped)
                else:
                    result.append(item)
            return result

    except Exception as e:
        print(
            f"[WARNING] Gemini API extraction failed, using rule-based fallback. "
            f"Error: {e}"
        )
        return extract_multiple_jobs_fallback(text)
