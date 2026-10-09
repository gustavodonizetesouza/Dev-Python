"""Repositórios de acesso a dados."""
from .connection import Database
from utils.seguranca import salvar_senha


class ClienteRepositorio:
    @staticmethod
    def listar(apenas_ativos=True):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM clientes"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(cliente_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(dados):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO clientes (nome, ativo, observacoes) VALUES (?,?,?)",
                    (dados["nome"], dados.get("ativo", 1), dados.get("observacoes")))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        Database.ajustar_cliente_ativo()
        return novo_id

    @staticmethod
    def atualizar(cliente_id, dados):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("UPDATE clientes SET nome=?, ativo=?, observacoes=? WHERE id=?",
                    (dados["nome"], dados.get("ativo", 1), dados.get("observacoes"), cliente_id))
        conn.commit()
        conn.close()
        Database.ajustar_cliente_ativo()

    @staticmethod
    def excluir(cliente_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM conexoes WHERE cliente_id=?", (cliente_id,))
        if cur.fetchone()[0] > 0:
            conn.close()
            return False
        cur.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
        conn.commit()
        conn.close()
        Database.ajustar_cliente_ativo()
        return True


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
        novo_nome = novo_nome.strip().upper()
        if not novo_nome:
            return False, "Informe o novo nome do módulo."
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT nome FROM modulos WHERE id = ?", (modulo_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return False, "Módulo não encontrado."
            antigo_nome = row[0]
            if antigo_nome == novo_nome:
                conn.close()
                return False, "O novo nome é igual ao atual."
            cur.execute("SELECT id FROM modulos WHERE nome = ? AND id <> ?",
                        (novo_nome, modulo_id))
            if cur.fetchone():
                conn.close()
                return False, f"Já existe um módulo com o nome '{novo_nome}'."
            cur.execute("UPDATE modulos SET nome = ? WHERE id = ?",
                        (novo_nome, modulo_id))
            cur.execute("UPDATE casos_teste SET modulo = ? WHERE modulo = ?",
                        (novo_nome, antigo_nome))
            cur.execute("UPDATE melhorias SET modulo = ? WHERE modulo = ?",
                        (novo_nome, antigo_nome))
            conn.commit()
            conn.close()
            return True, f"Módulo renomeado para '{novo_nome}'. Casos e melhorias vinculados atualizados."
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

    @staticmethod
    def excluir(modulo_id):
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
        cur.execute("INSERT INTO usuarios (nome, email, cargo, ativo) VALUES (?,?,?,?)",
                    (dados["nome"], dados.get("email"), dados.get("cargo"),
                     dados.get("ativo", 1)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(usuario_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET nome=?, email=?, cargo=?, ativo=? WHERE id=?",
                    (dados["nome"], dados.get("email"), dados.get("cargo"),
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


class TipoCicloRepositorio:
    @staticmethod
    def listar():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tipos_ciclo ORDER BY nome")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir(nome):
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO tipos_ciclo (nome) VALUES (?)",
                        (nome.strip().upper(),))
            conn.commit()
            novo_id = cur.lastrowid
            conn.close()
            return novo_id, None
        except Exception as e:
            conn.close()
            return None, str(e)

    @staticmethod
    def atualizar(tipo_id, novo_nome):
        novo_nome = novo_nome.strip().upper()
        if not novo_nome:
            return False, "Informe o novo nome do tipo."
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT nome FROM tipos_ciclo WHERE id = ?", (tipo_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return False, "Tipo não encontrado."
            antigo_nome = row[0]
            if antigo_nome == novo_nome:
                conn.close()
                return False, "O novo nome é igual ao atual."
            cur.execute("SELECT id FROM tipos_ciclo WHERE nome = ? AND id <> ?",
                        (novo_nome, tipo_id))
            if cur.fetchone():
                conn.close()
                return False, f"Já existe um tipo com o nome '{novo_nome}'."
            cur.execute(
                "UPDATE tipos_ciclo SET nome = ? WHERE id = ?", (novo_nome, tipo_id))
            cur.execute("UPDATE ciclos SET tipo = ? WHERE tipo = ?",
                        (novo_nome, antigo_nome))
            conn.commit()
            conn.close()
            return True, f"Tipo renomeado para '{novo_nome}'. Ciclos vinculados atualizados."
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

    @staticmethod
    def excluir(tipo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT nome FROM tipos_ciclo WHERE id = ?", (tipo_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        cur.execute("SELECT COUNT(*) FROM ciclos WHERE tipo = ?", (row[0],))
        if cur.fetchone()[0] > 0:
            conn.close()
            return False
        cur.execute("DELETE FROM tipos_ciclo WHERE id = ?", (tipo_id,))
        conn.commit()
        conn.close()
        return True


class CicloRepositorio:
    """Ciclos — a unidade completa de trabalho."""

    STATUS_OPCOES = ["Planejado", "Em andamento", "Concluído", "Cancelado"]

    @staticmethod
    def listar_tipos():
        return [t["nome"] for t in TipoCicloRepositorio.listar()]

    @staticmethod
    def listar(filtro_status=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM ciclos WHERE 1=1"
        params = []
        if filtro_status:
            sql += " AND status = ?"
            params.append(filtro_status)
        sql += " ORDER BY ano DESC, id DESC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ciclos WHERE id = ?", (ciclo_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ciclos (nome, tipo, versao, ano, data_inicio, data_fim,
                                status, responsavel, custo_orcado)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (dados["nome"], dados.get("tipo", "Virada de Versão"), dados.get("versao"),
              dados.get("ano"), dados.get(
                  "data_inicio"), dados.get("data_fim"),
              dados.get("status", "Planejado"), dados.get("responsavel"),
              dados.get("custo_orcado", 0)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE ciclos SET nome=?, tipo=?, versao=?, ano=?, data_inicio=?, data_fim=?,
                status=?, responsavel=?, custo_orcado=? WHERE id=?
        """, (dados["nome"], dados.get("tipo", "Virada de Versão"), dados.get("versao"),
              dados.get("ano"), dados.get(
                  "data_inicio"), dados.get("data_fim"),
              dados.get("status", "Planejado"), dados.get("responsavel"),
              dados.get("custo_orcado", 0), ciclo_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ciclos WHERE id=?", (ciclo_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def copiar(ciclo_id):
        """Copia o ciclo: novo ciclo com os mesmos casos, etapas e rotinas (execução reiniciada)."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ciclos WHERE id=?", (ciclo_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None, "Ciclo não encontrado."
        origem = dict(row)
        cur.execute("""
            INSERT INTO ciclos (nome, tipo, versao, ano, data_inicio, data_fim,
                                status, responsavel, custo_orcado)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (f"{origem.get('nome')} (cópia)", origem.get("tipo") or "Virada de Versão",
              origem.get("versao"), origem.get(
                  "ano"), origem.get("data_inicio"),
              origem.get("data_fim"), "Planejado", origem.get("responsavel"),
              origem.get("custo_orcado") or 0))
        novo_id = cur.lastrowid

        casos = cur.execute(
            "SELECT * FROM casos_teste WHERE ciclo_id=?", (ciclo_id,)).fetchall()
        for c in casos:
            cur.execute("""
                INSERT INTO casos_teste
                    (ciclo_id, codigo, tarefa, descricao, modulo, rotina, tipo, prioridade,
                     responsavel, requisito_compliance, status_exec, percentual, horas_estimadas)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (novo_id, c["codigo"], c["tarefa"], c["descricao"], c["modulo"],
                  c["rotina"], c["tipo"], c["prioridade"], c["responsavel"],
                  c["requisito_compliance"], "Nao iniciado", 0, c["horas_estimadas"] or 0))

        mapa_etapa = {}
        for e in cur.execute(
                "SELECT * FROM ciclo_etapas WHERE ciclo_id=?", (ciclo_id,)).fetchall():
            cur.execute("""
                INSERT INTO ciclo_etapas (ciclo_id, nome, descricao, ordem, responsavel,
                                          status, percentual, data_prevista_inicio,
                                          data_prevista_fim, custo_orcado)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (novo_id, e["nome"], e["descricao"], e["ordem"] or 0,
                  e["responsavel"], "Nao iniciada", 0, e["data_prevista_inicio"],
                  e["data_prevista_fim"], e["custo_orcado"] or 0))
            mapa_etapa[e["id"]] = cur.lastrowid

        for r in cur.execute(
                "SELECT * FROM ciclo_rotinas WHERE ciclo_id=?", (ciclo_id,)).fetchall():
            cur.execute("""
                INSERT INTO ciclo_rotinas (codigo, ciclo_id, etapa_id, nome, descricao,
                                           status, responsavel, horas_estimadas)
                VALUES (?,?,?,?,?,?,?,?)
            """, (f"{r['codigo']}-C{novo_id}", novo_id, mapa_etapa.get(r["etapa_id"]),
                  r["nome"], r["descricao"], "Pendente", r["responsavel"],
                  r["horas_estimadas"] or 0))

        conn.commit()
        conn.close()
        return novo_id, f"Ciclo copiado! {len(casos)} caso(s), etapas e rotinas reaproveitados (execução reiniciada)."

    @staticmethod
    def casos_do_ciclo(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM casos_teste
            WHERE ciclo_id = ?
            ORDER BY id
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def contar_casos(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM casos_teste WHERE ciclo_id=?", (ciclo_id,))
        total = cur.fetchone()[0]
        conn.close()
        return total

    @staticmethod
    def atualizar_execucao(caso_id, status, percentual, responsavel, horas_reais,
                           evidencia, observacoes):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE casos_teste SET status_exec=?, percentual=?, responsavel=?, horas_reais=?,
                evidencia=?, observacoes=?, atualizado_em=datetime('now','localtime')
            WHERE id=?
        """, (status, percentual, responsavel, horas_reais, evidencia, observacoes, caso_id))
        conn.commit()
        conn.close()

    @staticmethod
    def kpis(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status_exec IN ('Aprovado','Concluido') THEN 1 ELSE 0 END) AS aprovados,
                SUM(CASE WHEN status_exec IN ('Em andamento','Em Andamento') THEN 1 ELSE 0 END) AS andamento,
                SUM(CASE WHEN status_exec IN ('Reprovado','Bloqueado') THEN 1 ELSE 0 END) AS defeitos,
                SUM(CASE WHEN status_exec NOT IN ('Nao iniciado','Não iniciado') THEN 1 ELSE 0 END) AS executados,
                COALESCE(AVG(percentual), 0) AS perc_medio
            FROM casos_teste WHERE ciclo_id = ?
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


class CasoRepositorio:
    """Casos de teste — nascem dentro de um ciclo e ficam presos a ele."""

    @staticmethod
    def _proximo_codigo(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM casos_teste WHERE ciclo_id=?", (ciclo_id,))
        n = cur.fetchone()[0] + 1
        conn.close()
        return f"TC{ciclo_id:02d}-{n:03d}"

    @staticmethod
    def listar(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM casos_teste WHERE ciclo_id = ? ORDER BY id", (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
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
    def inserir(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        codigo = dados.get(
            "codigo") or CasoRepositorio._proximo_codigo(ciclo_id)
        cur.execute("""
            INSERT INTO casos_teste (ciclo_id, codigo, tarefa, descricao, modulo, rotina,
                                     tipo, prioridade, responsavel, requisito_compliance,
                                     horas_estimadas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (ciclo_id, codigo, dados.get("tarefa"), dados["descricao"], dados["modulo"],
              dados.get("rotina"), dados.get("tipo", "Funcional"),
              dados.get("prioridade", "Media"), dados.get("responsavel"),
              dados.get("requisito_compliance"), dados.get("horas_estimadas", 0)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id, codigo

    @staticmethod
    def atualizar(caso_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE casos_teste SET codigo=?, tarefa=?, descricao=?, modulo=?, rotina=?,
                tipo=?, prioridade=?, responsavel=?, requisito_compliance=?, horas_estimadas=?
            WHERE id=?
        """, (dados.get("codigo"), dados.get("tarefa"), dados["descricao"], dados["modulo"],
              dados.get("rotina"), dados.get("tipo", "Funcional"),
              dados.get("prioridade", "Media"), dados.get("responsavel"),
              dados.get("requisito_compliance"), dados.get("horas_estimadas", 0), caso_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(caso_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM casos_teste WHERE id=?", (caso_id,))
        conn.commit()
        conn.close()


class CicloDetalheRepositorio:
    """Etapas, rotinas, horas, custos e KPIs de gestão de um ciclo."""

    STATUS_ETAPA_OPCOES = ["Não iniciada",
                           "Em andamento", "Concluída", "Bloqueada"]
    STATUS_ROTINA_OPCOES = ["Pendente",
                            "Em andamento", "Concluída", "Cancelada"]
    CATEGORIAS_CUSTO = ["Terceiros", "Licenças", "Despesas", "Outros"]

    @staticmethod
    def listar_etapas(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.*,
                   (SELECT COALESCE(SUM(h.horas),0) FROM ciclo_horas h
                    WHERE h.etapa_id = e.id) AS horas_reais,
                   (SELECT COALESCE(SUM(h.horas*h.custo_hora),0) FROM ciclo_horas h
                    WHERE h.etapa_id = e.id) AS custo_horas
            FROM ciclo_etapas e
            WHERE e.ciclo_id = ?
            ORDER BY e.ordem, e.id
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir_etapa(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(ordem),0)+1 FROM ciclo_etapas WHERE ciclo_id=?",
                    (ciclo_id,))
        ordem = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO ciclo_etapas (ciclo_id, nome, descricao, ordem, responsavel,
                                      status, percentual, data_prevista_inicio,
                                      data_prevista_fim, custo_orcado)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (ciclo_id, dados["nome"], dados.get("descricao"), ordem,
              dados.get("responsavel"), dados.get("status", "Não iniciada"),
              dados.get("percentual", 0), dados.get("data_prevista_inicio"),
              dados.get("data_prevista_fim"), dados.get("custo_orcado", 0)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar_etapa(etapa_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE ciclo_etapas SET nome=?, descricao=?, responsavel=?, status=?,
                percentual=?, data_prevista_inicio=?, data_prevista_fim=?, custo_orcado=?
            WHERE id=?
        """, (dados["nome"], dados.get("descricao"), dados.get("responsavel"),
              dados.get("status", "Não iniciada"), dados.get("percentual", 0),
              dados.get("data_prevista_inicio"), dados.get(
                  "data_prevista_fim"),
              dados.get("custo_orcado", 0), etapa_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir_etapa(etapa_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE ciclo_rotinas SET etapa_id=NULL WHERE etapa_id=?", (etapa_id,))
        cur.execute(
            "UPDATE ciclo_horas SET etapa_id=NULL WHERE etapa_id=?", (etapa_id,))
        cur.execute(
            "UPDATE ciclo_custos SET etapa_id=NULL WHERE etapa_id=?", (etapa_id,))
        cur.execute("DELETE FROM ciclo_etapas WHERE id=?", (etapa_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def listar_rotinas(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, e.nome AS etapa_nome, c.codigo AS caso_codigo
            FROM ciclo_rotinas r
            LEFT JOIN ciclo_etapas e ON e.id = r.etapa_id
            LEFT JOIN casos_teste c ON c.id = r.caso_teste_id
            WHERE r.ciclo_id = ?
            ORDER BY r.id
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def _proximo_codigo_rotina(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM ciclo_rotinas WHERE ciclo_id=?", (ciclo_id,))
        n = cur.fetchone()[0] + 1
        conn.close()
        return f"ROT{ciclo_id:02d}-{n:03d}"

    @staticmethod
    def inserir_rotina(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        codigo = CicloDetalheRepositorio._proximo_codigo_rotina(ciclo_id)
        cur.execute("""
            INSERT INTO ciclo_rotinas (codigo, ciclo_id, etapa_id, nome, descricao,
                                       status, responsavel, horas_estimadas)
            VALUES (?,?,?,?,?,?,?,?)
        """, (codigo, ciclo_id, dados.get("etapa_id"), dados["nome"],
              dados.get("descricao"), dados.get("status", "Pendente"),
              dados.get("responsavel"), dados.get("horas_estimadas", 0)))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        return novo_id

    @staticmethod
    def atualizar_rotina(rotina_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE ciclo_rotinas SET etapa_id=?, nome=?, descricao=?, status=?,
                responsavel=?, horas_estimadas=? WHERE id=?
        """, (dados.get("etapa_id"), dados["nome"], dados.get("descricao"),
              dados.get("status", "Pendente"), dados.get("responsavel"),
              dados.get("horas_estimadas", 0), rotina_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir_rotina(rotina_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ciclo_rotinas WHERE id=?", (rotina_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def gerar_caso_teste(rotina_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ciclo_rotinas WHERE id=?", (rotina_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False, "Rotina não encontrada.", None
        rotina = dict(row)
        if rotina.get("caso_teste_id"):
            conn.close()
            return False, "Esta rotina já gerou um caso de teste.", rotina["caso_teste_id"]
        if rotina.get("status") != "Concluída":
            conn.close()
            return False, "A rotina precisa estar 'Concluída' para gerar um caso de teste.", None
        ciclo = cur.execute("SELECT * FROM ciclos WHERE id=?",
                            (rotina["ciclo_id"],)).fetchone()
        conn.close()
        modulo = ciclo["nome"] if ciclo else "Geral"
        caso_id, codigo = CasoRepositorio.inserir(rotina["ciclo_id"], {
            "codigo": rotina["codigo"],
            "tarefa": rotina["nome"],
            "descricao": rotina.get("descricao") or rotina["nome"],
            "modulo": modulo,
            "prioridade": "Media",
            "tipo": "Funcional",
            "responsavel": rotina.get("responsavel"),
        })
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE ciclo_rotinas SET caso_teste_id=? WHERE id=?",
                    (caso_id, rotina_id))
        conn.commit()
        conn.close()
        return True, f"Caso de teste {codigo} criado no ciclo a partir da rotina.", caso_id

    @staticmethod
    def listar_horas(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT h.*, e.nome AS etapa_nome, r.nome AS rotina_nome
            FROM ciclo_horas h
            LEFT JOIN ciclo_etapas e ON e.id = h.etapa_id
            LEFT JOIN ciclo_rotinas r ON r.id = h.rotina_id
            WHERE h.ciclo_id = ?
            ORDER BY h.data DESC, h.id DESC
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir_hora(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ciclo_horas (ciclo_id, etapa_id, rotina_id, lancado_por,
                                     data, horas, custo_hora, descricao)
            VALUES (?,?,?,?,?,?,?,?)
        """, (ciclo_id, dados.get("etapa_id"), dados.get("rotina_id"),
              dados.get("lancado_por"), dados.get("data"),
              dados.get("horas", 0), dados.get("custo_hora", 0),
              dados.get("descricao")))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir_hora(hora_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ciclo_horas WHERE id=?", (hora_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def listar_custos(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, e.nome AS etapa_nome
            FROM ciclo_custos c
            LEFT JOIN ciclo_etapas e ON e.id = c.etapa_id
            WHERE c.ciclo_id = ?
            ORDER BY c.data DESC, c.id DESC
        """, (ciclo_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir_custo(ciclo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ciclo_custos (ciclo_id, etapa_id, descricao, categoria, valor, data)
            VALUES (?,?,?,?,?,?)
        """, (ciclo_id, dados.get("etapa_id"), dados["descricao"],
              dados.get("categoria", "Outros"), dados.get("valor", 0), dados.get("data")))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir_custo(custo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ciclo_custos WHERE id=?", (custo_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def kpis_gestao(ciclo_id):
        conn = Database.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status IN ('Concluida','Concluída') THEN 1 ELSE 0 END) AS concluidas,
                   COALESCE(AVG(percentual), 0) AS andamento
            FROM ciclo_etapas WHERE ciclo_id = ?
        """, (ciclo_id,))
        e = cur.fetchone()

        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status IN ('Concluida','Concluída') THEN 1 ELSE 0 END) AS concluidas,
                   COALESCE(SUM(horas_estimadas), 0) AS horas_estimadas
            FROM ciclo_rotinas WHERE ciclo_id = ?
        """, (ciclo_id,))
        r = cur.fetchone()

        cur.execute("""
            SELECT COALESCE(SUM(horas), 0) AS horas,
                   COALESCE(SUM(horas * custo_hora), 0) AS custo_horas
            FROM ciclo_horas WHERE ciclo_id = ?
        """, (ciclo_id,))
        h = cur.fetchone()

        cur.execute("""
            SELECT COALESCE(SUM(valor), 0) AS total FROM ciclo_custos WHERE ciclo_id = ?
        """, (ciclo_id,))
        c = cur.fetchone()

        cur.execute("SELECT custo_orcado FROM ciclos WHERE id = ?", (ciclo_id,))
        p = cur.fetchone()
        conn.close()

        horas_reais = h[0] or 0
        custo_horas = h[1] or 0
        custo_adicionais = c[0] or 0
        custo_real = round(custo_horas + custo_adicionais, 2)
        custo_orcado = p[0] or 0

        return {
            "etapas_total": e[0] or 0,
            "etapas_concluidas": e[1] or 0,
            "andamento": round(e[2] or 0, 1),
            "rotinas_total": r[0] or 0,
            "rotinas_concluidas": r[1] or 0,
            "horas_estimadas": round(r[2] or 0, 2),
            "horas_reais": round(horas_reais, 2),
            "custo_orcado": round(custo_orcado, 2),
            "custo_horas": round(custo_horas, 2),
            "custo_adicionais": round(custo_adicionais, 2),
            "custo_real": custo_real,
            "variacao": round(custo_orcado - custo_real, 2),
            "perc_orcado_usado": round(custo_real / custo_orcado * 100, 1) if custo_orcado else 0,
        }


class MelhoriaRepositorio:
    STATUS_OPCOES = ["Proposta", "Em análise",
                     "Aprovada", "Implementada", "Recusada"]

    @staticmethod
    def _proximo_codigo():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM melhorias")
        total = cur.fetchone()[0]
        conn.close()
        return f"MEL-{total + 1:03d}"

    @staticmethod
    def listar(filtro_status=None, filtro_ciclo=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM melhorias WHERE 1=1"
        params = []
        if filtro_status:
            sql += " AND status = ?"
            params.append(filtro_status)
        if filtro_ciclo:
            sql += " AND ciclo_id = ?"
            params.append(filtro_ciclo)
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
                responsavel=?, observacoes=?, ciclo_id=?,
                data_implementacao=COALESCE(?, data_implementacao)
            WHERE id=?
        """, (dados["titulo"], dados.get("descricao"), dados.get("modulo"),
              dados.get("prioridade", "Media"), dados.get(
                  "status", "Proposta"),
              dados.get("responsavel"), dados.get(
                  "observacoes"), dados.get("ciclo_id"),
              data_impl, melhoria_id))
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
    def gerar_caso_no_ciclo(melhoria_id, ciclo_id):
        melhoria = MelhoriaRepositorio.obter(melhoria_id)
        if not melhoria:
            return False, "Melhoria não encontrada.", None
        if melhoria.get("caso_teste_id"):
            return False, "Esta melhoria já gerou um caso de teste.", melhoria["caso_teste_id"]
        if melhoria.get("status") not in ("Aprovada", "Implementada"):
            return False, "A melhoria precisa estar 'Aprovada' ou 'Implementada' para gerar um caso.", None
        if not ciclo_id:
            return False, "Selecione (ou crie) um ciclo para gerar o caso.", None
        caso_id, codigo = CasoRepositorio.inserir(ciclo_id, {
            "codigo": melhoria["codigo"],
            "tarefa": melhoria["titulo"],
            "descricao": melhoria.get("descricao") or melhoria["titulo"],
            "modulo": melhoria.get("modulo") or "Geral",
            "prioridade": melhoria.get("prioridade", "Media"),
            "tipo": "Funcional",
            "responsavel": melhoria.get("responsavel"),
        })
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE melhorias SET caso_teste_id=?, ciclo_id=COALESCE(ciclo_id, ?) WHERE id=?",
                    (caso_id, ciclo_id, melhoria_id))
        conn.commit()
        conn.close()
        return True, f"Caso de teste {codigo} criado no ciclo a partir da melhoria.", caso_id


class ConexaoRepositorio:
    @staticmethod
    def listar():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, cl.nome AS cliente_nome
            FROM conexoes c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            ORDER BY c.nome
        """)
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
    def inserir(dados, senha, cliente_id=None):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        if cliente_id is None:
            cliente = Database._get_cliente_ativo()
            cliente_id = cliente.get("id") if cliente else None
        cur.execute(
            "SELECT COUNT(*) FROM conexoes WHERE cliente_id=?", (cliente_id,))
        tem_conexao = cur.fetchone()[0] > 0
        padrao = 0 if tem_conexao else 1
        cur.execute("""
            INSERT INTO conexoes (nome, cliente, tipo, host, porta, banco, usuario, driver, cliente_id, padrao)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (dados["nome"], dados.get("cliente"), dados["tipo"],
              dados.get("host"), dados.get("porta"), dados.get("banco"),
              dados.get("usuario"), dados.get("driver"), cliente_id, padrao))
        conn.commit()
        novo_id = cur.lastrowid
        conn.close()
        if senha:
            salvar_senha(novo_id, senha)
        return novo_id

    @staticmethod
    def atualizar(conexao_id, dados, senha=None, cliente_id=None):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        if cliente_id is None:
            cliente = Database._get_cliente_ativo()
            cliente_id = cliente.get("id") if cliente else None
        cur.execute("""
            UPDATE conexoes SET nome=?, cliente=?, tipo=?, host=?, porta=?,
                banco=?, usuario=?, driver=?, cliente_id=? WHERE id=?
        """, (dados["nome"], dados.get("cliente"), dados["tipo"],
              dados.get("host"), dados.get("porta"), dados.get("banco"),
              dados.get("usuario"), dados.get("driver"), cliente_id, conexao_id))
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
