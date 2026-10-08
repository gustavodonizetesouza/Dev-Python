"""Funções utilitárias compartilhadas."""

STATUS_OPCOES = ["Não iniciado", "Em andamento",
                 "Aprovado", "Reprovado", "Bloqueado"]
TIPOS_OPCOES = ["Funcional", "Regressão", "Compliance", "Carga", "Integração"]
PRIORIDADES_OPCOES = ["Alta", "Média", "Baixa"]

# Mapeamento de status para cor (hex) — reflete a legenda da sua planilha
STATUS_CORES = {
    "Não iniciado": "#FFFFFF",
    "Em andamento": "#C6EFCE",
    "Aprovado": "#63BE7B",
    "Reprovado": "#FF7C80",
    "Bloqueado": "#FFC000",
}

# Módulos Protheus comuns — ajuste conforme seu ambiente
MODULOS_PROTHEUS = [
    "SIGAFAT", "SIGAFIS", "SIGAEST", "SIGAPCP", "SIGACFG",
    "SIGAFIN", "SIGACOM", "SIGAPES", "SIGAADM", "SIGAINT",
]


def normalizar_status(valor):
    """Normaliza variações de escrita para o enum padrão."""
    v = (valor or "").strip().lower()
    mapa = {
        "nao iniciado": "Não iniciado", "não iniciado": "Não iniciado", "": "Não iniciado",
        "em andamento": "Em andamento", "andamento": "Em andamento",
        "aprovado": "Aprovado", "concluido": "Aprovado", "concluído": "Aprovado",
        "reprovado": "Reprovado", "falhou": "Reprovado",
        "bloqueado": "Bloqueado", "bloqueio": "Bloqueado",
    }
    return mapa.get(v, "Não iniciado")
