# Engineering document assistant

A small app that reads an engineering document, a datasheet, a maintenance manual, a
technical report, and does three things with it: summarizes it, answers questions about it,
and pulls its specifications into a table you can download. It runs on the Claude API.

I built this because a lot of my mechanical work starts with wading through a PDF to find
one number. The rated power, the torque, the service interval. This puts Claude between me
and the document so I can just ask.

## What it does

- **Summary.** A technical summary aimed at an engineer who is short on time: what the
  document is, the key specs, and anything that affects safety, maintenance or compatibility.
- **Ask a question.** Answers grounded in the document. If the answer is not in the text, it
  says so instead of guessing.
- **Extract specs.** Pulls out specifications as structured rows (name, value, unit) and lets
  you download them as CSV.

## How it is built

The Claude calls live in `src/analyzer.py`, and they take the Anthropic client as an
argument instead of creating it inside. That one decision is what makes the project testable:
the test suite passes in a fake client, so `pytest` runs with no API key, no network, and no
cost, while the Streamlit app wires in a real client. Document reading (PDF via `pypdf`, or
plain text) is in `src/pdf_utils.py`.

```
app.py              Streamlit UI
src/analyzer.py     the Claude calls: summarize, answer_question, extract_specs
src/pdf_utils.py    read text out of an uploaded PDF or text file
tests/              unit tests with a fake client, no network
```

## Running it locally

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # on Windows: set ANTHROPIC_API_KEY=...
streamlit run app.py
```

The model defaults to `claude-opus-5-5`. You can point it at a cheaper model by setting
`ANTHROPIC_MODEL` (for example `claude-sonnet-5-5` or `claude-haiku-5-5`), which is worth
doing for short, simple documents.

## Running the tests

```
pip install -r requirements.txt
pytest
```

The tests do not need an API key. They mock the client, so they prove the prompt wiring and
the defensive JSON parsing without spending anything.

## Deploying it live

It deploys to Streamlit Community Cloud straight from the repo. Point it at `app.py`, then add
your `ANTHROPIC_API_KEY` under the app's Secrets (Streamlit reads secrets into the environment,
which is exactly where the app looks for it). It also runs as a Hugging Face Space with the
Streamlit SDK, with the key set as a Space secret.

## Honest limitations

- It reads the text layer of a PDF. A scanned document with no text layer will come back empty,
  it would need OCR first, which I have left out on purpose to keep this focused.
- Very long documents are truncated before being sent, and the app tells you when that happens.
  A production version would chunk the document and work section by section.
- The spec extractor is only as good as the document's own wording. It is deliberately
  conservative and returns nothing rather than inventing specs, so it can miss loosely worded
  ones.
- Your document is sent to the Anthropic API for analysis. Do not upload anything you are not
  allowed to share with a third party service.

## License

MIT, see `LICENSE`.
