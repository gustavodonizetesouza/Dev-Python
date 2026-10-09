"""Repositórios de acesso a dados."""
from .connection import Database
from utils.seguranca import salvar_senha


class ModuloRepositorio:
    @staticmethod
    def listar():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM modulos ORDER BY nome")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir(nome):
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO modulos (nome) VALUES (?)",
                        (nome.strip().upper(),))
            conn.commit()
            novo_id = cur.lastrowid
            conn.close()
            return novo_id, None
        except Exception as e:
            conn.close()
            return None, str(e)

    @staticmethod
    def atualizar(modulo_id, novo_nome):
        """
        Renomeia o módulo e atualiza TUDO que o referencia:
        - casos_teste.modulo
        - melhorias.modulo
        Feito em transação: ou renomeia tudo, ou nada (rollback).
        """
        novo_nome = novo_nome.strip().upper()
        if not novo_nome:
            return False, "Informe o novo nome do módulo."
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            # Pega o nome atual antes de renomear
            cur.execute("SELECT nome FROM modulos WHERE id = ?", (modulo_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return False, "Módulo não encontrado."
            antigo_nome = row[0]
            if antigo_nome == novo_nome:
                conn.close()
                return False, "O novo nome é igual ao atual."
            # Evita duplicidade (o nome é UNIQUE)
            cur.execute("SELECT id FROM modulos WHERE nome = ? AND id <> ?",
                        (novo_nome, modulo_id))
            if cur.fetchone():
                conn.close()
                return False, f"Já existe um módulo com o nome '{novo_nome}'."
            # Renomeia no cadastro e em tudo que referencia (transação)
            cur.execute("UPDATE modulos SET nome = ? WHERE id = ?",
                        (novo_nome, modulo_id))
            cur.execute("UPDATE casos_teste SET modulo = ? WHERE modulo = ?",
                        (novo_nome, antigo_nome))
            cur.execute("UPDATE melhorias SET modulo = ? WHERE modulo = ?",
                        (novo_nome, antigo_nome))
            conn.commit()
            conn.close()
            return True, f"Módulo '{antigo_nome}' renomeado para '{novo_nome}'. Casos e melhorias vinculados foram atualizados."
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

    @staticmethod
    def excluir(modulo_id):
        """Exclui um módulo. Retorna False se ele estiver em uso por casos de teste."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT nome FROM modulos WHERE id = ?", (modulo_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        cur.execute(
            "SELECT COUNT(*) FROM casos_teste WHERE modulo = ?", (row[0],))
        if cur.fetchone()[0] > 0:
            conn.close()
            return False
        cur.execute("DELETE FROM modulos WHERE id = ?", (modulo_id,))
        conn.commit()
        conn.close()
        return True


class UsuarioRepositorio:
    @staticmethod
    def listar(apenas_ativos=True):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM usuarios"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir(dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (nome, email, cargo, ativo)
            VALUES (?,?,?,?)
        """, (dados["nome"], dados.get("email"), dados.get("cargo"),
              dados.get("ativo", 1)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(usuario_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios SET nome=?, email=?, cargo=?, ativo=? WHERE id=?
        """, (dados["nome"], dados.get("email"), dados.get("cargo"),
              dados.get("ativo", 1), usuario_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(usuario_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
        conn.commit()
        conn.close()


class CasoRepositorio:
    @staticmethod
    def listar(filtro_modulo=None, filtro_tipo=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM casos_teste WHERE 1=1"
        params = []
        if filtro_modulo:
            sql += " AND modulo = ?"
            params.append(filtro_modulo)
        if filtro_tipo:
            sql += " AND tipo = ?"
            params.append(filtro_tipo)
        sql += " ORDER BY id"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def modulos_com_testes():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT modulo FROM casos_teste ORDER BY modulo")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(caso_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM casos_teste WHERE id = ?", (caso_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO casos_teste
                (codigo, tarefa, descricao, modulo, rotina, tipo, prioridade, responsavel, requisito_compliance)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (dados["codigo"], dados.get("tarefa"), dados["descricao"], dados["modulo"],
              dados.get("rotina"), dados.get("tipo", "Funcional"),
              dados.get("prioridade", "Media"), dados.get("responsavel"),
              dados.get("requisito_compliance")))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(caso_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE casos_teste SET codigo=?, tarefa=?, descricao=?, modulo=?, rotina=?, tipo=?,
                prioridade=?, responsavel=?, requisito_compliance=?
            WHERE id=?
        """, (dados["codigo"], dados.get("tarefa"), dados["descricao"], dados["modulo"],
              dados.get("rotina"), dados.get("tipo"), dados.get("prioridade"),
              dados.get("responsavel"), dados.get("requisito_compliance"), caso_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(caso_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM casos_teste WHERE id=?", (caso_id,))
        conn.commit()
        conn.close()


class CicloRepositorio:
    @staticmethod
    def listar():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ciclos ORDER BY ano DESC, id DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir(dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ciclos (nome, versao, ano, data_inicio, data_fim, status)
            VALUES (?,?,?,?,?,?)
        """, (dados["nome"], dados.get("versao"), dados.get("ano"),
              dados.get("data_inicio"), dados.get("data_fim"), dados.get("status", "Planejado")))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def associar_casos(ciclo_id, caso_ids):
        conn = Database.get_connection()
        cur = conn.cursor()
        for cid in caso_ids:
            cur.execute("""
                INSERT OR IGNORE INTO ciclo_casos (ciclo_id, caso_id)
                VALUES (?,?)
            """, (ciclo_id, cid))
        conn.commit()
        conn.close()

    @staticmethod
    def desvincular_casos(ciclo_id, caso_ids):
        conn = Database.get_connection()
        cur = conn.cursor()
        for cid in caso_ids:
            cur.execute(
                "DELETE FROM ciclo_casos WHERE ciclo_id=? AND caso_id=?", (ciclo_id, cid))
        conn.commit()
        conn.close()

    @staticmethod
    def casos_vinculados(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT caso_id FROM ciclo_casos WHERE ciclo_id = ?", (ciclo_id,))
        ids = {r[0] for r in cur.fetchall()}
        conn.close()
        return ids

    @staticmethod
    def casos_do_ciclo(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT cc.*, c.codigo, c.tarefa, c.descricao, c.modulo, c.rotina, c.tipo, c.prioridade,
                   c.requisito_compliance
            FROM ciclo_casos cc
            JOIN casos_teste c ON c.id = cc.caso_id
            WHERE cc.ciclo_id = ?
            ORDER BY c.id
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def atualizar_execucao(cc_id, status, percentual, responsavel, horas_reais, evidencia, observacoes):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE ciclo_casos SET status=?, percentual=?, responsavel=?, horas_reais=?,
                evidencia=?, observacoes=?, atualizado_em=datetime('now','localtime')
            WHERE id=?
        """, (status, percentual, responsavel, horas_reais, evidencia, observacoes, cc_id))
        conn.commit()
        conn.close()

    @staticmethod
    def kpis(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('Aprovado','Concluido') THEN 1 ELSE 0 END) AS aprovados,
                SUM(CASE WHEN status IN ('Em andamento','Em Andamento') THEN 1 ELSE 0 END) AS andamento,
                SUM(CASE WHEN status IN ('Reprovado','Bloqueado') THEN 1 ELSE 0 END) AS defeitos,
                SUM(CASE WHEN status NOT IN ('Nao iniciado','Não iniciado') THEN 1 ELSE 0 END) AS executados,
                COALESCE(AVG(percentual), 0) AS perc_medio
            FROM ciclo_casos WHERE ciclo_id = ?
        """, (ciclo_id,))
        row = cur.fetchone()
        conn.close()
        if not row or row[0] == 0:
            return {"total": 0, "aprovados": 0, "andamento": 0, "defeitos": 0,
                    "executados": 0, "perc_medio": 0}
        total = row[0]
        return {
            "total": total,
            "aprovados": row[1] or 0,
            "andamento": row[2] or 0,
            "defeitos": row[3] or 0,
            "executados": row[4] or 0,
            "perc_medio": round(row[5] or 0, 1),
            "perc_execucao": round((row[4] or 0) / total * 100, 1),
            "perc_aprovacao": round((row[1] or 0) / total * 100, 1),
        }


class ConexaoRepositorio:
    @staticmethod
    def listar():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conexoes ORDER BY nome")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(conexao_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conexoes WHERE id=?", (conexao_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(dados, senha):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO conexoes (nome, cliente, tipo, host, porta, banco, usuario, driver)
            VALUES (?,?,?,?,?,?,?,?)
        """, (dados["nome"], dados.get("cliente"), dados["tipo"],
              dados.get("host"), dados.get("porta"), dados.get("banco"),
              dados.get("usuario"), dados.get("driver")))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        if senha:
            salvar_senha(novo_id, senha)
        return novo_id

    @staticmethod
    def atualizar(conexao_id, dados, senha=None):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE conexoes SET nome=?, cliente=?, tipo=?, host=?, porta=?,
                banco=?, usuario=?, driver=? WHERE id=?
        """, (dados["nome"], dados.get("cliente"), dados["tipo"],
              dados.get("host"), dados.get("porta"), dados.get("banco"),
              dados.get("usuario"), dados.get("driver"), conexao_id))
        conn.commit()
        conn.close()
        if senha:
            salvar_senha(conexao_id, senha)

    @staticmethod
    def excluir(conexao_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM conexoes WHERE id=?", (conexao_id,))
        conn.commit()
        conn.close()


class MelhoriaRepositorio:
    """Controle de melhorias propostas durante os testes.

    Uma melhoria pode se tornar um caso de teste (gerar_caso_teste),
    criando um vínculo rastreável (melhorias.caso_teste_id).
    """

    STATUS_OPCOES = ["Proposta", "Em análise",
                     "Aprovada", "Implementada", "Recusada"]

    @staticmethod
    def _proximo_codigo():
        """Gera o próximo código sequencial (MEL-001, MEL-002...)."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM melhorias")
        total = cur.fetchone()[0]
        conn.close()
        return f"MEL-{total + 1:03d}"

    @staticmethod
    def listar(filtro_status=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM melhorias WHERE 1=1"
        params = []
        if filtro_status:
            sql += " AND status = ?"
            params.append(filtro_status)
        sql += " ORDER BY id DESC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(melhoria_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM melhorias WHERE id = ?", (melhoria_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        codigo = MelhoriaRepositorio._proximo_codigo()
        cur.execute("""
            INSERT INTO melhorias
                (codigo, titulo, descricao, modulo, prioridade, status, responsavel,
                 ciclo_id, caso_origem_id, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (codigo, dados["titulo"], dados.get("descricao"), dados.get("modulo"),
              dados.get("prioridade", "Media"), dados.get(
                  "status", "Proposta"),
              dados.get("responsavel"), dados.get(
                  "ciclo_id"), dados.get("caso_origem_id"),
              dados.get("observacoes")))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(melhoria_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        data_impl = None
        if dados.get("status") == "Implementada":
            data_impl = "datetime('now','localtime')"
        cur.execute("""
            UPDATE melhorias SET titulo=?, descricao=?, modulo=?, prioridade=?, status=?,
                responsavel=?, observacoes=?, data_implementacao=COALESCE(?, data_implementacao)
            WHERE id=?
        """, (dados["titulo"], dados.get("descricao"), dados.get("modulo"),
              dados.get("prioridade", "Media"), dados.get(
                  "status", "Proposta"),
              dados.get("responsavel"), dados.get("observacoes"), data_impl, melhoria_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(melhoria_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM melhorias WHERE id=?", (melhoria_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def gerar_caso_teste(melhoria_id):
        """Transforma a melhoria em um caso de teste no catálogo.

        Cria um caso novo (herdando título/descrição/módulo/prioridade da melhoria)
        e grava o vínculo em melhorias.caso_teste_id.
        Retorna (ok, mensagem, caso_id).
        """
        melhoria = MelhoriaRepositorio.obter(melhoria_id)
        if not melhoria:
            return False, "Melhoria não encontrada.", None
        if melhoria.get("caso_teste_id"):
            return False, "Esta melhoria já gerou um caso de teste.", melhoria["caso_teste_id"]
        if melhoria.get("status") != "Implementada":
            return False, "A melhoria precisa estar 'Implementada' para gerar um caso de teste.", None

        # Cria o caso de teste no catálogo
        caso_id = CasoRepositorio.inserir({
            "codigo": melhoria["codigo"],
            "tarefa": melhoria["titulo"],
            "descricao": melhoria.get("descricao") or melhoria["titulo"],
            "modulo": melhoria.get("modulo") or "Geral",
            "prioridade": melhoria.get("prioridade", "Media"),
            "tipo": "Funcional",
            "responsavel": melhoria.get("responsavel"),
        })

        # Grava o vínculo
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE melhorias SET caso_teste_id=? WHERE id=?",
                    (caso_id, melhoria_id))
        conn.commit()
        conn.close()

        return True, f"Caso de teste {melhoria['codigo']} criado a partir da melhoria.", caso_id
