from fastapi import FastAPI
from app.modules.bulas.router import router as bulas_router
from app.core.db.base import Base
from app.core.db.session import engine

def create_app() -> FastAPI:
    app = FastAPI(title="BulaGPT API", version="0.1.0")
    
    Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(bulas_router, prefix="/api/v1")
    return app

app = create_app()