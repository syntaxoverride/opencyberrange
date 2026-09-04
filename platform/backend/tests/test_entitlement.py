"""Entitlement fallback tests. Pure unit level, no database and no client:
app.entitlement reads a JSON file and caches the result per process."""
import json

import pytest

import app.entitlement as entitlement


@pytest.fixture()
def fresh_entitlement():
    """Clear the per-process cache before and after each test so one test's
    load can never leak into another."""
    entitlement._entitlement = None
    yield entitlement
    entitlement._entitlement = None


def test_missing_file_falls_back_to_lite(fresh_entitlement, monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ENTITLEMENT_FILE", str(tmp_path / "does_not_exist.json"))
    ent = fresh_entitlement.get_entitlement()
    assert ent == entitlement.LITE_DEFAULTS
    assert ent["edition"] == "lite"
    assert ent["max_privileged_accounts"] == 1
    assert ent["max_active_courses"] == 5


def test_unreadable_file_falls_back_to_lite(fresh_entitlement, monkeypatch, tmp_path):
    bad = tmp_path / "entitlement.json"
    bad.write_text("{ this is not valid json")
    monkeypatch.setenv("OCR_ENTITLEMENT_FILE", str(bad))
    ent = fresh_entitlement.get_entitlement()
    assert ent["edition"] == "lite"
    assert ent["max_privileged_accounts"] == 1


def test_enterprise_file_lifts_caps(fresh_entitlement, monkeypatch, tmp_path):
    good = tmp_path / "entitlement.json"
    good.write_text(json.dumps({
        "edition": "enterprise",
        "max_privileged_accounts": None,
        "max_active_courses": None,
    }))
    monkeypatch.setenv("OCR_ENTITLEMENT_FILE", str(good))
    ent = fresh_entitlement.get_entitlement()
    assert ent["edition"] == "enterprise"
    assert ent["max_privileged_accounts"] is None
    assert ent["max_active_courses"] is None


def test_unknown_keys_ignored(fresh_entitlement, monkeypatch, tmp_path):
    f = tmp_path / "entitlement.json"
    f.write_text(json.dumps({
        "edition": "enterprise",
        "definitely_not_a_real_key": True,
    }))
    monkeypatch.setenv("OCR_ENTITLEMENT_FILE", str(f))
    ent = fresh_entitlement.get_entitlement()
    assert "definitely_not_a_real_key" not in ent
    # Keys the file omits keep their Lite defaults.
    assert ent["max_privileged_accounts"] == 1


def test_result_is_cached_per_process(fresh_entitlement, monkeypatch, tmp_path):
    f = tmp_path / "entitlement.json"
    f.write_text(json.dumps({"edition": "enterprise"}))
    monkeypatch.setenv("OCR_ENTITLEMENT_FILE", str(f))
    first = fresh_entitlement.get_entitlement()
    # Changing the file after the first read must not change the answer.
    f.write_text(json.dumps({"edition": "lite"}))
    second = fresh_entitlement.get_entitlement()
    assert first is second
    assert second["edition"] == "enterprise"
