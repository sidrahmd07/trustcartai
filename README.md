# teamID · R3: TrustCart AI, the shopping assistant that doesn't lie
(Replace `teamID` with your team ID.) A Retail assistant for the fictional Saffron Retail Group. It answers Hinglish shopping and policy questions using only the supplied catalogue and policy, asks which product when a question is ambiguous, and refuses when the store does not sell the item or the data does not say.

## What it does
Shoppers type messy questions such as `Chargit QuillBolt red earphones kitne ke` or `12000 ka order hai COD ho jayega?`. For every question the assistant chooses exactly one action:
- **answer**: the catalogue or policy contains it. Every price and fact is copied from the catalogue by code and cites a product ID or policy section.
- **clarify**: several products match and they differ on what was asked (price, stock, an attribute). It lists the candidates instead of guessing.
- **refuse**: the item is not sold, or the catalogue or policy is silent. A missing attribute is never treated as "false".

Results on the 40 practice questions: score **1.0000** (organiser baseline: 0.7315), 0 hallucinated prices, mean latency about 4 ms, 0 LLM tokens. The practice questions were used while building the rules, so expect the hidden score to be lower.

## How to run
Python 3.11 or newer.
```
cd FULL_CODE
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Put the pack's files in `FULL_CODE/data/` (git-ignored): `catalogue.csv`, `policy.md`, `questions_dev.csv`, `questions_dev_truth.jsonl`, `questions_test.csv`.
No secrets or environment variables are needed (see `FULL_CODE/.env.example`).
```
python make_submission.py --split dev      # writes ../submission/R3_dev_predictions.jsonl
python evaluate.py --submission ../submission/R3_dev_predictions.jsonl --truth data/questions_dev_truth.jsonl --out dev_score.json
python make_submission.py --split test     # writes ../submission/R3_predictions.jsonl
python server.py                           # chat demo at http://127.0.0.1:8000
```

## How to run the tests
```
cd FULL_CODE
python -m unittest discover -s tests -t .
```

## Architecture
```
question -> query.py (typo-tolerant Hinglish parser) -> policy.py (policy router)
         -> retrieval.py (hard filters + best-coverage match, all variants kept)
         -> decision.py (answer / clarify / refuse, plain code)
         -> grounding.py (builds reply from catalogue values, then self_check)
```
- `trustcart/`: core logic, independent of the web layer. `pipeline.py` is the single entry point (`Assistant.respond`).
- `lexicon.py`: Hinglish words and the policy / attribute rules, kept as data.
- `server.py` + `ui/`: local chat demo (standard library only) showing the action badge, sources, latency and token count.
- `make_submission.py`: creates the files in `submission/`. `config.yaml`: all paths and settings.
- Safety: `self_check` re-verifies every cited ID, price, fact and rupee amount in the text against the catalogue before a reply is sent; any mismatch becomes a refusal. The server validates input length and type, binds to 127.0.0.1 and has no CORS, database or secrets.

## AI usage
- **In the product: none.** There is no LLM, so no model licence applies, no tokens are used and the output is deterministic. Decisions and numbers are made by code.
- **During development:** an AI assistant (Claude, by Anthropic) was used to help plan and write code and to review outputs. The team is responsible for the submitted code.

## Pre-built and third-party code
- `FULL_CODE/evaluate.py` is the organisers' scorer, included unchanged for reproducibility. It is not our work.
- Libraries: pandas, numpy, PyYAML (permissive licences). The chat page layout comes from the team's own earlier prototype for this hackathon.
- No code from other hackathons or past projects.

## Limitations
- Rules, not learning: unusual phrasings, new slang or spelling far from the catalogue can be refused or misrouted. Parser vocabulary was extended after reading the unlabeled test questions (no test answers were seen).
- Ambiguity is decided by the asked field, so some borderline "clarify or answer" cases may differ from the organisers' labels.
- Single-language rules (Hinglish and English); no memory beyond a conversation's earlier turns.
- Next steps: widen the synonym lists, add a small model only to rephrase wording (the facts would stay code-generated), and add a regression suite built from more labelled questions.
