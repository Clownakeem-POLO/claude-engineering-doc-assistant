"""Tests for document reading. The text path needs no external files."""
from src.pdf_utils import read_document


def test_read_plain_text():
    out = read_document("notes.txt", b"Rated power 400 kW")
    assert out == "Rated power 400 kW"


def test_read_markdown():
    out = read_document("spec.md", b"# Datasheet\n\nVoltage 415 V")
    assert "Voltage 415 V" in out


def test_unknown_extension_decoded_as_text():
    out = read_document("data.log", b"temperature 90 C")
    assert "temperature 90 C" in out
