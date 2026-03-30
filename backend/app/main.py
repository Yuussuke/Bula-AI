from fastapi import FastAPI
from app.modules.bulas.router import router as bulas_router

def create_app() -> FastAPI:
    app = FastAPI(title="BulaGPT API", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(bulas_router)
    return app

app = create_app()