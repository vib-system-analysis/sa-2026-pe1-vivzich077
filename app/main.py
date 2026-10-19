from fastapi import FastAPI

app = FastAPI(
    title="Тесты по требованиям и багрепортам",
    description="Сервис-заглушка для инфраструктурного старта проекта.",
    version="0.1.0",
)


@app.get("/", tags=["service"])
def read_root() -> dict[str, str]:
    return {"name": "ai-test-writer", "status": "stub"}


@app.get("/health", tags=["service"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
