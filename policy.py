"""Store policy: load policy.md, route a question to a sub-section, and quote the section text."""
import re
from pathlib import Path

from trustcart.lexicon import POLICY_GAP_RULES, POLICY_RULES
from trustcart.textnorm import normalise

_HEAD = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)\.?\s+(.*)$", re.M)
_RUPEE = re.compile(r"₹\s?[\d,]+")


class Policy:
    def __init__(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        marks = list(_HEAD.finditer(text))
        self.titles: dict[str, str] = {}
        self.bodies: dict[str, str] = {}
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            self.titles[m.group(1)] = m.group(2).strip()
            self.bodies[m.group(1)] = text[m.end():end].replace("**", "").replace("`", "").strip()
        self.amounts = {a.replace(" ", "") for body in self.bodies.values() for a in _RUPEE.findall(body)}

    def sections(self) -> list[str]:
        return list(self.bodies)

    def quote(self, section: str) -> str:
        return f"Per our store policy, section {section} ({self.titles[section]}): {self.bodies[section]}"


def route_policy(text: str) -> tuple[str, str | None]:
    """Return ('policy', section), ('gap', None) when the policy is silent, or ('none', None)."""
    low = normalise(text)
    for rx in POLICY_GAP_RULES:
        if re.search(rx, low):
            return "gap", None
    for rx, section in POLICY_RULES:
        if re.search(rx, low):
            return "policy", section
    return "none", None
