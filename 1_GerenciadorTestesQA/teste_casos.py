"""Teste rápido da camada de dados — rode no terminal: python teste_casos.py"""
from database.models import CicloRepositorio, CasoRepositorio, ModuloRepositorio
from database.connection import Database
import sys
import traceback

sys.path.insert(0, ".")


def main():
    # Mesmo fluxo de inicialização do app
    Database.init_config_db()
    Database.init_db()

    cliente = Database._get_cliente_ativo()
    print("Cliente ativo:", cliente)
    if cliente and cliente.get("id"):
        cfg = Database._get_conexao_padrao_cliente(cliente["id"])
        print("Conexão do cliente:", cfg)
    else:
        print("SEM cliente ativo -> dados vão para MEMÓRIA (somem ao fechar o app).")

    # --- Módulo ---
    mod_id, erro = ModuloRepositorio.inserir("MODULO TESTE")
    print("Inserir módulo ->", mod_id, erro)
    print("Módulos:", [m["nome"] for m in ModuloRepositorio.listar()])

    # --- Ciclo ---
    ciclo_id = CicloRepositorio.inserir({
        "nome": "Ciclo Teste",
        "tipo": "Virada de Versão",
        "ano": 2026,
        "status": "Planejado",
    })
    print("Ciclo criado -> ID", ciclo_id)

    # --- Caso DENTRO do ciclo ---
    novo_id, codigo = CasoRepositorio.inserir(ciclo_id, {
        "tarefa": "Testar X",
        "descricao": "Verificar funcionamento",
        "modulo": "MODULO TESTE",
        "tipo": "Funcional",
        "prioridade": "Media",
    })
    print("Caso criado -> ID", novo_id, "| Código", codigo)

    casos = CasoRepositorio.listar(ciclo_id)
    print("Casos dentro do ciclo:", [
          (c["id"], c["codigo"], c["ciclo_id"]) for c in casos])
    print("SUCESSO: a camada de dados grava e lê o vínculo ciclo -> caso.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nERRO NA CAMADA DE DADOS (copie tudo abaixo e me envie):")
        traceback.print_exc()
