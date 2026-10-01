# ============================================
# views/error_dialog.py
# Janela que exibe erros COMPLETOS (sem truncamento).
# Mostra o tipo do erro, a mensagem integral e o traceback
# (pilha de chamadas) em caixa rolável, com botão "Copiar"
# para facilitar o diagnóstico.
# ============================================
import traceback
import customtkinter as ctk


def show_error(parent, title, error):
    """Abre uma janela modal com o erro completo.

    Parâmetros:
        parent: janela pai (ex.: a tela de login)
        title:  título da janela de erro
        error:  exceção (Exception) ou texto (str) do erro
    """
    # Monta o detalhamento: tipo + mensagem + traceback
    if isinstance(error, Exception):
        details = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
    else:
        details = str(error)

    janela = ctk.CTkToplevel(parent)
    janela.title(title)
    janela.geometry("750x450")
    janela.minsize(550, 320)
    janela.transient(parent)
    janela.grab_set()  # modal: bloqueia a janela pai até fechar

    # Título da janela de erro
    ctk.CTkLabel(
        janela, text=title, font=("Arial", 16, "bold")
    ).pack(padx=15, pady=(15, 5), anchor="w")

    # Subtítulo explicativo
    ctk.CTkLabel(
        janela,
        text="Mensagem completa do erro abaixo. Use o botão Copiar para salvar o diagnóstico.",
        text_color="gray",
        font=("Arial", 11),
    ).pack(padx=15, pady=(0, 10), anchor="w")

    # Caixa de texto rolável com o erro completo
    texto = ctk.CTkTextbox(janela, font=("Consolas", 12))
    texto.pack(fill="both", expand=True, padx=15, pady=(0, 10))
    texto.insert("1.0", details)

    # Barra de botões
    rodape = ctk.CTkFrame(janela, fg_color="transparent")
    rodape.pack(fill="x", padx=15, pady=(0, 15))

    def copiar():
        janela.clipboard_clear()
        janela.clipboard_append(details)
        btn_copiar.configure(text="✅ Copiado!")

    btn_copiar = ctk.CTkButton(
        rodape, text="📋 Copiar erro", width=120, command=copiar)
    btn_copiar.pack(side="left")

    ctk.CTkButton(rodape, text="Fechar", width=100,
                  command=janela.destroy).pack(side="right")

    janela.wait_window()
