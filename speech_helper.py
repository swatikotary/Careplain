"""Gemini TTS helper for on-demand report narration."""

import base64

from google import genai
from google.genai import types


TTS_MODEL = "gemini-3.8-flash-lite-tts"
DEFAULT_VOICE = "Kore"


def synthesize_narration(text, api_key, voice=DEFAULT_VOICE):
    """Generate a WAV narration from the exact explanation supplied by the app."""
    if not api_key:
        raise ValueError("Gemini API key is required for voice narration.")
    if not text or not text.strip():
        raise ValueError("There is no explanation text to narrate.")

    # Gemini 3.8 TTS is currently served by the Gemini API v1beta endpoint.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            api_version="v1beta",
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    transcript = types.Part(
        text=text.strip(),
        speech_metadata=types.SpeechMetadata(
            style=(
                "Calm, clear, respectful patient-education narration. "
                "Use a measured pace and pronounce medical terms carefully."
            )
        ),
    )
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=types.Content(role="user", parts=[transcript]),
        config=types.GenerateContentConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        ),
    )

    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None)
            if data:
                if isinstance(data, str):
                    data = base64.b64decode(data)
                mime_type = getattr(inline_data, "mime_type", None) or "audio/wav"
                return data, mime_type

    raise ValueError("Gemini returned no audio data for the narration.")
