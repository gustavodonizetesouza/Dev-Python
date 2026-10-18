"""Gráficos leves desenhados com QPainter — sem dependências externas."""
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QWidget

from core.util import fmt_moeda_compacta

COR_VERDE, COR_VERMELHA = QColor("#43a047"), QColor("#e53935")


def _cor_texto(widget) -> QColor:
    return widget.palette().color(QPalette.ColorRole.Text)


class GraficoPizza(QWidget):
    """Pizza de despesas por categoria, com legenda lateral."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.itens = []

    def set_dados(self, itens):
        self.itens = list(itens or [])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        total = sum(i["total"] for i in self.itens)
        if total <= 0:
            p.setPen(QPen(_cor_texto(self)))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Sem despesas neste mês")
            p.end()
            return

        larg_legenda = min(210, int(w * 0.45))
        lado = max(0, min(h - 24, w - larg_legenda - 40))
        cx = 12 + (w - larg_legenda - 24 - lado) / 2
        rect = QRectF(cx, (h - lado) / 2, lado, lado)

        angulo = 90 * 16
        for item in self.itens:
            fatia = int(round(item["total"] / total * 360 * 16))
            p.setPen(QPen(Qt.PenStyle.NoPen))
            p.setBrush(QColor(item["cor"] or "#607d8b"))
            p.drawPie(rect, angulo, -fatia)
            angulo -= fatia

        x_leg = w - larg_legenda - 6
        y = max(16, (h - min(len(self.itens), 9) * 22) / 2)
        p.setPen(QPen(_cor_texto(self)))
        for item in self.itens[:9]:
            p.fillRect(int(x_leg), int(y), 12, 12,
                       QColor(item["cor"] or "#607d8b"))
            pct = item["total"] / total * 100
            p.drawText(int(x_leg) + 18, int(y) + 11,
                       f"{item['nome']} ({pct:.0f}%)")
            y += 22
        p.end()


class GraficoBarras(QWidget):
    """Barras agrupadas — entradas x saídas por mês."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.serie = []

    def set_serie(self, serie):
        self.serie = list(serie or [])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if not self.serie:
            p.setPen(QPen(_cor_texto(self)))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem dados")
            p.end()
            return

        txt = _cor_texto(self)
        cor_grid = QColor(txt.red(), txt.green(), txt.blue(), 45)
        m_esq, m_dir, topo, base = 78, 14, 18, 30
        larg = max(1, w - m_esq - m_dir)
        alt = max(1, h - topo - base)
        maior = max(max(ent, sai) for _, ent, sai in self.serie) or 1.0

        for i in range(4):
            y = topo + alt * i / 3
            p.setPen(QPen(cor_grid, 1))
            p.drawLine(int(m_esq), int(y), int(m_esq + larg), int(y))
            p.setPen(QPen(txt))
            p.drawText(4, int(y) + 4, fmt_moeda_compacta(maior * (1 - i / 3)))

        n = len(self.serie)
        passo = larg / n
        larg_barra = max(8, min(26, passo * 0.26))
        for idx, (rot, ent, sai) in enumerate(self.serie):
            cx = m_esq + passo * idx + passo / 2
            for desloc, valor, cor in ((-2 - larg_barra, ent, COR_VERDE),
                                       (2, sai, COR_VERMELHA)):
                if valor <= 0:
                    continue
                altura = alt * valor / maior
                p.fillRect(int(cx + desloc), int(topo + alt - altura),
                           int(larg_barra), int(altura), cor)
            p.setPen(QPen(txt))
            p.drawText(int(m_esq + passo * idx), h - 12, int(passo), 16,
                       Qt.AlignmentFlag.AlignCenter, rot)

        lx = max(0, w - 160)
        p.fillRect(lx, 2, 10, 10, COR_VERDE)
        p.drawText(lx + 14, 11, "Entradas")
        p.fillRect(lx + 82, 2, 10, 10, COR_VERMELHA)
        p.drawText(lx + 96, 11, "Saídas")
        p.end()
