"""Repositórios de Chamados, Subtarefas, Histórico, SLA e Base de Conhecimento.

Convenções do projeto:
- SQL neutro de dialeto (parâmetros '?'), portável SQLite/SQL Server;
- Timestamps como string ISO, nunca datetime('now');
- Cálculo de SLA em tempo real + snapshot dos prazos na abertura;
- Histórico é APPEND-ONLY: nunca UPDATE, nunca DELETE;
- Códigos gerados (CHM-0001, KB-0001) com padding de 4 dígitos;
- IDs obtidos via cur.lastrowid — o _CursorCompat do connection.py
  captura o IDENTITY automaticamente (OUTPUT INSERTED.id no SQL Server).
"""
from datetime import datetime, timedelta

from .connection import Database


def _agora():
    """Timestamp ISO consistente entre dialetos (NVARCHAR(30))."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_codigo(prefixo, numero, tamanho=4):
    return f"{prefixo}-{numero:0{tamanho}d}"


class SlaConfigRepositorio:
    """Configuração de SLA por prioridade (tabela sla_config)."""

    @staticmethod
    def listar():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM sla_config
            WHERE ativo = 1
            ORDER BY horas_resolucao
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter_por_prioridade(prioridade):
        """Retorna {'horas_resposta', 'horas_resolucao'} ou None."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT horas_resposta, horas_resolucao FROM sla_config
            WHERE prioridade = ? AND ativo = 1
        """, ((prioridade or "").strip(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def atualizar(prioridade, horas_resposta, horas_resolucao):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE sla_config SET horas_resposta=?, horas_resolucao=?
            WHERE prioridade = ?
        """, (horas_resposta, horas_resolucao, prioridade))
        conn.commit()
        conn.close()


class ChamadoHistoricoRepositorio:
    """Linha do tempo do chamado (APPEND-ONLY: só INSERT)."""

    @staticmethod
    def registrar(chamado_id, tipo_evento, autor, comentario=None,
                  de_status=None, para_status=None):
        if chamado_id is None:
            raise ValueError(
                "chamado_id não pode ser nulo ao registrar histórico. "
                "Verifique se cur.lastrowid retornou o ID após o INSERT.")
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chamado_historico
                (chamado_id, tipo_evento, de_status, para_status, autor,
                 comentario, criado_em)
            VALUES (?,?,?,?,?,?,?)
        """, (chamado_id, tipo_evento, de_status, para_status, autor,
              comentario, _agora()))
        conn.commit()
        conn.close()

    @staticmethod
    def listar(chamado_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chamado_historico
            WHERE chamado_id = ?
            ORDER BY criado_em, id
        """, (chamado_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows


class ChamadoTarefaRepositorio:
    """Subtarefas dentro de um chamado (checklist de atividades)."""

    STATUS_OPCOES = ["Pendente", "Em andamento", "Concluida", "Cancelada"]

    @staticmethod
    def listar(chamado_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chamado_tarefas
            WHERE chamado_id = ?
            ORDER BY ordem, id
        """, (chamado_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def inserir(chamado_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(MAX(ordem),0)+1 FROM chamado_tarefas
            WHERE chamado_id = ?
        """, (chamado_id,))
        ordem = cur.fetchone()[0]
        status = dados.get("status", "Pendente")
        concluida_em = _agora() if status == "Concluida" else None
        cur.execute("""
            INSERT INTO chamado_tarefas
                (chamado_id, titulo, descricao, responsavel, status, ordem,
                 prazo, concluida_em)
            VALUES (?,?,?,?,?,?,?,?)
        """, (chamado_id, dados["titulo"], dados.get("descricao"),
              dados.get("responsavel"), status, ordem,
              dados.get("prazo"), concluida_em))
        novo_id = cur.lastrowid
        conn.commit()
        conn.close()
        return novo_id

    @staticmethod
    def atualizar(tarefa_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        status = dados.get("status", "Pendente")
        concluida_em = _agora() if status == "Concluida" else None
        cur.execute("""
            UPDATE chamado_tarefas
               SET titulo=?, descricao=?, responsavel=?, status=?, prazo=?,
                   concluida_em=COALESCE(?, concluida_em)
             WHERE id=?
        """, (dados["titulo"], dados.get("descricao"), dados.get("responsavel"),
              status, dados.get("prazo"), concluida_em, tarefa_id))
        conn.commit()
        conn.close()

    @staticmethod
    def concluir(tarefa_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE chamado_tarefas SET status='Concluida', concluida_em=?
            WHERE id=?
        """, (_agora(), tarefa_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(tarefa_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chamado_tarefas WHERE id=?", (tarefa_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def progresso(chamado_id):
        """Retorna (total, concluidas) — para a barra de progresso."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chamado_tarefas WHERE chamado_id=?",
                    (chamado_id,))
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM chamado_tarefas
            WHERE chamado_id=? AND status='Concluida'
        """, (chamado_id,))
        prontas = cur.fetchone()[0]
        conn.close()
        return total, prontas


class ChamadoRepositorio:
    """Chamados de suporte — núcleo do módulo.

    Ciclo de vida: Aberto -> Em atendimento -> Aguardando terceiro
                  -> Resolvido -> Encerrado
    Saídas do encerramento: virar Melhoria (melhoria_id) ou virar KB (artigo_id).
    """

    STATUS_OPCOES = ["Aberto", "Em atendimento", "Aguardando terceiro",
                     "Resolvido", "Encerrado"]
    TIPO_OPCOES = ["Suporte", "Bug", "Melhoria", "Duvida"]
    ORIGEM_OPCOES = ["Manual", "Caso Reprovado", "Melhoria", "KB"]
    SEVERIDADE_OPCOES = ["Critica", "Alta", "Media", "Baixa"]
    AMBIENTE_OPCOES = ["Produção", "Homologação", "Teste", "Treinamento"]

    # Transições permitidas (bloqueia saltos incoerentes no fluxo)
    _TRANSICOES = {
        "Aberto": {"Em atendimento", "Aguardando terceiro",
                   "Resolvido", "Encerrado"},
        "Em atendimento": {"Aguardando terceiro", "Resolvido",
                           "Encerrado", "Aberto"},
        "Aguardando terceiro": {"Em atendimento", "Resolvido", "Encerrado"},
        "Resolvido": {"Em atendimento", "Encerrado"},
        "Encerrado": set(),  # terminal
    }

    # ---------- Geração de código ----------
    @staticmethod
    def _proximo_codigo():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chamados")
        total = cur.fetchone()[0]
        conn.close()
        return _fmt_codigo("CHM", total + 1)

    # ---------- Cálculo de prazo (SLA) ----------
    @staticmethod
    def _prazos_por_prioridade(prioridade):
        """Retorna (prazo_resposta_iso, prazo_resolucao_iso)."""
        cfg = SlaConfigRepositorio.obter_por_prioridade(prioridade)
        if not cfg:
            cfg = {"horas_resposta": 24, "horas_resolucao": 72}
        base = datetime.now()
        resp = (base + timedelta(hours=float(cfg["horas_resposta"]))).strftime(
            "%Y-%m-%d %H:%M:%S")
        reso = (base + timedelta(hours=float(cfg["horas_resolucao"]))).strftime(
            "%Y-%m-%d %H:%M:%S")
        return resp, reso

    @staticmethod
    def _sla_atrasado(row):
        """True se não resolvido e já passou do prazo de resolução."""
        if not row:
            return False
        if row.get("resolvido_em"):
            return False
        prazo = row.get("prazo_resolucao")
        if not prazo:
            return False
        try:
            return datetime.now() > datetime.strptime(prazo, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return False

    # ---------- CRUD ----------
    @staticmethod
    def listar(filtro_status=None, filtro_responsavel=None, filtro_ciclo=None,
               filtro_tipo=None, busca=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = """
            SELECT c.*,
                   (SELECT COUNT(*) FROM chamado_tarefas t
                     WHERE t.chamado_id = c.id AND t.status='Concluida')
                       AS tarefas_ok,
                   (SELECT COUNT(*) FROM chamado_tarefas t
                     WHERE t.chamado_id = c.id) AS tarefas_total
              FROM chamados c
             WHERE 1=1
        """
        params = []
        if filtro_status:
            sql += " AND c.status = ?"
            params.append(filtro_status)
        if filtro_responsavel:
            sql += " AND c.responsavel = ?"
            params.append(filtro_responsavel)
        if filtro_ciclo:
            sql += " AND c.ciclo_id = ?"
            params.append(filtro_ciclo)
        if filtro_tipo:
            sql += " AND c.tipo = ?"
            params.append(filtro_tipo)
        if busca:
            sql += " AND (c.titulo LIKE ? OR c.descricao LIKE ? OR c.codigo LIKE ?)"
            termo = f"%{busca}%"
            params.extend([termo, termo, termo])
        sql += " ORDER BY id DESC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            r["sla_atrasado"] = ChamadoRepositorio._sla_atrasado(r)
        return rows

    @staticmethod
    def obter(chamado_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM chamados WHERE id = ?", (chamado_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["sla_atrasado"] = ChamadoRepositorio._sla_atrasado(d)
        return d

    @staticmethod
    def inserir(dados, autor_login=None):
        """Abre um chamado com histórico na MESMA transação.

        Atomicidade: chamado e histórico são gravados juntos. Se o histórico
        falhar, o chamado é desfeito (rollback) — nunca fica chamado órfão.
        """
        prioridade = dados.get("prioridade", "Media")
        prazo_resp, prazo_reso = ChamadoRepositorio._prazos_por_prioridade(
            prioridade)
        codigo = ChamadoRepositorio._proximo_codigo()
        agora = _agora()
        status_inicial = dados.get("status", "Aberto")

        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO chamados
                    (codigo, titulo, descricao, tipo, origem, prioridade,
                     severidade, status, responsavel, solicitante, modulo,
                     ambiente, ciclo_id, caso_teste_id,
                     prazo_resposta, prazo_resolucao, criado_por, atualizado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (codigo, dados["titulo"], dados["descricao"],
                  dados.get("tipo", "Suporte"), dados.get("origem", "Manual"),
                  prioridade, dados.get("severidade"), status_inicial,
                  dados.get("responsavel"), dados.get("solicitante"),
                  dados.get("modulo"), dados.get("ambiente"),
                  dados.get("ciclo_id"), dados.get("caso_teste_id"),
                  prazo_resp, prazo_reso, autor_login, agora))

            novo_id = cur.lastrowid
            if novo_id is None:
                raise RuntimeError(
                    "O chamado foi inserido, mas cur.lastrowid retornou None. "
                    "Verifique o _CursorCompat no connection.py.")

            cur.execute("""
                INSERT INTO chamado_historico
                    (chamado_id, tipo_evento, de_status, para_status, autor,
                     comentario, criado_em)
                VALUES (?,?,?,?,?,?,?)
            """, (novo_id, "status", None, status_inicial,
                  autor_login or dados.get("criado_por"),
                  "Chamado aberto.", agora))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return novo_id, codigo

    @staticmethod
    def atualizar(chamado_id, dados, autor_login=None):
        """Atualiza o cabeçalho do chamado. Valida transição de status."""
        atual = ChamadoRepositorio.obter(chamado_id)
        if not atual:
            return False, "Chamado não encontrado."
        novo_status = dados.get("status", atual.get("status"))
        if novo_status != atual.get("status"):
            permitidos = ChamadoRepositorio._TRANSICOES.get(
                atual["status"], set())
            if novo_status not in permitidos:
                return False, (
                    f"Transição inválida: '{atual['status']}' → '{novo_status}'.\n"
                    f"Permitidos: {', '.join(sorted(permitidos)) or 'nenhum'}."
                )
        conn = Database.get_connection()
        cur = conn.cursor()
        agora = _agora()
        cur.execute("""
            UPDATE chamados
               SET titulo=?, descricao=?, tipo=?, prioridade=?, severidade=?,
                   status=?, responsavel=?, solicitante=?, modulo=?,
                   ambiente=?, solucao=?, ciclo_id=?, atualizado_em=?
             WHERE id=?
        """, (dados["titulo"], dados["descricao"],
              dados.get("tipo", atual.get("tipo")),
              dados.get("prioridade", atual.get("prioridade")),
              dados.get("severidade"), novo_status,
              dados.get("responsavel"), dados.get("solicitante"),
              dados.get("modulo"), dados.get("ambiente"),
              dados.get("solucao"), dados.get("ciclo_id"),
              agora, chamado_id))
        conn.commit()
        conn.close()
        if novo_status != atual.get("status"):
            ChamadoHistoricoRepositorio.registrar(
                chamado_id, "status", autor_login,
                de_status=atual.get("status"), para_status=novo_status)
        return True, "Chamado atualizado."

    @staticmethod
    def mudar_status(chamado_id, novo_status, autor_login=None, comentario=None):
        """Troca de status com validação de transição e log no histórico."""
        atual = ChamadoRepositorio.obter(chamado_id)
        if not atual:
            return False, "Chamado não encontrado."
        permitidos = ChamadoRepositorio._TRANSICOES.get(atual["status"], set())
        if novo_status not in permitidos:
            return False, (
                f"Transição inválida: '{atual['status']}' → '{novo_status}'. "
                f"Permitidos a partir de '{atual['status']}': "
                f"{', '.join(sorted(permitidos)) or 'nenhum'}.")
        campos_extra = ""
        params_extra = []
        if novo_status == "Resolvido" and not atual.get("resolvido_em"):
            campos_extra += ", resolvido_em=?"
            params_extra.append(_agora())
        if novo_status == "Encerrado" and not atual.get("encerrado_em"):
            campos_extra += ", encerrado_em=?"
            params_extra.append(_agora())
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE chamados SET status=?{campos_extra}, atualizado_em=?
            WHERE id=?
        """, [novo_status] + params_extra + [_agora(), chamado_id])
        conn.commit()
        conn.close()
        ChamadoHistoricoRepositorio.registrar(
            chamado_id, "status", autor_login,
            de_status=atual["status"], para_status=novo_status,
            comentario=comentario)
        return True, f"Status alterado para '{novo_status}'."

    @staticmethod
    def registrar_primeira_resposta(chamado_id, autor_login=None):
        """Marca a primeira resposta do SLA (idempotente)."""
        atual = ChamadoRepositorio.obter(chamado_id)
        if not atual or atual.get("primeira_resposta_em"):
            return False
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE chamados SET primeira_resposta_em=? WHERE id=?",
                    (_agora(), chamado_id))
        conn.commit()
        conn.close()
        ChamadoHistoricoRepositorio.registrar(
            chamado_id, "sla", autor_login,
            comentario="Primeira resposta registrada.")
        return True

    @staticmethod
    def comentar(chamado_id, autor_login, comentario):
        ChamadoHistoricoRepositorio.registrar(
            chamado_id, "comentario", autor_login, comentario=comentario)
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE chamados SET atualizado_em=? WHERE id=?",
                    (_agora(), chamado_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def excluir(chamado_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chamados WHERE id=?", (chamado_id,))
        conn.commit()
        conn.close()

    # ---------- Vínculos com Melhoria e KB (Pacote 2) ----------
    @staticmethod
    def vincular_melhoria(chamado_id, melhoria_id):
        """Vincula o chamado a uma melhoria criada (rastreabilidade)."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chamados SET melhoria_id=?, atualizado_em=? WHERE id=?",
            (melhoria_id, _agora(), chamado_id))
        conn.commit()
        conn.close()

    @staticmethod
    def vincular_artigo_kb(chamado_id, artigo_id):
        """Vincula o chamado a um artigo da Base de Conhecimento."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chamados SET artigo_id=?, atualizado_em=? WHERE id=?",
            (artigo_id, _agora(), chamado_id))
        conn.commit()
        conn.close()

    # ---------- KPIs / Dashboard ----------
    @staticmethod
    def kpis():
        """KPIs gerais do módulo de chamados."""
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='Aberto' THEN 1 ELSE 0 END) AS abertos,
                SUM(CASE WHEN status='Em atendimento' THEN 1 ELSE 0 END) AS atendimento,
                SUM(CASE WHEN status='Aguardando terceiro' THEN 1 ELSE 0 END) AS aguardando,
                SUM(CASE WHEN status='Resolvido' THEN 1 ELSE 0 END) AS resolvidos,
                SUM(CASE WHEN status='Encerrado' THEN 1 ELSE 0 END) AS encerrados
              FROM chamados
        """)
        row = cur.fetchone()
        d = dict(row) if row else {}
        for k in ("total", "abertos", "atendimento", "aguardando",
                  "resolvidos", "encerrados"):
            d[k] = d.get(k) or 0
        cur.execute("""
            SELECT prazo_resolucao FROM chamados
            WHERE status NOT IN ('Resolvido','Encerrado')
              AND resolvido_em IS NULL
        """)
        atrasados = 0
        for r in cur.fetchall():
            prazo = dict(r).get("prazo_resolucao")
            if not prazo:
                continue
            try:
                if datetime.now() > datetime.strptime(prazo, "%Y-%m-%d %H:%M:%S"):
                    atrasados += 1
            except (ValueError, TypeError):
                pass
        conn.close()
        d["sla_atrasado"] = atrasados
        return d
