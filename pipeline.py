"""Question -> grounded prediction. Shared by the chat UI, the API and make_submission.py."""
import time
from dataclasses import dataclass, field
from pathlib import Path

from trustcart.catalogue import Catalogue
from trustcart.config import load_config, path_of
from trustcart.decision import Decider
from trustcart.grounding import self_check
from trustcart.lexicon import LIST_WORDS
from trustcart.policy import Policy
from trustcart.query import QueryFrame, QueryParser
from trustcart.textnorm import normalise, tokenize


@dataclass
class ConversationState:
    tokens: list[str] = field(default_factory=list)
    budget: int | None = None
    asked: str = "list"


class Assistant:
    def __init__(self, catalogue_path: Path | None = None, policy_path: Path | None = None) -> None:
        cfg = load_config()
        self.catalogue = Catalogue(catalogue_path or path_of(cfg, "catalogue"))
        self.policy = Policy(policy_path or path_of(cfg, "policy"))
        ordinary = {t for body in (*self.policy.bodies.values(), *self.policy.titles.values()) for t in tokenize(body)}
        self.parser = QueryParser(self.catalogue, ordinary)
        self.decider = Decider(self.catalogue, self.policy)
        self.conversations: dict[str, ConversationState] = {}

    def _with_context(self, frame: QueryFrame, state: ConversationState | None) -> QueryFrame:
        """Follow-up turns ('lavender wali', '1500 ke andar wale?') inherit the earlier turns' constraints."""
        if state is None or not state.tokens or frame.has_subject or frame.unknown or frame.out_of_catalogue:
            return frame
        frame.tokens = sorted(set(state.tokens) | set(frame.tokens))
        frame.budget = frame.budget if frame.budget is not None else state.budget
        low = normalise(frame.text)
        if frame.asked == "list" and frame.budget is None or (frame.asked == "list" and not LIST_WORDS.search(low) and frame.budget == state.budget):
            frame.asked = state.asked
        return frame

    def respond(self, text: str, conversation_id: str = "default") -> dict:
        start = time.perf_counter()
        state = self.conversations.get(conversation_id)
        frame = self._with_context(self.parser.parse(text), state)
        result = self.decider.decide(frame)
        result = self_check(result, self.catalogue, self.policy, text)
        if result["action"] != "refuse" or frame.tokens:
            self.conversations[conversation_id] = ConversationState(frame.tokens, frame.budget, frame.asked)
        result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        result["tokens_in"] = 0
        result["tokens_out"] = 0
        return result
