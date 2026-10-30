"""Create the prediction files with the TrustCart pipeline. Run from FULL_CODE/.

    python make_submission.py --split dev    # -> ../submission/R3_dev_predictions.jsonl
    python make_submission.py --split test   # -> ../submission/R3_predictions.jsonl
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from trustcart.config import load_config, path_of
from trustcart.pipeline import Assistant

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    args = parser.parse_args()
    cfg = load_config()
    questions = pd.read_csv(path_of(cfg, f"questions_{args.split}"), dtype=str)
    questions = questions.assign(turn=questions["turn"].astype(int)).sort_values(["conversation_id", "turn"])
    name = "R3_dev_predictions.jsonl" if args.split == "dev" else "R3_predictions.jsonl"
    out = (HERE.parent / "submission" / name)
    out.parent.mkdir(parents=True, exist_ok=True)
    assistant = Assistant()
    with open(out, "w", encoding="utf-8") as handle:
        for row in questions.itertuples(index=False):
            result = assistant.respond(row.question_text, row.conversation_id)
            handle.write(json.dumps({"question_id": row.question_id, **result}, ensure_ascii=False) + "\n")
    print(f"wrote {len(questions)} predictions to {out}")


if __name__ == "__main__":
    main()
