"""Small, privacy-conscious helpers for per-session API result caching."""

import hashlib
import json

from prompts import PROMPTS


def content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def explanation_cache_key(report_text, prompt_version, report_type,
                          reading_level, language):
    """Key an explanation by its inputs, without including an API key."""
    payload = {
        "report_hash": content_hash(report_text),
        "prompt_version": prompt_version,
        "report_type": report_type,
        "reading_level": reading_level,
        "language": language,
        # Conservatively invalidate cached explanations if any prompt changes.
        "prompt_library_hash": content_hash(json.dumps(PROMPTS, sort_keys=True)),
        "cache_revision": 1,
    }
    return content_hash(json.dumps(payload, sort_keys=True))


def get_or_create(cache, key, create):
    """Return (value, cache_hit); create and store a value on a miss."""
    if key in cache:
        return cache[key], True
    value = create()
    cache[key] = value
    return value, False


def is_usable_explanation(text):
    """Reject empty or punctuation-only model responses before caching them."""
    if not isinstance(text, str):
        return False
    return sum(character.isalnum() for character in text) >= 40


def is_quota_exhaustion(error):
    """Recognize hard Gemini quota/rate exhaustion without retrying it."""
    message = str(error).casefold()
    if any(marker in message for marker in (
        "resource_exhausted", "429", "generate_content_free_tier_requests",
    )):
        return True
    return any(marker in message for marker in (
        "requests per day",
        "per day",
    )) and "quota" in message
