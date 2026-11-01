# NyayNet

An AI agent that detects abusive and threatening Instagram comments in several languages, compiles the evidence, and files structured complaints on India's National Cyber Crime Reporting Portal. A person stays in control of what gets filed.

## Pipeline

```
Instagram comments -> preprocessing -> hybrid detection -> severity scoring
  -> decision engine -> human review -> evidence compiler -> portal filing -> tracking
```

- **Ingestion** polls comments through the Instagram API, with a mock client for local runs.
- **Text preprocessing** handles language detection, transliterated Indic text and emoji.
- **Hybrid detection** screens each comment with a local Hugging Face hate speech model. Clear results stop there, and uncertain ones escalate to an LLM classifier, which keeps API cost down.
- **Scoring** combines severity with behavior across a commenter's history.
- **Decision engine** acts only above a confidence threshold, and a human review queue can override any decision.
- **Evidence** compiles screenshots (Playwright) and a PDF report (ReportLab).
- **Filing** fills the portal form with Playwright. CAPTCHA and OTP steps always go to the user.
- **Tracking** follows complaint status and sends notifications.
- **Storage and audit** keep encrypted records and an audit log of every decision, with rate limiting on outbound calls.

## Setup

Requires Python 3.10 or newer.

```
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Fill in `ANTHROPIC_API_KEY`, `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_BUSINESS_ACCOUNT_ID` in `.env`.

## Usage

```
python main.py init                 # set up the database
python main.py seed                 # load sample data
python main.py monitor --once       # poll comments and classify them
python main.py review               # work through the human review queue
python main.py file-complaint <decision_id>   # file an approved decision
python main.py status [complaint_id]          # check complaint status
```

Run `python main.py <command> --help` for each command's options.

## Tests

```
pytest tests
```

Unit and integration tests cover detection, scoring, decisions, evidence, filing, ingestion and storage.
