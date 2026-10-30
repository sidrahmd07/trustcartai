"""Turn a messy Hinglish question into a structured QueryFrame (what is asked + which products)."""
import difflib
import re
from dataclasses import dataclass, field

from trustcart.catalogue import Catalogue
from trustcart.lexicon import (ACCESSORY_WORDS, ATTRIBUTE_RULES, BUDGET_PATTERNS, COMPARE_SPLIT, CONTEXT_WORDS,
                               DISCOUNT_WORDS, FUNCTION_WORDS, IN_STOCK_FILTER, LIST_WORDS, OUT_OF_CATALOGUE_WORDS,
                               PRICE_WORDS, STOCK_WORDS, SUPER_MAX, SUPER_MIN)
from trustcart.textnorm import is_number, normalise, tokenize

SOFT_TOKENS = {"men", "women", "unisex", "boy", "girl", "kid", "wala", "pro", "bag"}
_FUZZY_CUTOFF = 0.82
_BRAND_CUTOFF = 0.72


@dataclass
class QueryFrame:
    text: str
    tokens: list[str] = field(default_factory=list)        # content tokens that identify products
    unknown: list[str] = field(default_factory=list)       # words the catalogue has never seen
    budget: int | None = None
    asked: str = "list"            # price | stock | discount | attribute | superlative | list
    attr_keys: tuple[str, ...] = ()
    superlative: str | None = None  # min | max
    want_in_stock: bool = False
    parts: list[list[str]] = field(default_factory=list)   # token groups when comparing two products
    laptop_inches: float | None = None
    size_request: str | None = None
    out_of_catalogue: bool = False
    refers_back: bool = False
    has_subject: bool = False       # question names a product type (so it is not a follow-up)


def _budget(low: str) -> tuple[int | None, str]:
    for rx in BUDGET_PATTERNS:
        m = rx.search(low)
        if m:
            value = float(m.group(1)) * (1000 if m.group(2) else 1)
            return int(value), low[:m.start()] + " " + low[m.end():]
    return None, low


def _attribute_keys(low: str) -> tuple[tuple[str, ...], str]:
    keys: tuple[str, ...] = ()
    for rx, found, consume in ATTRIBUTE_RULES:
        if re.search(rx, low):
            keys = keys or found
            if consume:
                low = re.sub(rx, " ", low)
    return keys, low


