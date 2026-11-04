"""Arabic: right-to-left; short vowels (harakat) are usually optional."""

from __future__ import annotations

from langex.languages.domain.normalization import BaseNormalizer
from langex.languages.domain.profile import LanguageProfile, TextDirection
from langex.shared_kernel.language import LanguageCode

_TATWEEL = "ـ"  # decorative stretching, never meaningful

# Common letter variants learners mix up; accepted as CLOSE, not EXACT.
_LETTER_VARIANTS = str.maketrans(
    {
        "أ": "ا",  # أ -> ا
        "إ": "ا",  # إ -> ا
        "آ": "ا",  # آ -> ا
        "ٱ": "ا",  # ٱ -> ا
        "ى": "ي",  # ى -> ي
        "ة": "ه",  # ة -> ه
        "ؤ": "و",  # ؤ -> و
        "ئ": "ي",  # ئ -> ي
    }
)


class ArabicNormalizer(BaseNormalizer):
    def strict(self, text: str) -> str:
        return super().strict(text.replace(_TATWEEL, ""))

    def lenient(self, text: str) -> str:
        # Map variants before the base step strips hamza marks.
        return super().lenient(self.strict(text).translate(_LETTER_VARIANTS))


PROFILE = LanguageProfile(
    code=LanguageCode("ar"),
    english_name="Arabic",
    native_name="العربية",
    direction=TextDirection.RTL,
    scripts=("Arab",),
    normalizer=ArabicNormalizer(),
)
