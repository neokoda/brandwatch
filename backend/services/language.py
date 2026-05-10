from lingua import Language, LanguageDetectorBuilder

_SUPPORTED = [
    Language.ENGLISH, Language.FRENCH, Language.GERMAN, Language.SPANISH,
    Language.PORTUGUESE, Language.ITALIAN, Language.ARABIC, Language.HINDI,
    Language.CHINESE, Language.JAPANESE, Language.KOREAN, Language.DUTCH,
    Language.RUSSIAN, Language.TURKISH, Language.INDONESIAN,
]

_detector = LanguageDetectorBuilder.from_languages(*_SUPPORTED).build()

_LANG_CODE_MAP = {
    Language.ENGLISH: "en",
    Language.FRENCH: "fr",
    Language.GERMAN: "de",
    Language.SPANISH: "es",
    Language.PORTUGUESE: "pt",
    Language.ITALIAN: "it",
    Language.ARABIC: "ar",
    Language.HINDI: "hi",
    Language.CHINESE: "zh",
    Language.JAPANESE: "ja",
    Language.KOREAN: "ko",
    Language.DUTCH: "nl",
    Language.RUSSIAN: "ru",
    Language.TURKISH: "tr",
    Language.INDONESIAN: "id",
}

# Languages supported by the XLM multilingual sentiment model
_XLM_SUPPORTED = {"en", "fr", "de", "es", "pt", "it", "ar", "hi"}


def detect_language(text: str) -> str | None:
    """Returns ISO 639-1 code or None if unknown."""
    lang = _detector.detect_language_of(text[:500])
    if lang is None:
        return None
    return _LANG_CODE_MAP.get(lang)


def get_sentiment_model(lang_code: str | None) -> str:
    """Return the HF model ID appropriate for this language."""
    if lang_code == "en":
        return "cardiffnlp/twitter-roberta-base-sentiment-latest"
    if lang_code in _XLM_SUPPORTED:
        return "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    return "cardiffnlp/twitter-xlm-roberta-base-sentiment"
