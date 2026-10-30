"""Load the catalogue (single source of truth) and build the search index over it."""
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd

from trustcart.textnorm import title_tokens, tokenize


class Catalogue:
    """Products keyed by id, plus token index used by retrieval."""

    def __init__(self, path: Path) -> None:
        df = pd.read_csv(path, dtype={"product_id": str})
        self.products: dict[str, dict] = {}
        for rec in df.to_dict("records"):
            rec["attributes"] = json.loads(rec["attributes"]) if isinstance(rec["attributes"], str) else {}
            if rec.get("review_count", 0) == 0 or pd.isna(rec.get("rating")):
                rec["rating"] = None
            self.products[rec["product_id"]] = rec
        self.ids: list[str] = list(self.products)
        self.brands = {p["brand"].lower() for p in self.products.values()}
        self.sub_categories = {p["sub_category"].lower() for p in self.products.values()}
        self.doc_tokens: dict[str, set[str]] = {}
        self.title_tokens: dict[str, set[str]] = {}
        for pid, p in self.products.items():
            title = title_tokens(f"{p['title']} {p['sub_category']}")
            vals: list[str] = []
            for v in p["attributes"].values():
                vals.extend(str(x) for x in v) if isinstance(v, list) else vals.append(str(v))
            self.title_tokens[pid] = title
            self.doc_tokens[pid] = title | set(tokenize(" ".join(vals)))
        df_count = Counter(t for toks in self.doc_tokens.values() for t in toks)
        n = len(self.ids)
        self.idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df_count.items()}
        self.vocab = set(df_count)
        self.brand_tokens = {t for b in self.brands for t in tokenize(b)}
        self.sub_category_tokens = {t for s in self.sub_categories for t in tokenize(s)}
        self.colours = {str(p["attributes"]["colour"]).lower() for p in self.products.values() if "colour" in p["attributes"]}
        self.inverted: dict[str, list[str]] = {}
        for pid, toks in self.doc_tokens.items():
            for t in toks:
                self.inverted.setdefault(t, []).append(pid)

    def get(self, pid: str) -> dict:
        return self.products[pid]
