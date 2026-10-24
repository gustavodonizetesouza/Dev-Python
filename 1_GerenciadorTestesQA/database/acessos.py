"""Repositórios de segurança e controle de acesso (Fase 1 + mobilidade).

Escopo:
- PerfilRepositorio: catálogo de perfis (Administrador, Gerente, Líder de Teste,
  Testador, Visualizador) e permissões por perfil (usadas na Fase 2);
- UsuarioSistemaRepositorio: identidade de LOGIN (global, no banco de configuração)
  — autenticação, CRUD e proteções (último admin, não excluir a si mesmo);
- UsuarioClienteRepositorio: vínculo N:N usuário ↔ clientes (escopo de acesso
  que filtra o seletor de clientes do rodapé);
- ConexaoAcessoRepositorio: conexões PERMITIDAS ao usuário (join conexoes ×
  usuario_clientes) — alimenta o diálogo de seleção de conexão pós-login.

IMPORTANTE: 'usuarios_sistema' (login global) é diferente da tabela 'usuarios'
por cliente (catálogo de analistas/responsáveis dos casos).
"""
from .connection import Database
from utils.autenticacao import hash_senha, verificar_senha


class PerfilRepositorio:
    """Catálogo de perfis — semeado na inicialização (5 perfis fixos na Fase 1)."""

    @staticmethod
    def listar():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM perfis ORDER BY id")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(perfil_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM perfis WHERE id = ?", (perfil_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def permissoes_do_perfil(perfil_id):
        """Códigos de permissão do perfil (ex.: 'ciclos.gerenciar') — Fase 2."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT permissao FROM perfil_permissoes
            WHERE perfil_id = ? ORDER BY permissao
        """, (perfil_id,))
        perms = [r["permissao"] for r in cur.fetchall()]
        conn.close()
        return perms

    @staticmethod
    def usuario_tem_permissao(usuario, permissao):
        """Verifica se o usuário logado (dict do login) tem a permissão.

        Administrador tem tudo implicitamente. Base para a Fase 2.
        """
        if not usuario:
            return False
        if usuario.get("perfil_nome") == "Administrador":
            return True
        perfil_id = usuario.get("perfil_id")
        if not perfil_id:
            return False
        return permissao in PerfilRepositorio.permissoes_do_perfil(perfil_id)


