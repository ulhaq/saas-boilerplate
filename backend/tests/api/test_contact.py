from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "name": "Mette Hansen",
    "email": "mette@example.org",
    "subject": "Question about pricing",
    "message": "Could you tell me what the Advanced plan includes?",
}


def test_submit_contact_message(client: TestClient) -> None:
    response = client.post("/v1/contact", json=VALID_PAYLOAD)
    assert response.status_code == 202
    assert "message" in response.json()


def test_submit_contact_message_emails_the_team(client: TestClient, mocker) -> None:
    send_email = mocker.patch("src.platform.services.contact.send_email")

    response = client.post("/v1/contact", json=VALID_PAYLOAD)

    assert response.status_code == 202
    send_email.assert_called_once()
    kwargs = send_email.call_args.kwargs
    assert kwargs["email_template"] == "contact-message"
    # Team members reply straight to the person who wrote in.
    assert kwargs["reply_to"] == VALID_PAYLOAD["email"]
    assert kwargs["data"]["message_body"] == VALID_PAYLOAD["message"]


def test_submit_contact_message_rejects_invalid_email(client: TestClient) -> None:
    response = client.post("/v1/contact", json=VALID_PAYLOAD | {"email": "nope"})
    assert response.status_code == 422


def test_submit_contact_message_rejects_blank_name(client: TestClient) -> None:
    response = client.post("/v1/contact", json=VALID_PAYLOAD | {"name": "   "})
    assert response.status_code == 422


def test_submit_contact_message_rejects_too_short_message(client: TestClient) -> None:
    response = client.post("/v1/contact", json=VALID_PAYLOAD | {"message": "hi"})
    assert response.status_code == 422
