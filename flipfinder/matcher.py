"""Works out which watchlist item (if any) a deal title is for."""
import re

# Words that mean "this isn't the actual item" whatever the category.
GLOBAL_EXCLUDE = [
    "faulty", "spares", "repairs", "for parts", "broken", "not working",
    "box only", "empty box", "replica", "dummy", "display model only",
    "skin", "decal", "wanted", "swap",
]


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9.+()'\- ]", " ", text)
    return re.sub(r"\s+", " ", text)


def has_term(text: str, term: str) -> bool:
    """True if term appears as a whole term.

    Letters must not run on from letters, digits must not run on from
    digits - so 'pro' won't match 'professional', 'iphone 16' won't match
    'iphone 160', but model code 'dcd796' DOES match 'dcd796n'.
    """
    term = _normalise(term).strip()
    if not term:
        return False
    left = r"(?<![a-z])" if term[0].isalpha() else (r"(?<![0-9])" if term[0].isdigit() else "")
    right = r"(?![a-z])" if term[-1].isalpha() else (r"(?![0-9])" if term[-1].isdigit() else "")
    return re.search(left + re.escape(term) + right, text) is not None


def matches(title: str, item) -> bool:
    text = _normalise(title)
    for group in item.must_include:
        if not any(has_term(text, alt) for alt in group):
            return False
    for bad in item.exclude + GLOBAL_EXCLUDE:
        if has_term(text, bad):
            return False
    return True


def find_item(title: str, watchlist: list):
    """Return the most specific matching item, or None."""
    hits = [i for i in watchlist if matches(title, i)]
    if not hits:
        return None
    # Most specific = the one with the most required terms.
    return max(hits, key=lambda i: len(i.must_include))
