"""Custom vocabulary processing for improved transcription accuracy."""

from __future__ import annotations

import re
from pathlib import Path


class VocabularyProcessor:
    """Handles custom vocabulary injection and post-processing."""

    def __init__(self, terms: list[str]):
        self.terms = sorted(set(terms), key=len, reverse=True)
        # Build regex patterns for fuzzy matching
        self._patterns: list[tuple[re.Pattern, str]] = []
        for term in self.terms:
            # Create case-insensitive pattern that matches the term
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            self._patterns.append((pattern, term))

    @staticmethod
    def load_file(path: Path) -> list[str]:
        """Load vocabulary terms from a file (one term per line)."""
        terms = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    terms.append(line)
        return terms

    def as_prompt(self) -> str:
        """Generate an initial prompt string from vocabulary terms.

        Whisper uses the initial prompt for context, improving recognition
        of domain-specific terms.
        """
        # Limit to avoid exceeding prompt length
        selected = self.terms[:50]
        return "Vocabulary: " + ", ".join(selected) + "."

    def apply(self, text: str) -> str:
        """Apply vocabulary corrections to transcribed text."""
        for pattern, correct_term in self._patterns:
            text = pattern.sub(correct_term, text)
        return text
