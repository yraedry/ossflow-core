"""Validación estructural del docker-compose.yml raíz (Fase 2)."""
from pathlib import Path

import pytest
import yaml

COMPOSE_PATH = Path("C:/proyectos/docker-compose.yml")
BACKENDS = ("chapter-splitter", "subtitle-generator", "dubbing-generator")
BACKEND_PORTS = {
    "chapter-splitter": 8001,
    "subtitle-generator": 8002,
    "dubbing-generator": 8003,
}


@pytest.fixture(scope="module")
def compose():
    assert COMPOSE_PATH.exists(), f"No existe {COMPOSE_PATH}"
    with COMPOSE_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_required_services_present(compose):
    services = compose.get("services", {})
    for svc in (*BACKENDS, "processor-api", "processor-frontend"):
        assert svc in services, f"Falta servicio {svc}"


@pytest.mark.parametrize("backend", BACKENDS)
def test_backend_has_gpu_reservation(compose, backend):
    svc = compose["services"][backend]
    devices = svc["deploy"]["resources"]["reservations"]["devices"]
    assert any(
        d.get("driver") == "nvidia" and "gpu" in d.get("capabilities", [])
        for d in devices
    ), f"{backend} sin reserva GPU nvidia"


@pytest.mark.parametrize("backend,port", BACKEND_PORTS.items())
def test_backend_exposes_port(compose, backend, port):
    ports = compose["services"][backend].get("ports", [])
    assert any(str(port) in str(p) for p in ports), f"{backend} no expone {port}"


@pytest.mark.parametrize("backend", BACKENDS)
def test_backend_healthcheck(compose, backend):
    assert "healthcheck" in compose["services"][backend], f"{backend} sin healthcheck"


def test_processor_api_depends_on_backends(compose):
    deps = compose["services"]["processor-api"].get("depends_on", {})
    # admite dict (con condition) o list
    if isinstance(deps, list):
        for b in BACKENDS:
            assert b in deps
    else:
        for b in BACKENDS:
            assert b in deps, f"processor-api no depende de {b}"
            assert deps[b].get("condition") == "service_healthy"


def test_processor_api_env_urls(compose):
    env = compose["services"]["processor-api"].get("environment", [])
    # normaliza a dict
    if isinstance(env, list):
        env_d = dict(e.split("=", 1) for e in env if "=" in e)
    else:
        env_d = dict(env)
    assert env_d.get("SPLITTER_URL") == "http://chapter-splitter:8001"
    assert env_d.get("SUBS_URL") == "http://subtitle-generator:8002"
    assert env_d.get("DUBBING_URL") == "http://dubbing-generator:8003"


@pytest.mark.parametrize("backend", BACKENDS)
def test_backend_build_context(compose, backend):
    build = compose["services"][backend]["build"]
    assert build["context"].rstrip("/").endswith("python")
    assert backend in build["dockerfile"]


@pytest.mark.parametrize("backend", BACKENDS)
def test_backend_library_volume(compose, backend):
    vols = compose["services"][backend].get("volumes", [])
    assert any("/library" in str(v) for v in vols), f"{backend} sin montaje /library"


def test_common_network(compose):
    assert "bjj_net" in compose.get("networks", {})
    for b in BACKENDS:
        assert "bjj_net" in compose["services"][b].get("networks", [])
