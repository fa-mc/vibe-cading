"""Regression tests for the private ``.env`` loader (``vibe_cading._env``).

Focus: the matched-surrounding-quote stripping in :func:`load_env_file`.
The project's own ``.env`` / ``.env.example`` write quoted values
(``VIBE_PRINT_PROFILE="bambu_p1s__pla_overture"``, ``PIN_HOLE_PRINTED="4.85"``);
the parser must strip the quote characters so they never leak into the env var
(which would break profile-name lookups and ``float()`` casts).
"""

from __future__ import annotations

import os

from vibe_cading._env import load_env_file


def _write_env(tmp_path, body: str):
    """Write ``body`` to a temp ``.env`` file and return its path."""
    env_path = tmp_path / ".env"
    env_path.write_text(body)
    return env_path


def test_double_quoted_value_stripped(tmp_path, monkeypatch):
    """``KEY="val"`` → ``val`` (quote chars removed)."""
    monkeypatch.delenv("VIBE_TEST_DQ", raising=False)
    load_env_file(_write_env(tmp_path, 'VIBE_TEST_DQ="bambu_p1s"\n'))
    assert os.environ["VIBE_TEST_DQ"] == "bambu_p1s"


def test_single_quoted_value_stripped(tmp_path, monkeypatch):
    """``KEY='val'`` → ``val`` (single quotes are also a matched pair)."""
    monkeypatch.delenv("VIBE_TEST_SQ", raising=False)
    load_env_file(_write_env(tmp_path, "VIBE_TEST_SQ='bambu_p1s'\n"))
    assert os.environ["VIBE_TEST_SQ"] == "bambu_p1s"


def test_unquoted_value_unchanged(tmp_path, monkeypatch):
    """``KEY=val`` → ``val`` (no quotes, value passes through verbatim)."""
    monkeypatch.delenv("VIBE_TEST_PLAIN", raising=False)
    load_env_file(_write_env(tmp_path, "VIBE_TEST_PLAIN=bambu_p1s\n"))
    assert os.environ["VIBE_TEST_PLAIN"] == "bambu_p1s"


def test_empty_double_quotes_yield_empty_string(tmp_path, monkeypatch):
    """``KEY=""`` → empty string (matches GH_TOKEN="" in .env.example)."""
    monkeypatch.delenv("VIBE_TEST_EMPTY", raising=False)
    load_env_file(_write_env(tmp_path, 'VIBE_TEST_EMPTY=""\n'))
    assert os.environ["VIBE_TEST_EMPTY"] == ""


def test_mismatched_quotes_left_untouched(tmp_path, monkeypatch):
    """``KEY="val'`` — unbalanced quotes are NOT a matched pair; leave as-is."""
    monkeypatch.delenv("VIBE_TEST_MISMATCH", raising=False)
    load_env_file(_write_env(tmp_path, "VIBE_TEST_MISMATCH=\"val'\n"))
    assert os.environ["VIBE_TEST_MISMATCH"] == "\"val'"


def test_quoted_numeric_value_floatable(tmp_path, monkeypatch):
    """``KEY="4.85"`` → ``4.85`` parses cleanly with ``float()``.

    Guards the constants.py import path: a quoted numeric value previously
    raised ``ValueError`` on ``float('"4.85"')``.
    """
    monkeypatch.delenv("VIBE_TEST_NUMERIC", raising=False)
    load_env_file(_write_env(tmp_path, 'VIBE_TEST_NUMERIC="4.85"\n'))
    assert float(os.environ["VIBE_TEST_NUMERIC"]) == 4.85


def test_single_quote_char_only_left_untouched(tmp_path, monkeypatch):
    """A lone quote char (len < 2 after strip) is not a pair — leave as-is."""
    monkeypatch.delenv("VIBE_TEST_LONE", raising=False)
    load_env_file(_write_env(tmp_path, 'VIBE_TEST_LONE="\n'))
    assert os.environ["VIBE_TEST_LONE"] == '"'


def test_already_set_env_var_wins(tmp_path, monkeypatch):
    """``setdefault`` semantics preserved — a pre-set OS var is not overwritten."""
    monkeypatch.setenv("VIBE_TEST_PRESET", "shell_value")
    load_env_file(_write_env(tmp_path, 'VIBE_TEST_PRESET="file_value"\n'))
    assert os.environ["VIBE_TEST_PRESET"] == "shell_value"
