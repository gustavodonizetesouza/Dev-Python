from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, compras

app = FastAPI(title="Gestão Familiar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # ajuste em produção para os domínios reais do seu app
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(compras.router)


@app.get("/health")
def health():
    return {"status": "ok"}
