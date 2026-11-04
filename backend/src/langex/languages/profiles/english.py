"""English: used as a bridge language for glosses between partners."""

from langex.languages.domain.profile import LanguageProfile, TextDirection
from langex.shared_kernel.language import LanguageCode

PROFILE = LanguageProfile(
    code=LanguageCode("en"),
    english_name="English",
    native_name="English",
    direction=TextDirection.LTR,
    scripts=("Latn",),
)
