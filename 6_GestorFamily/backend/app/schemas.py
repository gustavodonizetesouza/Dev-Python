from pydantic import BaseModel, EmailStr, Field

class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)

class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr

    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ListaCompraCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)

class ItemCompraCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    quantidade: float = 1
    preco_estimado: float | None = None

class ItemPatch(BaseModel):
    marcado: bool

class ItemCompraOut(BaseModel):
    id: int
    descricao: str
    quantidade: float
    preco_estimado: float | None
    marcado: bool

    model_config = {"from_attributes": True}

class ListaCompraOut(BaseModel):
    id: int
    nome: str
    itens: list[ItemCompraOut] = []
    total_estimado: float = 0

    model_config = {"from_attributes": True}