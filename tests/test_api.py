"""Tests for the FastAPI REST API."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from airscribe.transcriber import TranscriptionResult, Segment


@pytest.fixture
def client():
    from airscribe.api import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestModelsEndpoint:
    def test_list_models(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        assert "large-v3" in r.json()["available"]


class TestDomainsEndpoint:
    def test_list_domains(self, client):
        r = client.get("/domains")
        assert r.status_code == 200
        assert "medical" in r.json()
