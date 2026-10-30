"""Find the products a question is about: hard filters, then 'best coverage' scoring over query tokens."""
from dataclasses import dataclass

from trustcart.catalogue import Catalogue
from trustcart.query import SOFT_TOKENS


@dataclass
class Match:
    ids: list[str]                 # every product tied for the best coverage (all variants kept)
    missing: list[str]             # query tokens that no matched product contains
    hard_missing: bool             # a missing token that matters (brand, colour, size ...)


def find_products(cat: Catalogue, tokens: list[str], budget: int | None = None,
                  min_laptop_in: float | None = None, in_stock_only: bool = False) -> Match:
    """Best-coverage match. Products passing the filters are scored by the IDF weight of the query tokens they contain;
    all products tied for the best score are returned, because each colour/size variant is a separate product."""
    need_laptop = "@laptop" in tokens
    for tok in tokens:
        if tok.startswith("@laptop_in:"):
            min_laptop_in = float(tok.split(":")[1])
    tokens = [t for t in tokens if not t.startswith("@")]
    if not tokens:
        return Match([], [], True)
    pool: set[str] = set()
    for tok in tokens:
        pool.update(cat.inverted.get(tok, ()))
    kept: list[str] = []
    for pid in pool:
        p = cat.products[pid]
        if budget is not None and p["price_inr"] > budget:
            continue
        if in_stock_only and p["stock_status"] == "out_of_stock":
            continue
        if need_laptop and p["attributes"].get("laptop_compartment") is not True:
            continue
        if min_laptop_in is not None and float(p["attributes"].get("fits_laptop_upto_in", 0) or 0) < min_laptop_in:
            continue
        kept.append(pid)
    if not kept:
        return Match([], list(tokens), True)
    scores = {pid: sum(cat.idf[t] for t in tokens if t in cat.doc_tokens[pid]) for pid in kept}
    best = max(scores.values())
    ids = sorted((pid for pid, s in scores.items() if s >= best - 1e-9), key=lambda i: (cat.products[i]["price_inr"], i))
    missing = [t for t in tokens if not any(t in cat.doc_tokens[pid] for pid in ids)]
    return Match(ids, missing, any(t not in SOFT_TOKENS for t in missing))
