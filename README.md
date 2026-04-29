# ossflow-core

Infraestructura compartida del ecosistema OSSFlow.

## Contenido

- **`ossflow-base/`**: imagen Docker base con CUDA 12.4 + PyTorch + FastAPI. Se construye una sola vez (`docker build -t ossflow-base:latest -f ossflow-base/Dockerfile .`) y la consumen los servicios GPU de `ossflow-platform`.
- **`ossflow_service_kit/`**: paquete Python compartido (`ossflow-service-kit` en PyPI). Provee `app_factory`, ring buffer de logs, eventos SSE, runner de jobs y la capa de base de datos común (SQLAlchemy 2.0 + Alembic).

## Distribución

`ossflow_service_kit` se publica vía Git tags. Los servicios consumidores instalan con:

```toml
dependencies = [
    "ossflow-service-kit @ git+https://github.com/yraedry/ossflow-core@v0.1.0#subdirectory=ossflow_service_kit",
]
```
