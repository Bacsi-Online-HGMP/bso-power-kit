"""Niche profile loader — reads YAML profiles and provides stage-specific context.

Each niche profile configures: script tone/hooks/CTAs, visual style/subjects,
voice pace/energy, caption styling, music mood, thumbnail strategy, and
topic discovery sources.
"""

import yaml
from pathlib import Path
from typing import Any

from .log import log

# Niche profiles live in niches/ at the project root
NICHES_DIR = Path(__file__).resolve().parent.parent / "niches"

# Cache loaded profiles to avoid re-reading YAML on every stage
_cache: dict[str, dict] = {}


def load_niche(name: str = "general") -> dict:
    """Load a niche profile by name. Returns general fallback if not found."""
    name = (name or "general").strip().lower()

    if name in _cache:
        return _cache[name]

    profile_path = NICHES_DIR / f"{name}.yaml"
    if not profile_path.exists():
        log(f"Niche profile '{name}' not found at {profile_path}")
        if name != "general":
            log("Falling back to 'general' profile")
            return load_niche("general")
        # Return minimal default if even general.yaml is missing
        return _minimal_profile(name)

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
        profile.setdefault("name", name)
        _cache[name] = profile
        log(f"Loaded niche profile: {name}")
        return profile
    except Exception as e:
        log(f"Failed to parse niche profile '{name}': {e}")
        return _minimal_profile(name)


def _minimal_profile(name: str) -> dict:
    """Bare minimum profile when YAML is missing or broken."""
    return {
        "name": name,
        "display_name": name.title(),
        "script": {
            "tone": "clear, engaging, conversational",
            "pacing": "moderate, well structured",
            "word_count": "150 to 180",
        },
        "visuals": {
            "style": "cinematic, professional",
            "prompt_suffix": "photorealistic, cinematic lighting, high quality",
        },
        "voice": {},
        "captions": {},
        "music": {},
        "thumbnail": {},
        "discovery": {},
    }


def get_script_context(profile: dict) -> str:
    """Build the script intelligence block for the LLM prompt.

    Returns a multi-line string that goes into the Claude/Gemini/GPT prompt
    to shape the script tone, hooks, structure, and CTAs.
    """
    script = profile.get("script", {})
    if not script:
        return ""

    parts = []
    parts.append(f"NICHE: {profile.get('display_name', profile.get('name', 'General'))}")

    if script.get("tone"):
        parts.append(f"TONE: {script['tone']}")
    if script.get("pacing"):
        parts.append(f"PACING: {script['pacing']}")
    if script.get("perspective"):
        parts.append(f"PERSPECTIVE: {script['perspective']}")
    if script.get("word_count"):
        parts.append(f"TARGET WORD COUNT: {script['word_count']}")
    if script.get("sentence_style"):
        parts.append(f"SENTENCE STYLE: {script['sentence_style']}")

    # Hook patterns
    hooks = script.get("hooks", [])
    if hooks:
        hook_lines = []
        for h in hooks:
            template = h.get("template", "")
            when = h.get("when", "")
            if template:
                line = f"  {h.get('id', 'hook')}: \"{template}\""
                if when:
                    line += f" (use when: {when})"
                hook_lines.append(line)
        if hook_lines:
            parts.append("HOOK PATTERNS (pick the most appropriate for this topic):")
            parts.extend(hook_lines)

    # Structure guidance
    structure = script.get("structure", {})
    if structure:
        parts.append("SCRIPT STRUCTURE:")
        if structure.get("opening"):
            parts.append(f"  Opening: {structure['opening']}")
        if structure.get("middle"):
            parts.append(f"  Middle: {structure['middle']}")
        if structure.get("closing"):
            parts.append(f"  Closing: {structure['closing']}")

    # CTA variants
    ctas = script.get("cta_variants", [])
    if ctas:
        parts.append(f"CTA OPTIONS (pick one): {', '.join(ctas)}")

    # Forbidden phrases
    forbidden = script.get("forbidden_phrases", [])
    if forbidden:
        parts.append(f"NEVER USE: {', '.join(forbidden)}")

    return "\n".join(parts)


def get_visual_context(profile: dict) -> dict:
    """Extract visual intelligence for b-roll prompt shaping.

    Returns dict with style, mood, subjects, avoid, prompt_suffix.
    """
    return profile.get("visuals", {})


def get_visual_prompt_suffix(profile: dict) -> str:
    """Get the image prompt suffix from the niche profile."""
    visuals = profile.get("visuals", {})
    return visuals.get("prompt_suffix", "photorealistic, cinematic lighting, high quality")


def get_visual_subjects(profile: dict) -> dict:
    """Get preferred and avoided visual subjects."""
    visuals = profile.get("visuals", {})
    subjects = visuals.get("subjects", {})
    return {
        "prefer": subjects.get("prefer", []),
        "avoid": subjects.get("avoid", []),
    }


def get_voice_config(profile: dict, provider: str = "edge_tts", lang: str = "en") -> dict:
    """Get voice configuration for the specified provider and language."""
    voice = profile.get("voice", {})
    suggested = voice.get("suggested_voices", {})

    config = {
        "pace": voice.get("pace", ""),
        "energy": voice.get("energy", ""),
        "style": voice.get("style", ""),
    }

    provider_voices = suggested.get(provider, {})
    if isinstance(provider_voices, dict):
        config["voice_id"] = provider_voices.get(lang, provider_voices.get("en", ""))
        # Providers that ship a single voice_id + a settings dict (rather than
        # one voice_id per language) — ElevenLabs and 60db follow this shape.
        if provider in ("elevenlabs", "60db"):
            config["voice_id"] = provider_voices.get("voice_id", "")
            config["settings"] = provider_voices.get("settings", {})
    elif isinstance(provider_voices, str):
        config["voice_id"] = provider_voices

    return config


def get_caption_config(profile: dict) -> dict:
    """Get caption styling from the niche profile."""
    defaults = {
        "highlight_color": "#FFFF00",
        "text_color": "#FFFFFF",
        "font_family": "Arial",
        "font_size": 72,
        "font_weight": "bold",
        "position": "lower_third",
        "background": "semi_transparent_dark",
        "words_per_group": 4,
    }
    captions = profile.get("captions", {})
    defaults.update(captions)
    return defaults


def get_music_config(profile: dict) -> dict:
    """Get music mood and ducking config from the niche profile."""
    defaults = {
        "mood": "ambient, subtle, no lyrics",
        "energy": "medium",
        "tags": [],
        "duck_volume_speech": 0.12,
        "duck_volume_gap": 0.25,
    }
    music = profile.get("music", {})
    defaults.update(music)
    return defaults


def get_thumbnail_config(profile: dict) -> dict:
    """Get thumbnail style guidance from the niche profile."""
    return profile.get("thumbnail", {})


def get_discovery_config(profile: dict) -> dict:
    """Get topic discovery sources from the niche profile."""
    return profile.get("discovery", {})


def list_niches() -> list[str]:
    """List all available niche profile names."""
    if not NICHES_DIR.exists():
        return ["general"]
    names = [p.stem for p in NICHES_DIR.glob("*.yaml")]
    if "general" not in names:
        names.append("general")
    return sorted(names)
