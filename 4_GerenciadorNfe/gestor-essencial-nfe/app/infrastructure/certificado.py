"""Carga do certificado digital A1 (.pfx) e geração de PEM para TLS mútuo."""
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


@dataclass
class CertificadoDigital:
    chave: object                  # RSAPrivateKey
    certificado: object            # x509.Certificate

    @classmethod
    def carregar_pfx(cls, caminho: str | Path, senha: str) -> "CertificadoDigital":
        with open(caminho, "rb") as f:
            chave, certificado, _ = pkcs12.load_key_and_certificates(
                f.read(), senha.encode(), None
            )
        if chave is None or certificado is None:
            raise ValueError("PFX inválido ou senha incorreta")
        return cls(chave=chave, certificado=certificado)

    def gerar_pem_para_tls(self, pasta_tmp: Path) -> tuple[Path, Path]:
        """Converte PFX em cert.pem + key.pem temporários para o mTLS do httpx."""
        cert_pem = pasta_tmp / "cert.pem"
        key_pem = pasta_tmp / "key.pem"
        cert_pem.write_bytes(
            self.certificado.public_bytes(serialization.Encoding.PEM)
        )
        key_pem.write_bytes(
            self.chave.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        key_pem.chmod(0o600)  # segurança: só o dono lê a chave
        return cert_pem, key_pem

    def certificado_base64_dersha256(self) -> str:
        import base64
        return base64.b64encode(
            self.certificado.public_bytes(serialization.Encoding.DER)
        ).decode()
