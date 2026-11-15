"""
Tests for the analyzer. These use a fake Anthropic client, so they never call the real API
and never cost anything. The point is to prove the prompt wiring, text extraction and the
defensive JSON parsing all behave.
"""
from dataclasses import dataclass

from src import analyzer


@dataclass
class FakeBlock:
    type: str
    text: str


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeBlock("text", text)]


class FakeMessages:
    def __init__(self, reply):
        self.reply = reply
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self.reply)


class FakeClient:
    def __init__(self, reply):
        self.messages = FakeMessages(reply)


def test_summarize_returns_text_and_sends_document():
    client = FakeClient("A 400 kW diesel generator set.")
    out = analyzer.summarize(client, "Prime power 400 kW diesel genset.")
    assert "400 kW" in out
    # the document text must reach the API call
    sent = client.messages.last_kwargs["messages"][0]["content"]
    assert "diesel genset" in sent


def test_answer_question_includes_question():
    client = FakeClient("The rated output is 400 kW.")
    out = analyzer.answer_question(client, "Rated output: 400 kW.", "What is the rated output?")
    assert "400 kW" in out
    sent = client.messages.last_kwargs["messages"][0]["content"]
    assert "What is the rated output?" in sent


def test_extract_specs_parses_json_array():
    reply = '[{"name": "Rated power", "value": "400", "unit": "kW"}, ' \
            '{"name": "Voltage", "value": "415", "unit": "V"}]'
    client = FakeClient(reply)
    specs = analyzer.extract_specs(client, "some datasheet")
    assert len(specs) == 2
    assert specs[0].name == "Rated power"
    assert specs[0].value == "400"
    assert specs[0].unit == "kW"


def test_extract_specs_handles_prose_wrapped_json():
    reply = 'Here are the specs:\n[{"name": "Mass", "value": "1200", "unit": "kg"}]\nThanks.'
    client = FakeClient(reply)
    specs = analyzer.extract_specs(client, "doc")
    assert len(specs) == 1
    assert specs[0].name == "Mass"


def test_extract_specs_handles_garbage_gracefully():
    client = FakeClient("I could not find any specifications.")
    specs = analyzer.extract_specs(client, "doc")
    assert specs == []


def test_truncation_flag():
    short, was_cut = analyzer._truncate("x" * 100)
    assert was_cut is False
    long, was_cut = analyzer._truncate("x" * (analyzer.MAX_CHARS + 10))
    assert was_cut is True
    assert len(long) == analyzer.MAX_CHARS
