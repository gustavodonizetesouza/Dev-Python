import httpx

API_URL = "http://127.0.0.1:8000"  # endereço do backend FastAPI


class ApiError(Exception):
    """Erro amigável retornado pela API."""

    def __init__(self, mensagem: str, status: int = 400) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class ApiClient:
    def __init__(self) -> None:
        self.token: str | None = None
        self._client = httpx.Client(base_url=API_URL, timeout=15.0)

    # ---------- autenticação ----------
    def registrar(self, nome: str, email: str, senha: str) -> dict:
        resp = self._client.post(
            "/auth/registro",
            json={"nome": nome, "email": email, "senha": senha},
        )
        if resp.status_code >= 400:
            raise ApiError(self._erro(resp), resp.status_code)
        return resp.json()

    def login(self, email: str, senha: str) -> dict:
        resp = self._client.post(
            "/auth/login",
            json={"email": email, "senha": senha},
        )
        if resp.status_code >= 400:
            raise ApiError(self._erro(resp), resp.status_code)
        self.token = resp.json()["access_token"]
        return resp.json()

    # ---------- listas de compras ----------
    def listar_listas(self) -> list[dict]:
        return self._get("/compras/listas")

    def criar_lista(self, nome: str) -> dict:
        return self._post("/compras/listas", {"nome": nome})

    def adicionar_item(self, lista_id: int, descricao: str, quantidade: float, preco: float | None) -> dict:
        return self._post(
            f"/compras/listas/{lista_id}/itens",
            {"descricao": descricao, "quantidade": quantidade, "preco_estimado": preco},
        )

    def marcar_item(self, item_id: int, marcado: bool) -> dict:
        return self._patch(f"/compras/itens/{item_id}", {"marcado": marcado})

    # ---------- helpers ----------
    def _headers(self) -> dict:
        if not self.token:
            raise ApiError("Você precisa estar logado.")
        return {"Authorization": f"Bearer {self.token}"}

    def _get(self, path: str) -> dict:
        resp = self._client.get(path, headers=self._headers())
        return self._tratar(resp)

    def _post(self, path: str, payload: dict) -> dict:
        resp = self._client.post(path, json=payload, headers=self._headers())
        return self._tratar(resp)

    def _patch(self, path: str, payload: dict) -> dict:
        resp = self._client.patch(path, json=payload, headers=self._headers())
        return self._tratar(resp)

    def _tratar(self, resp: httpx.Response) -> dict:
        if resp.status_code >= 400:
            raise ApiError(self._erro(resp), resp.status_code)
        return resp.json()

    @staticmethod
    def _erro(resp: httpx.Response) -> str:
        try:
            dados = resp.json()
            return dados.get("detail") or "Erro desconhecido"
        except Exception:
            return f"Erro {resp.status_code}"


api = ApiClient()
