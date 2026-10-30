"""Text normalisation shared by the catalogue index and the question parser."""
import re
import unicodedata

_SYNONYMS = {
    "tshirt": "t-shirt", "tshirts": "t-shirt", "t-shirts": "t-shirt", "powerbank": "power bank",
    "ladies": "women", "lady": "women", "womens": "women", "mens": "men", "gents": "men",
    "boy": "boys", "girl": "girls", "bacche": "kids", "bachon": "kids", "bacchon": "kids", "bachcho": "kids",
    "litre": "l", "liter": "l", "ltr": "l", "litres": "l", "liters": "l", "lit": "l",
    "watt": "w", "watts": "w", "kilo": "kg", "gram": "g", "inch": "in", "inches": "in",
    "pieces": "pc", "piece": "pc", "pcs": "pc", "pc": "pc", "chulha": "cooktop", "chappal": "chappals",
    "chappals": "chappal", "earphone": "earphones", "trimer": "trimmer",
    "facewash": "face wash", "mah": "mah", "rs": "", "rupees": "", "rupaye": "", "inr": "", "₹": "",
    "dabba": "container", "chargers": "charger", "mixer": "mixer", "cooker": "cooker",
    "saal": "years", "sal": "years", "mobile": "mobile",
}
_UNITS = {"l", "ml", "cm", "mm", "kg", "g", "w", "mah", "in", "pc", "ft", "m", "jar", "jars", "pack", "ton"}
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("₹", " ")
    text = text.replace("-", " ").replace("'", "")
    text = re.sub(r"(\w+) blend\b", r"\1blend", text)   # 'cotton blend' is a different material from 'cotton'
    text = re.sub(r"spf\s*(\d+)", r"spf\1", text)
    text = re.sub(r"pack of (\d+)", r"\1pack", text)
    text = re.sub(r"(\d+)\s*(?:wala|wali|wale)?\s*pack\b", r"\1pack", text)
    return re.sub(r"\s+", " ", text).strip()


def camel_split(text: str) -> str:
    """'RippleFlex' -> 'Ripple Flex' so product-line names match when shoppers split them."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)


def title_tokens(text: str) -> set[str]:
    return set(tokenize(text)) | set(tokenize(camel_split(text)))


def stem(tok: str) -> str:
    """Strip a plural 's' so 'mats' and 'mat' match (numbers and short tokens are left alone)."""
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") and not tok[-2].isdigit():
        return tok[:-1]
    return tok


def tokenize(text: str) -> list[str]:
    """Lower-case tokens with synonyms applied and number+unit pairs also emitted joined ('3 l' -> '3l')."""
    out: list[str] = []
    for raw in _TOKEN.findall(normalise(text)):
        for tok in _SYNONYMS.get(raw, raw).split():
            out.append(stem(tok))
    joined: list[str] = []
    for i in range(len(out) - 1):
        if re.fullmatch(r"\d+(?:\.\d+)?", out[i]) and out[i + 1] in _UNITS:
            joined.append(out[i] + out[i + 1])
    split_num = []
    for tok in out:
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(l|ml|cm|mm|kg|g|w|mah|in|pc|ft|ton)", tok)
        if m:
            split_num.extend([m.group(1), m.group(2), tok])
    return out + joined + split_num


def is_number(tok: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", tok))
