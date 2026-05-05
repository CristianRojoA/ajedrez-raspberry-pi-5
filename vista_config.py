from kivy.config import Config
Config.set('graphics', 'width', '1520')
Config.set('graphics', 'height', '960')
Config.set('graphics', 'resizable', '0')

import os
import glob
import threading
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Rectangle, Color, Line, RoundedRectangle
from kivy.core.text import Label as CoreLabel
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, FadeTransition
from kivy.uix.video import Video
from kivy.uix.stencilview import StencilView
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

from modeloraul import (inicializar_ajedrez, elegir_movimiento,
                        hacer_movimiento, estado_juego, esta_en_jaque,
                        get_last_stats, hash_tablero)
import partidas_pgn

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PARTIDAS_DIR    = r"D:\ajedrez_dya\chees\partidas"
PARTIDAS_DIR_ML = os.path.join(BASE_DIR, 'partidas', 'partidas aprendizaje')
MODELOS_DIR_ML  = os.path.join(BASE_DIR, 'modelos_ml')

SKINS = {
    'clasico':  os.path.join(BASE_DIR, 'assets', 'clasico'),
    'vocaloid': os.path.join(BASE_DIR, 'assets', 'vocaloid_backup'),
    'shield':   os.path.join(BASE_DIR, 'assets', 'shield'),
}
DEFAULT_SKIN = 'vocaloid'

BOARD_WIDTH    = 960
BOARD_HEIGHT   = 960
PANEL_WIDTH    = 560
ML_BOARD_SIZE  = 720   # tamaño del tablero en modo ML (debe ser múltiplo de 8)
CHAT_HEIGHT    = 240   # altura del panel de chat en modo ML
SQUARE_SIZE    = BOARD_WIDTH // 8
PIECE_SIZE     = int(SQUARE_SIZE * 0.85)
PIECE_OFFSET   = (SQUARE_SIZE - PIECE_SIZE) // 2

ANIM_DURATION = 0.30
MOVE_DELAY    = 0.55

LIGHT_SQUARE    = (240/255, 217/255, 181/255, 1)   # chess.com crema
DARK_SQUARE     = (181/255, 136/255,  99/255, 1)   # chess.com café
HIGHLIGHT       = (0.85, 0.82, 0.15, 0.55)         # amarillo cálido
BOARD_FRAME     = (0.20, 0.11, 0.05, 1)            # caoba oscura
BOARD_FRAME_MID = (0.40, 0.24, 0.11, 1)            # caoba media (acento)
COORD_COLOR     = (0.90, 0.74, 0.54, 1)            # dorado suave

PIECE_NAMES = {
     1: "peon_b",    2: "caballo_b",  3: "alfil_b",  4: "torre_b",  5: "reina_b",  6: "rey_b",
    -1: "peon",     -2: "caballo",   -3: "alfil",   -4: "torre",   -5: "reina",   -6: "rey",
}

PIECE_LABELS = {
     1: "Peon",    2: "Caballo",  3: "Alfil",  4: "Torre",  5: "Reina",  6: "Rey",
    -1: "Peon",   -2: "Caballo", -3: "Alfil", -4: "Torre", -5: "Reina", -6: "Rey",
}

COLS = "abcdefgh"

PIECE_WIDTH_SCALE = {
    "torre_b": 0.78,
    "torre":   0.78,
}

# ── Paleta UI moderna (navy + lavanda) ───────────────────────────────────────
UI_BG_PAGE   = (0.95, 0.95, 0.98, 1)   # fondo pantallas
UI_BG_CARD   = (0.88, 0.88, 0.95, 1)   # fondo de cards/paneles
UI_BG_ITEM   = (0.82, 0.83, 0.92, 1)   # items seleccionables en listas
UI_NAVY      = (0.08, 0.10, 0.43, 1)   # navy profundo - botones primarios
UI_NAVY_MID  = (0.16, 0.19, 0.55, 1)   # navy medio
UI_NAVY_SEL  = (0.22, 0.28, 0.68, 1)   # navy seleccionado
UI_TEXT_DARK = (0.06, 0.08, 0.35, 1)   # texto principal sobre fondo claro
UI_TEXT_SOFT = (0.28, 0.32, 0.58, 1)   # texto secundario
UI_WHITE     = (1.00, 1.00, 1.00, 1)
UI_GOLD      = (0.92, 0.82, 0.45, 1)   # dorado - acento
UI_RED       = (0.60, 0.10, 0.10, 1)   # peligro/borrar
UI_GREEN     = (0.12, 0.52, 0.22, 1)   # confirmar/entrenar

COLOR_MOVE_NORMAL   = UI_BG_ITEM
COLOR_MOVE_SELECTED = UI_NAVY_SEL
COLOR_BTN_PAUSE     = UI_NAVY
COLOR_BTN_RESUME    = UI_GREEN
COLOR_SKIN_NORMAL   = UI_NAVY_MID
COLOR_SKIN_SELECTED = UI_NAVY


class RoundedButton(Button):
    """Botón con esquinas redondeadas estilo navy."""
    def __init__(self, btn_color=None, radius=20, **kwargs):
        if btn_color is None:
            btn_color = UI_NAVY
        self._btn_color = btn_color
        self._radius = radius
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color  = (0, 0, 0, 0)
        self.color = UI_WHITE
        with self.canvas.before:
            self._clr  = Color(*self._btn_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[self._radius])
        self.bind(pos=self._upd_rect, size=self._upd_rect)

    def _upd_rect(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size

    def set_btn_color(self, color):
        self._btn_color = color
        self._clr.rgba = color


def idx_to_sq(idx):
    row, col = idx // 8, idx % 8
    return f"{COLS[col]}{row + 1}"