class UsuarioSistemaRepositorio:
    """Identidade de login do sistema (global) — autenticação e gestão."""

    SENHA_PADRAO_ADMIN = "admin123"

    @staticmethod
    def listar():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.login, u.nome, u.perfil_id, u.ativo, u.criado_em,
                   p.nome AS perfil_nome,
                   (SELECT COUNT(*) FROM usuario_clientes uc
                    WHERE uc.usuario_id = u.id) AS total_clientes
            FROM usuarios_sistema u
            JOIN perfis p ON p.id = u.perfil_id
            ORDER BY u.login
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def obter(usuario_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.login, u.nome, u.perfil_id, u.ativo, u.criado_em,
                   p.nome AS perfil_nome
            FROM usuarios_sistema u
            JOIN perfis p ON p.id = u.perfil_id
            WHERE u.id = ?
        """, (usuario_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def inserir(login, nome, senha, perfil_id, ativo=1):
        login = (login or "").strip()
        nome = (nome or "").strip()
        if not login:
            return None, "Informe o login."
        if not nome:
            return None, "Informe o nome."
        if not senha:
            return None, "Informe a senha."
        if not perfil_id:
            return None, "Selecione o perfil."
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios_sistema WHERE login = ?", (login,))
        if cur.fetchone():
            conn.close()
            return None, f"Já existe um usuário com o login '{login}'."
        try:
            cur.execute("""
                INSERT INTO usuarios_sistema (login, nome, senha_hash, perfil_id, ativo)
                VALUES (?,?,?,?,?)
            """, (login, nome, hash_senha(senha), perfil_id, 1 if ativo else 0))
            conn.commit()
            novo_id = cur.lastrowid
            conn.close()
            return novo_id, None
        except Exception as e:
            conn.close()
            return None, str(e)

    @staticmethod
    def atualizar(usuario_id, dados, senha=None):
        """Atualiza o usuário. senha=None ou '' mantém a senha atual."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        novo_login = (dados.get("login") or "").strip()
        cur.execute("SELECT id FROM usuarios_sistema WHERE login=? AND id<>?",
                    (novo_login, usuario_id))
        if cur.fetchone():
            conn.close()
            return False, f"Já existe outro usuário com o login '{novo_login}'."
        if senha:
            cur.execute("""
                UPDATE usuarios_sistema
                SET login=?, nome=?, perfil_id=?, ativo=?, senha_hash=?
                WHERE id=?
            """, (novo_login, (dados.get("nome") or "").strip(),
                  dados.get("perfil_id"), 1 if dados.get("ativo", 1) else 0,
                  hash_senha(senha), usuario_id))
        else:
            cur.execute("""
                UPDATE usuarios_sistema
                SET login=?, nome=?, perfil_id=?, ativo=?
                WHERE id=?
            """, (novo_login, (dados.get("nome") or "").strip(),
                  dados.get("perfil_id"), 1 if dados.get("ativo", 1) else 0,
                  usuario_id))
        conn.commit()
        conn.close()
        return True, "Usuário atualizado."

    @staticmethod
    def excluir(usuario_id, usuario_logado_id=None):
        """Exclui o usuário e seus vínculos, com proteções de segurança."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios_sistema WHERE id=?", (usuario_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False, "Usuário não encontrado."
        if usuario_logado_id and usuario_id == usuario_logado_id:
            conn.close()
            return False, "Você não pode excluir o próprio usuário logado."
        eh_admin_ativo = False
        if row["perfil_id"]:
            cur.execute("SELECT nome FROM perfis WHERE id=?", (row["perfil_id"],))
            p = cur.fetchone()
            eh_admin_ativo = bool(p and p["nome"] == "Administrador" and row["ativo"])
        if eh_admin_ativo:
            cur.execute("""
                SELECT COUNT(*) FROM usuarios_sistema u
                JOIN perfis p ON p.id = u.perfil_id
                WHERE p.nome='Administrador' AND u.ativo=1
            """)
            if cur.fetchone()[0] <= 1:
                conn.close()
                return False, "Não é possível excluir o último Administrador ativo."
        cur.execute("DELETE FROM usuario_clientes WHERE usuario_id=?", (usuario_id,))
        cur.execute("DELETE FROM usuarios_sistema WHERE id=?", (usuario_id,))
        conn.commit()
        conn.close()
        return True, "Usuário excluído."

    @staticmethod
    def autenticar(login, senha):
        """Autentica e retorna o dict do usuário (sem o hash) ou None."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.*, p.nome AS perfil_nome
            FROM usuarios_sistema u
            JOIN perfis p ON p.id = u.perfil_id
            WHERE u.login = ? AND u.ativo = 1
        """, ((login or "").strip(),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        usuario = dict(row)
        if not verificar_senha(senha, usuario.get("senha_hash") or ""):
            return None
        usuario.pop("senha_hash", None)
        return usuario

    @staticmethod
    def admin_usa_senha_padrao():
        """True se o admin ainda usa a senha padrão (dica de primeiro acesso)."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.senha_hash FROM usuarios_sistema u
            JOIN perfis p ON p.id = u.perfil_id
            WHERE u.login='admin' AND p.nome='Administrador' AND u.ativo=1
        """)
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        return verificar_senha(UsuarioSistemaRepositorio.SENHA_PADRAO_ADMIN,
                               row["senha_hash"] or "")


class UsuarioClienteRepositorio:
    """Vínculo N:N usuário do sistema ↔ clientes (escopo de acesso)."""

    @staticmethod
    def listar_clientes(usuario_id, apenas_ativos=True):
        """Clientes vinculados ao usuário (o que ele vê no seletor do rodapé)."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        sql = """
            SELECT c.* FROM clientes c
            JOIN usuario_clientes uc ON uc.cliente_id = c.id
            WHERE uc.usuario_id = ?
        """
        if apenas_ativos:
            sql += " AND c.ativo = 1"
        sql += " ORDER BY c.nome"
        cur.execute(sql, (usuario_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def listar_todos_com_marcacao(usuario_id):
        """Todos os clientes com flag 'vinculado' (para o diálogo de vínculos)."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, CASE WHEN uc.usuario_id IS NOT NULL THEN 1 ELSE 0 END AS vinculado
            FROM clientes c
            LEFT JOIN usuario_clientes uc
                   ON uc.cliente_id = c.id AND uc.usuario_id = ?
            ORDER BY c.nome
        """, (usuario_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def definir_vinculos(usuario_id, cliente_ids):
        """Substitui todos os vínculos do usuário pela lista informada."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM usuario_clientes WHERE usuario_id=?", (usuario_id,))
        for cid in (cliente_ids or []):
            if cid is None:
                continue
            cur.execute("""
                INSERT OR IGNORE INTO usuario_clientes (usuario_id, cliente_id)
                VALUES (?,?)
            """, (usuario_id, cid))
        conn.commit()
        conn.close()

    @staticmethod
    def pode_acessar(usuario_id, cliente_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM usuario_clientes
            WHERE usuario_id=? AND cliente_id=?
        """, (usuario_id, cliente_id))
        ok = cur.fetchone() is not None
        conn.close()
        return ok


class ConexaoAcessoRepositorio:
    """Conexões PERMITIDAS ao usuário — alimenta o diálogo de seleção pós-login.

    Regra: o usuário vê as conexões dos clientes a que está vinculado
    (usuario_clientes). Administrador vê todas as conexões.
    """

    @staticmethod
    def listar_conexoes_permitidas(usuario):
        """Lista de conexões (dict) visíveis ao usuário logado, com o cliente."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        if usuario and usuario.get("perfil_nome") == "Administrador":
            cur.execute("""
                SELECT cx.*, cl.nome AS cliente_nome
                FROM conexoes cx
                LEFT JOIN clientes cl ON cl.id = cx.cliente_id
                ORDER BY cl.nome, cx.nome
            """)
        else:
            if not usuario or not usuario.get("id"):
                conn.close()
                return []
            cur.execute("""
                SELECT cx.*, cl.nome AS cliente_nome
                FROM conexoes cx
                LEFT JOIN clientes cl ON cl.id = cx.cliente_id
                JOIN usuario_clientes uc ON uc.cliente_id = cx.cliente_id
                WHERE uc.usuario_id = ?
                ORDER BY cl.nome, cx.nome
            """, (usuario["id"],))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows