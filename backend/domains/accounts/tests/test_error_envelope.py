"""The envelope is the API's only failure shape, so it gets tested directly.

A DRF exception whose ``detail`` is a dict — a malformed ``Authorization`` header produces
one — must still come back as a sentence, not a Python repr.
"""

import pytest

pytestmark = pytest.mark.django_db

ME = "/api/v1/auth/me"


class TestEnvelopeShape:
    def test_every_failure_has_the_same_three_keys(self, api):
        response = api.get(ME)

        assert set(response.data) == {"error"}
        assert set(response.data["error"]) == {"code", "message", "details"}

    def test_a_malformed_authorization_header_reads_as_a_sentence(self, api):
        api.credentials(HTTP_AUTHORIZATION="Bearer")

        response = api.get(ME)

        assert response.status_code == 401
        assert response.data["error"]["code"] == "NOT_AUTHENTICATED"
        message = response.data["error"]["message"]
        assert "ErrorDetail" not in message
        assert "{" not in message
        assert message.endswith("values")

    def test_a_garbage_token_reads_as_a_sentence(self, api):
        api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        response = api.get(ME)

        assert response.status_code == 401
        assert "ErrorDetail" not in response.data["error"]["message"]

    def test_an_unsupported_method_uses_its_own_code(self, librarian_api):
        response = librarian_api.delete(ME)

        assert response.status_code == 405
        assert response.data["error"]["code"] == "METHOD_NOT_ALLOWED"
        assert "ErrorDetail" not in response.data["error"]["message"]

    def test_an_unknown_api_path_stays_in_the_envelope(self, api):
        response = api.get("/api/v1/nonsense")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    def test_throttling_answers_in_the_envelope(self, api, monkeypatch):
        # DRF snapshots THROTTLE_RATES onto the class at import, so overriding the setting
        # here would do nothing — patch the class the auth endpoints actually use.
        from django.core.cache import cache

        from domains.accounts.throttles import AuthEndpointThrottle

        monkeypatch.setattr(AuthEndpointThrottle, "THROTTLE_RATES", {"auth": "1/min"})
        cache.clear()

        payload = {"email": "nobody@x.test", "password": "whatever"}
        api.post("/api/v1/auth/login", payload, format="json")
        response = api.post("/api/v1/auth/login", payload, format="json")

        assert response.status_code == 429
        assert response.data["error"]["code"] == "THROTTLED"
        assert "ErrorDetail" not in response.data["error"]["message"]
        cache.clear()
