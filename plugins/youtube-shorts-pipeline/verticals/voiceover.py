"""Legacy voiceover module — delegates to tts.py.

Kept for backward compatibility with existing produce/assemble calls.
"""

from pathlib import Path
from .tts import generate_voiceover

__all__ = ["generate_voiceover"]
