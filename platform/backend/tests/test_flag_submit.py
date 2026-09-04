"""Flag submission smoke tests against /api/exercises/labs/{id}/submit-flag.

Each test gets its own user and lab from fixtures, so ordering never
matters and a correct submission in one test cannot mark a lab completed
for another.
"""
import pytest

pytestmark = pytest.mark.db


def _submit(client, headers, lab_id, flag):
    return client.post(
        f"/api/exercises/labs/{lab_id}/submit-flag",
        json={"flag": flag},
        headers=headers,
    )


def test_wrong_flag_rejected(client, auth_headers, test_lab):
    resp = _submit(client, auth_headers, test_lab.id, "OCR{completely_wrong}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["correct"] is False
    assert body["attempts"] == 1
    assert "Incorrect" in body["message"]


def test_correct_flag_accepted(client, auth_headers, test_lab, test_flag):
    resp = _submit(client, auth_headers, test_lab.id, test_flag)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["correct"] is True


def test_flag_comparison_is_case_sensitive(client, auth_headers, test_lab, test_flag):
    # The backend strips surrounding whitespace but preserves case, so a
    # case-mangled copy of the real flag must be rejected.
    mangled = test_flag.swapcase()
    assert mangled != test_flag
    resp = _submit(client, auth_headers, test_lab.id, mangled)
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is False

    # The exact flag still works afterwards for the same user and lab.
    resp = _submit(client, auth_headers, test_lab.id, test_flag)
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True


def test_empty_flag_is_a_400(client, auth_headers, test_lab):
    resp = _submit(client, auth_headers, test_lab.id, "   ")
    assert resp.status_code == 400


def test_submit_requires_auth(client, db_schema, test_lab):
    resp = client.post(
        f"/api/exercises/labs/{test_lab.id}/submit-flag",
        json={"flag": "OCR{anything}"},
    )
    assert resp.status_code == 401
