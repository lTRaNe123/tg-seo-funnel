import re
import unicodedata
from typing import Dict

_TRANSLIT = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y",
    "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
    "х":"h","ц":"ts","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
}

def title_case_ru(text: str) -> str:
    """Каждое слово с заглавной — как в примере."""
    words = re.split(r"\s+", text.strip())
    out = []
    for w in words:
        if not w:
            continue
        out.append(w[:1].upper() + w[1:])
    return " ".join(out) or "Подробнее"

def slugify_ru(text: str) -> str:
    """
    Русский заголовок -> латинский slug:
    - lower
    - транслит
    - пробелы/пунктуация -> '-'
    - сжатие дефисов
    """
    t = unicodedata.normalize("NFKD", text.strip().lower())
    out = []
    for ch in t:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif "a" <= ch <= "z" or "0" <= ch <= "9":
            out.append(ch)
        else:
            out.append("-")
    s = "".join(out)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "page"

def ensure_unique_slug(slug: str, used: Dict[str, int]) -> str:
    if slug not in used:
        used[slug] = 1
        return slug
    used[slug] += 1
    return f"{slug}-{used[slug]}"
