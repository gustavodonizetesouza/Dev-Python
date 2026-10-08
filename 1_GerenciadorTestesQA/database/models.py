"""Repositórios de acesso a dados."""
from .connection import Database


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
        sql += " ORDER BY id"  # ← ordena por ID, como pedido
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def modulos_com_testes():
        """Retorna apenas os módulos que possuem casos cadastrados (para o filtro)."""
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
        """Vincula casos selecionados ao ciclo (regressão + compliance)."""
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
        """Retorna % execução, % aprovação, contagens por status."""
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
