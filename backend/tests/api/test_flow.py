"""The main loop over HTTP: sign in, pair up, teach, review, practise, correct."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.conftest import auth, sign_in


def _pair(client: TestClient) -> tuple[dict[str, str], dict[str, str], str]:
    amina, malam = auth(sign_in(client, "amina")), auth(sign_in(client, "malam"))
    invite = client.post("/v1/invitations", json={"teaches": "ar", "learns": "bs"}, headers=malam)
    assert invite.status_code == 201
    assert invite.json()["expires_in_days"] == 7
    accepted = client.post(
        "/v1/invitations/accept", json={"code": invite.json()["code"]}, headers=amina
    )
    assert accepted.status_code == 201, accepted.text
    return malam, amina, accepted.json()["id"]


def test_partners_teach_and_learn_each_other(client: TestClient) -> None:
    malam, amina, pair_id = _pair(client)
    assert [p["id"] for p in client.get("/v1/pairs", headers=malam).json()] == [pair_id]

    taught = client.post(
        f"/v1/pairs/{pair_id}/contributions",
        json={"text": "صباح الخير", "gloss": "Good morning", "gloss_language": "en"},
        headers=malam,
    )
    assert taught.status_code == 201, taught.text
    assert taught.json()["language"] == "ar"

    # Amina (learning Arabic) now has it as a new review card.
    session = client.get("/v1/reviews/session", headers=amina).json()
    assert [card["item_id"] for card in session] == [taught.json()["id"]]
    assert client.get("/v1/reviews/session", headers=malam).json() == []

    reviewed = client.post(
        f"/v1/reviews/{session[0]['id']}", json={"rating": 3, "duration_ms": 1800}, headers=amina
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["is_new"] is False

    # Amina practises Arabic; Malam corrects; the correction becomes her card.
    attempt = client.post(
        f"/v1/pairs/{pair_id}/attempts", json={"text": "صباح النور"}, headers=amina
    ).json()
    waiting = client.get("/v1/attempts/to-review", headers=malam).json()
    assert [a["id"] for a in waiting] == [attempt["id"]]
    corrected = client.post(
        f"/v1/attempts/{attempt['id']}/correction",
        json={"corrected_text": "صباح النور", "comment": "Perfect reply!"},
        headers=malam,
    )
    assert corrected.status_code == 200
    assert corrected.json()["correction"]["comment"] == "Perfect reply!"
    twice = client.post(
        f"/v1/attempts/{attempt['id']}/correction",
        json={"corrected_text": "x"},
        headers=malam,
    )
    assert twice.status_code == 409

    contributions = client.get(f"/v1/pairs/{pair_id}/contributions", headers=amina).json()
    assert len(contributions) == 1
    later = client.get(
        f"/v1/pairs/{pair_id}/contributions",
        params={"since": "2026-12-01T00:00:00"},
        headers=amina,
    )
    assert later.json() == []

    assert client.get(f"/v1/pairs/{pair_id}/streak", headers=amina).json() == {"days": 0}
