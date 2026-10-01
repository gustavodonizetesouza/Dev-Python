# ============================================
# repositories/auth_repository.py
# Autenticação de usuário.
# Valida a senha contra o hash do ASP.NET Identity
# (PBKDF2) gravado na tabela AspNetUsers.
# ============================================
import base64
import hmac
import hashlib
from database import Database


class AuthRepository:
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifica a senha digitada contra o hash do ASP.NET Identity.

        Formato do hash (base64):
            [byte 0 = versão][salt 16 bytes][subkey 32 bytes]
        """
        try:
            decoded = base64.b64decode(password_hash)
        except Exception:
            return False

        # Estrutura mínima: 1 (versão) + 16 (salt) + 32 (subkey) = 49 bytes
        if len(decoded) < 49:
            return False

        version = decoded[0]
        salt = decoded[1:17]      # 16 bytes (128 bits)
        subkey = decoded[17:49]   # 32 bytes (256 bits)

        # Define algoritmo e iterações conforme a versão do hash
        if version == 0x00:       # v2: PBKDF2-HMAC-SHA1, 1000 iterações
            iterations, hash_name = 1000, "sha1"
        elif version == 0x01:     # v3: PBKDF2-HMAC-SHA512, 100000 iterações
            iterations, hash_name = 100000, "sha512"
        else:
            return False

        # Recalcula o PBKDF2 com o mesmo salt da senha armazenada
        derived = hashlib.pbkdf2_hmac(
            hash_name, password.encode("utf-8"), salt, iterations, dklen=32
        )

        # Comparação em tempo constante (evita timing attack)
        return hmac.compare_digest(derived, subkey)

    @staticmethod
    def authenticate(email: str, password: str):
        """Busca o usuário no banco e valida a senha.

        Retorna um dict com os dados do usuário (email e perfil)
        se o login for válido; caso contrário, retorna None.
        """
        rows = Database.query(
            """
            SELECT u.Email, u.PasswordHash, r.Name
            FROM AspNetUsers u
            LEFT JOIN AspNetUserRoles ur ON ur.UserId = u.Id
            LEFT JOIN AspNetRoles r ON r.Id = ur.RoleId
            WHERE u.NormalizedEmail = UPPER(?)
            """,
            (email.strip(),),
        )

        if not rows:
            return None

        user_email, password_hash, role = rows[0]

        if not AuthRepository.verify_password(password, password_hash):
            return None

        return {
            "email": user_email,
            "role": role or "Sem perfil",
        }
