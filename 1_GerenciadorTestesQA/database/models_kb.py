"""Repositórios da Base de Conhecimento (artigos_kb, kb_vinculos).

Regras:
- Busca por código de erro Protheus (SX6/SX7) é prioridade máxima;
- Busca textual em titulo/sintoma/solucao/tags;
- Registro de utilidade (sim/não) por chamado, para ranquear;
- Contador de visualizações incrementado a cada abertura.
"""
from datetime import datetime

from .connection import Database


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_codigo(prefixo, numero, tamanho=4):
    return f"{prefixo}-{numero:0{tamanho}d}"


class KbRepositorio:
    """Artigos da Base de Conhecimento."""

    @staticmethod
    def _proximo_codigo():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM artigos_kb")
        total = cur.fetchone()[0]
        conn.close()
        return _fmt_codigo("KB", total + 1)

    # ---------- Busca ----------
    @staticmethod
    def buscar(termo=None, codigo_erro=None, modulo=None, limite=50):
        """Busca artigos publicados.

        Ordem de relevância:
          1) Match exato de código de erro (prioridade absoluta)
          2) Match textual em titulo/sintoma/solucao/tags
          3) Ordem decrescente de utilidade (util_sim - util_nao)
        """
        conn = Database.get_connection()
        cur = conn.cursor()
        sql = """
            SELECT *, (util_sim - util_nao) AS score_util
              FROM artigos_kb
             WHERE publicado = 1
        """
        params = []
        if codigo_erro:
            sql += " AND UPPER(codigo_erro) = UPPER(?)"
            params.append(codigo_erro.strip())
        if modulo:
            sql += " AND modulo = ?"
            params.append(modulo)
        if termo:
            sql += """ AND (titulo LIKE ? OR sintoma LIKE ?
                          OR solucao LIKE ? OR tags LIKE ? OR codigo LIKE ?)"""
            t = f"%{termo.strip()}%"
            params.extend([t, t, t, t, t])
        sql += " ORDER BY score_util DESC, visualizacoes DESC, id DESC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()][:limite]
        conn.close()
        return rows

    @staticmethod
    def sugerir_para_chamado(titulo, descricao=None, codigo_erro=None,
                             limite=5):
        """Sugestão proativa antes de abrir chamado.

        Usa código de erro quando disponível; senão usa o título como termo.
        Retorna lista vazia quando não há nada relevante.
        """
        if codigo_erro:
            encontrados = KbRepositorio.buscar(codigo_erro=codigo_erro,
                                               limite=limite)
            if encontrados:
                return encontrados
        # Fallback: tenta as 3 primeiras palavras significativas do título
        termo = None
        if titulo:
            palavras = [p for p in titulo.split() if len(p) > 3]
            if palavras:
                termo = " ".join(palavras[:3])
        if not termo and descricao:
            palavras = [p for p in descricao.split() if len(p) > 5]
            if palavras:
                termo = " ".join(palavras[:3])
        if not termo:
            return []
        return KbRepositorio.buscar(termo=termo, limite=limite)

    # ---------- CRUD ----------
    @staticmethod
    def obter(artigo_id, incrementar_visualizacao=False):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM artigos_kb WHERE id = ?", (artigo_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        if incrementar_visualizacao:
            KbRepositorio.incrementar_visualizacao(artigo_id)
        return dict(row)

    @staticmethod
    def inserir(dados, autor_login=None):
        """Cria um artigo. Retorna (novo_id, codigo)."""
        codigo = KbRepositorio._proximo_codigo()
        agora = _agora()
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO artigos_kb
                (codigo, titulo, sintoma, causa_raiz, solucao, tags, modulo,
                 codigo_erro, autor, chamado_origem_id, publicado,
                 criado_em, atualizado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (codigo, dados["titulo"], dados["sintoma"],
              dados.get("causa_raiz"), dados["solucao"],
              dados.get("tags"), dados.get("modulo"),
              dados.get("codigo_erro"), autor_login,
              dados.get("chamado_origem_id"),
              1 if dados.get("publicado", True) else 0,
              agora, agora))
        novo_id = cur.lastrowid
        conn.commit()
        conn.close()
        return novo_id, codigo

    @staticmethod
    def atualizar(artigo_id, dados):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE artigos_kb
               SET titulo=?, sintoma=?, causa_raiz=?, solucao=?, tags=?,
                   modulo=?, codigo_erro=?, publicado=?, atualizado_em=?
             WHERE id=?
        """, (dados["titulo"], dados["sintoma"], dados.get("causa_raiz"),
              dados["solucao"], dados.get("tags"), dados.get("modulo"),
              dados.get("codigo_erro"),
              1 if dados.get("publicado", True) else 0,
              _agora(), artigo_id))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(artigo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM artigos_kb WHERE id=?", (artigo_id,))
        conn.commit()
        conn.close()

    # ---------- Métricas ----------
    @staticmethod
    def incrementar_visualizacao(artigo_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE artigos_kb SET visualizacoes = visualizacoes + 1 "
                    "WHERE id=?", (artigo_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def registrar_utilidade(artigo_id, util):
        """util=True -> util_sim+1; False -> util_nao+1."""
        campo = "util_sim" if util else "util_nao"
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE artigos_kb SET {campo} = {campo} + 1 WHERE id=?",
                    (artigo_id,))
        conn.commit()
        conn.close()

    # ---------- Vínculo chamado ↔ KB ----------
    @staticmethod
    def vincular_chamado(chamado_id, artigo_id, util=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO kb_vinculos (chamado_id, artigo_id, util, criado_em)
                VALUES (?,?,?,?)
            """, (chamado_id, artigo_id, util, _agora()))
        except Exception:
            # Vínculo já existe (UNIQUE) — atualiza utilidades
            cur.execute("""
                UPDATE kb_vinculos SET util=COALESCE(?, util)
                WHERE chamado_id=? AND artigo_id=?
            """, (util, chamado_id, artigo_id))
        conn.commit()
        conn.close()

    @staticmethod
    def listar_vinculos(chamado_id):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.*, a.codigo, a.titulo
              FROM kb_vinculos v
              JOIN artigos_kb a ON a.id = v.artigo_id
             WHERE v.chamado_id = ?
             ORDER BY v.criado_em DESC
        """, (chamado_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def kpis():
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN publicado=1 THEN 1 ELSE 0 END) AS publicados,
                SUM(CASE WHEN publicado=0 THEN 1 ELSE 0 END) AS rascunhos,
                COALESCE(SUM(visualizacoes), 0) AS visualizacoes,
                COALESCE(SUM(util_sim), 0) AS util_sim,
                COALESCE(SUM(util_nao), 0) AS util_nao
              FROM artigos_kb
        """)
        row = cur.fetchone()
        d = dict(row) if row else {}
        for k in ("total", "publicados", "rascunhos",
                  "visualizacoes", "util_sim", "util_nao"):
            d[k] = d.get(k) or 0
        conn.close()
        return d
