"""
Core document analysis logic, built on the Claude Messages API.

The functions here take the Anthropic client as an argument rather than creating it
inside. That keeps the logic pure and lets the tests pass a fake client, so the test suite
never touches the network or spends money. The Streamlit app wires in a real client.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

DEFAULT_MODEL = "claude-opus-5-5"
# The context window is large, but PDFs can be huge, so cap what we send and say so.
MAX_CHARS = 180_000


def _text_from(response) -> str:
    """Pull the plain text out of a Messages API response."""
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_CHARS:
        return text, False
    return text[:MAX_CHARS], True


def summarize(client, document: str, model: str = DEFAULT_MODEL) -> str:
    """A tight technical summary of the document."""
    body, truncated = _truncate(document)
    system = (
        "You are a careful engineering analyst. Summarize technical documents for an "
        "engineer who is short on time. Lead with what the document is and what it is for, "
        "then the key specifications, then anything that affects safety, maintenance or "
        "compatibility. Be specific with numbers and units. Do not invent details that are "
        "not in the text."
    )
    note = "\n\n(Note: the document was long and has been truncated.)" if truncated else ""
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"Summarize this document.{note}\n\n{body}"}],
    )
    return _text_from(response)


def answer_question(client, document: str, question: str, model: str = DEFAULT_MODEL) -> str:
    """Answer a question grounded in the document."""
    body, truncated = _truncate(document)
    system = (
        "You answer questions strictly from the provided document. If the answer is not in "
        "the document, say so plainly rather than guessing. Quote the relevant figure or "
        "clause when it helps. Keep answers short and concrete."
    )
    note = "\n\n(Note: the document was long and has been truncated.)" if truncated else ""
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Document:{note}\n\n{body}\n\nQuestion: {question}",
        }],
    )
    return _text_from(response)


@dataclass
class Spec:
    name: str
    value: str
    unit: str


def _parse_specs(raw: str) -> list[Spec]:
    """Pull a JSON array out of the model text and turn it into Spec rows, defensively."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    specs = []
    for item in data:
        if isinstance(item, dict) and item.get("name"):
            specs.append(Spec(
                name=str(item.get("name", "")).strip(),
                value=str(item.get("value", "")).strip(),
                unit=str(item.get("unit", "")).strip(),
            ))
    return specs


def extract_specs(client, document: str, model: str = DEFAULT_MODEL) -> list[Spec]:
    """Extract structured specifications (name, value, unit) from the document."""
    body, _ = _truncate(document)
    system = (
        "You extract technical specifications from engineering documents. Return ONLY a JSON "
        "array of objects, each with the keys name, value and unit. Split the numeric value "
        "from its unit (for example value '400', unit 'kW'). If there is no unit, use an "
        "empty string. Do not include anything that is not a real specification in the text, "
        "and do not wrap the JSON in prose or code fences."
    )
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"Extract the specifications.\n\n{body}"}],
    )
    return _parse_specs(_text_from(response))