class QueryParser:
    def __init__(self, catalogue: Catalogue, ordinary_words: set[str] | None = None) -> None:
        self.cat = catalogue
        self.ordinary = ordinary_words or set()   # words from the store policy are never brand typos
        self._vocab_list = sorted(catalogue.vocab)
        self._brand_list = sorted(catalogue.brand_tokens)

    def _fix_token(self, tok: str) -> str | None:
        """Map a token to the catalogue vocabulary (typo tolerant); None when unknown."""
        if tok in self.cat.vocab:
            return tok
        if is_number(tok) or len(tok) < 4:
            return None
        if tok in self.ordinary:
            return None
        hit = difflib.get_close_matches(tok, self._brand_list, n=1, cutoff=_BRAND_CUTOFF)
        if hit:
            return hit[0]
        for brand in self._brand_list:
            if len(tok) >= 5 and brand.startswith(tok[:4]) and difflib.SequenceMatcher(None, tok, brand).ratio() >= 0.6:
                return brand
        hit = difflib.get_close_matches(tok, self._vocab_list, n=1, cutoff=_FUZZY_CUTOFF)
        return hit[0] if hit else None

    def _join_adjacent(self, toks: list[str]) -> list[str]:
        """'ripple flex' -> also 'rippleflex' ; 'ghar kraft' -> 'gharkraft' (shoppers split product names)."""
        extra: list[str] = []
        for a, b in zip(toks, toks[1:]):
            joined = a + b
            if is_number(a) or is_number(b):
                continue
            if joined in self.cat.vocab:
                extra.append(joined)
            elif len(joined) >= 8:
                hit = difflib.get_close_matches(joined, self._vocab_list, n=1, cutoff=0.88)
                if hit:
                    extra.append(hit[0])
        return extra

    def content_tokens(self, low: str) -> tuple[list[str], list[str]]:
        raw = [t for t in tokenize(low) if t not in FUNCTION_WORDS]
        joins = self._join_adjacent(tokenize(low))
        fixed: list[str] = []
        unknown: list[str] = []
        for tok in raw + joins:
            hit = self._fix_token(tok)
            if hit:
                fixed.append(hit)
            elif tok not in joins:
                unknown.append(tok)
        merged = set(fixed)
        for tok in joins:                      # 'urban loom' -> brand 'urbanloom': its halves are not words of their own
            if tok in self.cat.brand_tokens:
                for a, b in zip(raw, raw[1:]):
                    if a + b == tok:
                        merged.discard(a)
                        merged.discard(b)
        # a joined number+unit token ('3l') replaces its parts ('3', 'l') so they are not scored twice
        for tok in list(merged):
            m = re.fullmatch(r"(\d+(?:\.\d+)?)(l|ml|cm|mm|kg|g|w|mah|in|pc|ft|ton)", tok)
            if m:
                merged.discard(m.group(1))
                merged.discard(m.group(2))
        unknown = [u for u in unknown if not any(u in j and len(j) > len(u) for j in merged)]
        unit_parts = {u for u in unknown if re.fullmatch(r"\d+(?:\.\d+)?(?:l|ml|cm|mm|kg|g|w|mah|in|pc|ft|ton)", u)}
        number_parts = {re.match(r"\d+(?:\.\d+)?", u).group(0) for u in unit_parts}
        unknown = [u for u in dict.fromkeys(unknown) if len(u) > 2 and not (u in number_parts or u in {"l", "ml", "cm", "mm", "kg", "g", "w", "mah", "in", "pc", "ft", "ton"})]
        return sorted(merged), unknown

    def parse(self, text: str) -> QueryFrame:
        low = normalise(text)
        frame = QueryFrame(text=text)
        frame.budget, low = _budget(low)
        frame.attr_keys, low_noattr = _attribute_keys(low)
        frame.superlative = "min" if SUPER_MIN.search(low) else "max" if SUPER_MAX.search(low) else None
        frame.want_in_stock = bool(IN_STOCK_FILTER.search(low))
        frame.refers_back = bool(set(low.split()) & CONTEXT_WORDS)
        laptop_in = re.search(r"(\d+(?:\.\d+)?)\s*in(?:ch)?\b", low)
        if laptop_in and "laptop" in low:
            frame.laptop_inches = float(laptop_in.group(1))
            low_noattr = low_noattr.replace(laptop_in.group(0), " ")
        size = re.search(r"(\d+)\s*(?:-|se|to)?\s*(\d+)\s*(?:years|year|saal|sal|yrs|y)\b", low)
        if size:
            frame.size_request = f"{size.group(1)}-{size.group(2)}Y"
            low_noattr = low_noattr.replace(size.group(0), " ")
        frame.tokens, frame.unknown = self.content_tokens(low_noattr)
        self._laptop_filters(frame, low)
        words = set(tokenize(low_noattr))
        banned = OUT_OF_CATALOGUE_WORDS & words
        frame.out_of_catalogue = bool(banned) and not (words & ACCESSORY_WORDS) and "@laptop" not in frame.tokens
        frame.has_subject = any(t in self.cat.sub_category_tokens and t not in self.cat.brand_tokens for t in frame.tokens)
        frame.asked = self._asked(low, frame)
        if frame.asked != "list" or COMPARE_SPLIT.search(" " + low + " "):
            frame.parts = self._compare_parts(low_noattr)
        return frame

    @staticmethod
    def _laptop_filters(frame: QueryFrame, low: str) -> None:
        """'laptop wala backpack' means a bag WITH a laptop compartment, not a laptop (carried as pseudo-tokens)."""
        if "laptop" in frame.tokens and ("backpack" in frame.tokens or "bag" in frame.tokens) and "sleeve" not in frame.tokens:
            frame.tokens = [t for t in frame.tokens if t != "laptop"] + ["@laptop"]
        if frame.laptop_inches is not None and not frame.attr_keys:
            frame.tokens = [t for t in frame.tokens if t != "laptop"] + ["@laptop", f"@laptop_in:{frame.laptop_inches}"]

    @staticmethod
    def _asked(low: str, frame: QueryFrame) -> str:
        if frame.attr_keys:
            return "attribute"
        if frame.superlative:
            return "superlative"
        if DISCOUNT_WORDS.search(low):
            return "discount"
        if frame.budget is not None or LIST_WORDS.search(low):
            return "list"
        if STOCK_WORDS.search(low):
            return "stock"
        if PRICE_WORDS.search(low):
            return "price"
        return "list"

    def _compare_parts(self, low: str) -> list[list[str]]:
        pieces = [p for p in COMPARE_SPLIT.split(" " + low + " ") if p.strip()]
        if len(pieces) < 2:
            return []
        parts = [self.content_tokens(p)[0] for p in pieces]
        subject = sorted({t for part in parts for t in part if t in self.cat.sub_category_tokens and t not in self.cat.brand_tokens})
        brand_line: list[str] = []
        out: list[list[str]] = []
        for part in parts:
            if not part:
                continue
            has_brand = any(t in self.cat.brand_tokens for t in part)
            merged = set(part) | set(subject)
            if not has_brand and brand_line:
                merged |= set(brand_line)
            if has_brand:
                brand_line = [t for t in part if t not in self.cat.sub_category_tokens and t not in self.cat.colours]
            out.append(sorted(merged))
        return out if len(out) >= 2 else []
