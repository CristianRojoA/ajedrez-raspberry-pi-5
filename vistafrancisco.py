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
from kivy.graphics import Rectangle, Color, Line
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

COLOR_MOVE_NORMAL   = (0.15, 0.15, 0.20, 1)
COLOR_MOVE_SELECTED = (0.25, 0.38, 0.60, 1)
COLOR_BTN_PAUSE     = (0.18, 0.48, 0.78, 1)
COLOR_BTN_RESUME    = (0.18, 0.68, 0.28, 1)
COLOR_SKIN_NORMAL   = (0.20, 0.20, 0.28, 1)
COLOR_SKIN_SELECTED = (0.18, 0.48, 0.78, 1)


def idx_to_sq(idx):
    row, col = idx // 8, idx % 8
    return f"{COLS[col]}{row + 1}"


class ChatPanel(BoxLayout):
    """Panel de chat con el modelo ML — placeholder para implementación futura."""

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=[8, 6, 8, 6], spacing=4, **kwargs)

        with self.canvas.before:
            Color(0.09, 0.11, 0.15, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self.add_widget(Label(
            text="Chat — Modelo ML",
            size_hint=(1, None), height=26,
            font_size=13, bold=True,
            color=(0.92, 0.82, 0.45, 1),
        ))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._msg_grid = GridLayout(cols=1, size_hint_y=None, spacing=2, padding=[4, 2])
        self._msg_grid.bind(minimum_height=self._msg_grid.setter('height'))
        scroll.add_widget(self._msg_grid)
        self.add_widget(scroll)

        self._add_msg("[Sistema]", "Modelo ML no configurado. Próximamente.", system=True)

        input_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=36, spacing=6)
        self._input = TextInput(
            hint_text="Mensaje al modelo...",
            multiline=False,
            size_hint=(1, 1),
            font_size=12,
            background_color=(0.14, 0.14, 0.20, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.92, 0.82, 0.45, 1),
        )
        self._input.bind(on_text_validate=self._send)
        btn_send = Button(
            text="Enviar",
            size_hint=(None, 1), width=72,
            background_normal='',
            background_color=(0.18, 0.38, 0.68, 1),
            color=(1, 1, 1, 1),
            font_size=12, bold=True,
        )
        btn_send.bind(on_press=self._send)
        input_row.add_widget(self._input)
        input_row.add_widget(btn_send)
        self.add_widget(input_row)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _add_msg(self, sender, text, system=False):
        color = (0.50, 0.65, 0.72, 1) if system else (0.88, 0.92, 0.88, 1)
        lbl = Label(
            text=f"[b]{sender}[/b]  {text}",
            size_hint=(1, None),
            font_size=11, markup=True,
            color=color,
            halign='left', valign='top',
        )
        lbl.bind(width=lambda w, v: setattr(w, 'text_size', (v, None)))
        lbl.bind(texture_size=lambda w, v: setattr(w, 'height', v[1]))
        self._msg_grid.add_widget(lbl)

    def _send(self, *_):
        txt = self._input.text.strip()
        if not txt:
            return
        self._add_msg("[Tú]", txt)
        self._input.text = ''
        # TODO: conectar con el modelo ML cuando esté disponible
        self._add_msg("[ML]", "Modelo no disponible aún.", system=True)


class MovePanel(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=[10, 10, 10, 10], spacing=6, **kwargs)

        with self.canvas.before:
            Color(0.13, 0.13, 0.17, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.add_widget(Label(
            text="Movimientos",
            size_hint=(1, None), height=40,
            bold=True, font_size=18,
            color=(0.92, 0.82, 0.45, 1),
        ))

        self._status_label = Label(
            text="",
            size_hint=(1, None), height=28,
            font_size=12, bold=True,
            color=(0.95, 0.40, 0.20, 1),
        )
        self.add_widget(self._status_label)

        self._scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._move_list = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self._move_list.bind(minimum_height=self._move_list.setter('height'))
        self._scroll.add_widget(self._move_list)
        self.add_widget(self._scroll)

        self._btn = Button(
            text="Pausar",
            size_hint=(1, None), height=50,
            background_normal='',
            background_color=COLOR_BTN_PAUSE,
            color=(1, 1, 1, 1),
            font_size=15, bold=True,
        )
        self._btn.bind(on_press=self._toggle_pause)
        self.add_widget(self._btn)

        self._btn_guardar = Button(
            text="Guardar Partida",
            size_hint=(1, None), height=44,
            background_normal='',
            background_color=(0.55, 0.38, 0.08, 1),
            color=(1, 1, 1, 1),
            font_size=14, bold=True,
        )
        self._btn_guardar.bind(on_press=self._guardar_partida)
        self.add_widget(self._btn_guardar)

        self._btn_volver = Button(
            text="< Menú",
            size_hint=(1, None), height=40,
            background_normal='',
            background_color=(0.25, 0.18, 0.18, 1),
            color=(0.85, 0.70, 0.70, 1),
            font_size=13, bold=True,
        )
        self._btn_volver.bind(on_press=self._volver_menu)
        self.add_widget(self._btn_volver)

        self.board         = None
        self._move_buttons = []
        self._mode         = 'minimax'

    def set_mode(self, mode):
        self._mode = mode

    def _volver_menu(self, *_):
        if self.board:
            self.board.pause()
        App.get_running_app().root.current = 'menu'

    def _add_entry_ml(self, text, idx):
        """Entrada simplificada para modo ML: sin bloque de análisis DAA."""
        label_clean = text.replace('[', '').replace(']', '')
        btn = Button(
            text=f"  {idx + 1:>3}. {label_clean}",
            size_hint=(1, None), height=28,
            background_normal='',
            background_color=COLOR_MOVE_NORMAL,
            color=(0.72, 0.88, 1.0, 1),
            font_size=12,
            halign='left',
        )
        btn.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], v[1])))
        self._move_list.add_widget(btn)
        self._move_buttons.append(btn)

    def set_status(self, text):
        self._status_label.text = text

    def _update_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def add_entry(self, text, idx, stats):
        if self._mode == 'ml':
            self._add_entry_ml(text, idx)
            return
        b0 = stats.get('candidatos_disponibles', 0)
        b  = max(stats.get('movimientos_raiz', 1), 1)
        d  = stats.get('profundidad', 2)
        n  = stats.get('nodos', 0)
        p  = stats.get('podas', 0)
        ch = stats.get('cache_hits', 0)

        # Espacio de soluciones S(I) = b^d
        s_bruto  = b ** d
        s_optimo = max(int(b ** (d / 2)), 1)
        b_ef     = round(n ** (1 / max(d, 1)), 2) if n > 0 else 0
        ahorro   = max(0, int(100 * (1 - n / max(s_bruto, 1))))

        # Regla del pulgar (DAA S4): |S(I)| × T_verif <= 10^8
        def _zona(nodos):
            if nodos < 1_000:         return "TRIVIAL  < 10^3"
            if nodos < 10_000_000:    return "VIABLE   < 10^7"
            if nodos < 100_000_000:   return "LIMITE   < 10^8"
            return                           "EXPLOSION> 10^8"

        # Proyeccion de explosion combinatoria a mayor profundidad
        proj_lines = "\n".join(
            f"  d={dep}: {b**dep:>12,} nodos  {_zona(b**dep)}"
            for dep in [2, 3, 4, 6, 8]
        )

        label_clean = text.replace('[', '').replace(']', '')

        detalle = (
            f"Paradigma: Busqueda Exhaustiva + Poda alfa-beta\n"
            f"Estrategia complementaria: Memoizacion (DP)\n"
            f"------------------------------------------------\n"
            f"ESPACIO DE SOLUCIONES S(I) = b^d\n"
            f"  b0 candidatos reales  = {b0:>5} mov.\n"
            f"  b  candidatos usados  = {b:>5} mov. (limite)\n"
            f"  d  profundidad        = {d:>5} niveles\n"
            f"  |S(I)| sin poda O(b^d)= {s_bruto:>5,} nodos\n"
            f"  Peor caso: Omega(|S(I)|) = {s_bruto:,}\n"
            f"------------------------------------------------\n"
            f"BUSQUEDA REAL (Instrumentada)\n"
            f"  |S(I)| explorado      = {n:>5,} nodos\n"
            f"  Poda alfa-beta (BT)   = {p:>5,} ramas cortadas\n"
            f"  Memoizacion DP        = {ch:>5,} hits de cache\n"
            f"  O(b^(d/2)) optimo     = {s_optimo:>5,} nodos\n"
            f"  b efectivo            = ~{b_ef}\n"
            f"  Reduccion vs S bruto  = {ahorro:>5}%\n"
            f"------------------------------------------------\n"
            f"PROYECCION EXPLOSION COMBINATORIA (b={b})\n"
            f"Regla: |S(I)| x T_verif <= 10^8 es viable\n"
            f"{proj_lines}"
        )

        detail_height = detalle.count('\n') * 15 + 27

        if ahorro >= 60:
            bg = (0.08, 0.20, 0.10, 1)
        elif ahorro >= 30:
            bg = (0.20, 0.16, 0.06, 1)
        else:
            bg = (0.20, 0.08, 0.08, 1)

        container = BoxLayout(orientation='vertical', size_hint=(1, None), height=28)

        header = Button(
            text=f"  {idx + 1:>3}. {label_clean}",
            size_hint=(1, None), height=28,
            background_normal='',
            background_color=COLOR_MOVE_NORMAL,
            color=(0.88, 0.88, 0.88, 1),
            font_size=12,
            halign='left',
        )
        header.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], v[1])))

        detail_wrapper = BoxLayout(size_hint=(1, None), height=0, opacity=0)
        with detail_wrapper.canvas.before:
            Color(*bg)
            rect = Rectangle(pos=detail_wrapper.pos, size=detail_wrapper.size)
        detail_wrapper.bind(
            pos =lambda _, v: setattr(rect, 'pos',  v),
            size=lambda _, v: setattr(rect, 'size', v),
        )
        lbl = Label(
            text=detalle,
            size_hint=(1, 1),
            font_size=11,
            color=(0.88, 0.88, 0.88, 1),
            halign='left', valign='top',
        )
        lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        detail_wrapper.add_widget(lbl)

        def on_press(_):
            if detail_wrapper.height == 0:
                detail_wrapper.height  = detail_height
                detail_wrapper.opacity = 1
                container.height       = 28 + detail_height
            else:
                detail_wrapper.height  = 0
                detail_wrapper.opacity = 0
                container.height       = 28
            self._on_move_clicked(idx)

        header.bind(on_press=on_press)

        container.add_widget(header)
        container.add_widget(detail_wrapper)
        self._move_list.add_widget(container)
        self._move_buttons.append(header)

    def _on_move_clicked(self, idx):
        self.ensure_paused()
        for i, btn in enumerate(self._move_buttons):
            btn.background_color = COLOR_MOVE_SELECTED if i == idx else COLOR_MOVE_NORMAL
        if self.board:
            self.board.replay_move(idx)

    def ensure_paused(self):
        if self.board and not self.board._paused:
            self.board.pause()
            self._btn.text             = "Reanudar"
            self._btn.background_color = COLOR_BTN_RESUME

    def _toggle_pause(self, *_):
        if self.board is None:
            return
        if not self.board._paused:
            self.board.pause()
            self._btn.text             = "Reanudar"
            self._btn.background_color = COLOR_BTN_RESUME
        else:
            self.board.resume()
            self._btn.text             = "Pausar"
            self._btn.background_color = COLOR_BTN_PAUSE
            for btn in self._move_buttons:
                btn.background_color = COLOR_MOVE_NORMAL

    def _guardar_partida(self, *_):
        if not self.board or not self.board._history:
            self.set_status("Sin movimientos para guardar")
            return

        msg = self.board._game_over_msg
        if 'Blancas' in msg:
            resultado = '1-0'
        elif 'Negras' in msg:
            resultado = '0-1'
        elif msg:
            resultado = '1/2-1/2'
        else:
            resultado = '*'

        self.board.pause()
        self._btn.text             = "Reanudar"
        self._btn.background_color = COLOR_BTN_RESUME

        self._mostrar_dialogo_nombre(resultado)

    def _mostrar_dialogo_nombre(self, resultado):
        from datetime import datetime
        sugerido = datetime.now().strftime('%Y%m%d_%H%M%S')

        content = BoxLayout(orientation='vertical', padding=16, spacing=12)

        content.add_widget(Label(
            text="Nombre del archivo (sin extensión):",
            size_hint=(1, None), height=30,
            font_size=14, color=(0.88, 0.88, 0.92, 1),
            halign='left',
        ))

        entrada = TextInput(
            text=sugerido,
            multiline=False,
            size_hint=(1, None), height=42,
            font_size=15,
            background_color=(0.18, 0.18, 0.24, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.92, 0.82, 0.45, 1),
        )
        content.add_widget(entrada)

        self._error_lbl = Label(
            text='',
            size_hint=(1, None), height=22,
            font_size=12, color=(0.90, 0.30, 0.20, 1),
        )
        content.add_widget(self._error_lbl)

        botones = BoxLayout(orientation='horizontal', spacing=10,
                            size_hint=(1, None), height=46)

        btn_cancel = Button(
            text="Cancelar",
            background_normal='',
            background_color=(0.30, 0.30, 0.38, 1),
            color=(1, 1, 1, 1), font_size=14, bold=True,
        )
        btn_ok = Button(
            text="Guardar",
            background_normal='',
            background_color=(0.18, 0.68, 0.28, 1),
            color=(1, 1, 1, 1), font_size=14, bold=True,
        )
        botones.add_widget(btn_cancel)
        botones.add_widget(btn_ok)
        content.add_widget(botones)

        popup = Popup(
            title="Guardar partida",
            content=content,
            size_hint=(None, None), size=(480, 240),
            background_color=(0.10, 0.10, 0.15, 1),
            title_color=(0.92, 0.82, 0.45, 1),
            title_size=16,
            separator_color=(0.92, 0.82, 0.45, 1),
            auto_dismiss=False,
        )

        def _on_guardar(_):
            nombre = entrada.text.strip()
            if not nombre:
                self._error_lbl.text = "El nombre no puede estar vacío."
                return
            # Caracteres inválidos en nombres de archivo Windows
            invalidos = set(r'\/:*?"<>|')
            if any(c in invalidos for c in nombre):
                self._error_lbl.text = 'Caracteres no permitidos: \\ / : * ? " < > |'
                return
            try:
                ruta = partidas_pgn.guardar_partida(
                    self.board._history, resultado, nombre=nombre
                )
                popup.dismiss()
                self.set_status(f"Guardada: {os.path.basename(ruta)}")
                self._btn_guardar.background_color = (0.12, 0.45, 0.20, 1)
                Clock.schedule_once(
                    lambda _: setattr(self._btn_guardar, 'background_color',
                                      (0.55, 0.38, 0.08, 1)),
                    2.5,
                )
            except Exception as e:
                self._error_lbl.text = f"Error: {e}"

        btn_ok.bind(on_press=_on_guardar)
        entrada.bind(on_text_validate=_on_guardar)
        btn_cancel.bind(on_press=lambda _: popup.dismiss())

        popup.open()


class ChessBoard(Widget):

    def __init__(self, on_move=None, on_status=None, assets_dir=None, **kwargs):
        super().__init__(**kwargs)
        self._assets_dir   = assets_dir or SKINS[DEFAULT_SKIN]
        self._board_texture = None
        self.tablero       = inicializar_ajedrez()
        self.textures      = self._load_assets()
        self.turno        = 0
        self.on_move_cb   = on_move
        self.on_status_cb = on_status

        self._anim_active   = False
        self._anim_progress = 0.0
        self._anim_from     = None
        self._anim_to       = None
        self._anim_piece    = None
        self._anim_final    = None
        self._anim_event    = None

        self._paused        = False
        self._pending_event = None
        self._reviewing     = False
        self._live_saved    = False
        self._live_tablero  = None
        self._live_turno    = 0
        self._historial     = {}
        self._live_historial = {}
        self._initial_board = self.tablero[:]
        self._history       = []
        self._game_over     = False
        self._game_over_msg = ""

        self._replay_moves  = None   # list[(desde,hasta)] o None → modo normal
        self._replay_idx    = 0
        self._coord_cache   = {}
        self._motor_ml      = None   # MotorML si se juega en modo ML
        self._num_mov_ml    = 0
        self._motor_ml_turno = None  # 0=ML juega blancas, 1=negras, None=ambos

        self.bind(pos=self._draw, size=self._draw)
        self._draw()
        self._pending_event = Clock.schedule_once(self._next_move, 1.0)

    # ── Assets ───────────────────────────────────────────────────────────────

    def _load_assets(self):
        textures = {}
        for nombre in set(PIECE_NAMES.values()):
            path = os.path.join(self._assets_dir, f"{nombre}.png")
            if not os.path.isfile(path):
                continue
            try:
                textures[nombre] = CoreImage(path).texture
            except Exception:
                pass

        for fname in os.listdir(self._assets_dir):
            if fname.startswith('tablero'):
                try:
                    self._board_texture = CoreImage(
                        os.path.join(self._assets_dir, fname)).texture
                except Exception:
                    pass
                break

        return textures

    # ── Pausa / reanudación ───────────────────────────────────────────────────

    def pause(self):
        self._paused = True
        if self._pending_event:
            self._pending_event.cancel()
            self._pending_event = None
        if not self._live_saved:
            src = self._history[-1]['board_after'] if self._history else self._initial_board
            self._live_tablero   = src[:]
            self._live_turno     = self.turno
            self._live_historial = dict(self._historial)
            self._live_saved     = True

    def resume(self):
        self._paused    = False
        self._reviewing = False
        if self._live_saved and self._live_tablero is not None:
            self.tablero     = self._live_tablero[:]
            self.turno       = self._live_turno
            self._historial  = dict(self._live_historial)
            self._live_saved = False
        if not self._anim_active:
            self._pending_event = Clock.schedule_once(self._next_move, MOVE_DELAY)

    def replay_move(self, idx):
        if idx < 0 or idx >= len(self._history):
            return
        if self._anim_active and self._anim_event:
            self._anim_event.cancel()
            self._anim_active = False

        self._reviewing = True
        entry = self._history[idx]

        # Restaurar tablero al estado previo al movimiento
        self.tablero = entry['board_before'][:]
        self.tablero[entry['desde']] = 0          # pieza en vuelo: limpiar origen

        self._anim_from     = entry['desde']
        self._anim_to       = entry['hasta']
        self._anim_piece    = entry['pieza_volando']
        self._anim_final    = entry['pieza_final']
        self._anim_progress = 0.0
        self._anim_active   = True
        self.tablero[entry['hasta']] = 0           # limpiar destino durante vuelo
        self._anim_event = Clock.schedule_interval(self._tick_anim, 1 / 60)

    # ── Turno ─────────────────────────────────────────────────────────────────

    def _next_move(self, *_):
        self._pending_event = None
        if self._paused:
            return

        est = estado_juego(self.tablero, self.turno)
        if est != "NORMAL":
            ganador = "Negras" if self.turno == 0 else "Blancas"
            msg = (f"¡Jaque mate! Ganan {ganador}"
                   if est == "JAQUE_MATE" else "Tablas por ahogado")
            self._game_over     = True
            self._game_over_msg = msg
            if self.on_status_cb:
                self.on_status_cb(msg)
            self._draw()
            return

        h = hash_tablero(self.tablero)
        self._historial[h] = self._historial.get(h, 0) + 1
        if self._historial[h] >= 3:
            msg = "Tablas por repetición"
            self._game_over     = True
            self._game_over_msg = msg
            if self.on_status_cb:
                self.on_status_cb(msg)
            self._draw()
            return

        if self._replay_moves is not None:
            if self._replay_idx >= len(self._replay_moves):
                return
            move, stats = (self._replay_moves[self._replay_idx][:2],
                           self._replay_moves[self._replay_idx][2])
            self._replay_idx += 1
        elif self._motor_ml is not None and (
                self._motor_ml_turno is None or self.turno == self._motor_ml_turno):
            try:
                mov_ml, dist, valor = self._motor_ml.predecir(
                    self.tablero, self.turno, self._num_mov_ml)
                self._num_mov_ml += 1
                if mov_ml is None:
                    return
                move  = mov_ml
                conf  = round(dist.get(move, 0) * 100, 1) if dist else 0
                stats = {'tipo': 'ml', 'valor': round(valor, 3),
                         'confianza': conf}
            except Exception as e:
                print(f"Error motor ML: {e}")
                return
        else:
            move = elegir_movimiento(self.tablero, self.turno, historial=self._historial)
            stats = get_last_stats()
            if move is None:
                return

        desde, hasta  = move
        board_before  = self.tablero[:]
        pieza_volando = self.tablero[desde]

        hacer_movimiento(self.tablero, desde, hasta)
        pieza_final = self.tablero[hasta]
        board_after = self.tablero[:]

        move_idx = len(self._history)
        self._history.append({
            'board_before':  board_before,
            'board_after':   board_after,
            'desde':         desde,
            'hasta':         hasta,
            'pieza_volando': pieza_volando,
            'pieza_final':   pieza_final,
            'stats':         stats,
        })

        jaque = esta_en_jaque(self.tablero, 1 - self.turno)

        color      = "Blancas" if self.turno == 0 else "Negras"
        nombre     = PIECE_LABELS.get(pieza_volando, "?")
        sq         = idx_to_sq(hasta)
        move_label = f"[{color}] {nombre} {sq}{' +' if jaque else ''}"

        if self.on_move_cb:
            self.on_move_cb(move_label, move_idx, stats)

        if self.on_status_cb:
            self.on_status_cb("¡Jaque!" if jaque else "")

        self._start_anim(desde, hasta, pieza_volando, pieza_final)
        self.turno = 1 - self.turno

    # ── Animación ─────────────────────────────────────────────────────────────

    def _start_anim(self, desde, hasta, pieza_volando, pieza_final):
        self._anim_from     = desde
        self._anim_to       = hasta
        self._anim_piece    = pieza_volando
        self._anim_final    = pieza_final
        self._anim_progress = 0.0
        self._anim_active   = True
        self.tablero[hasta] = 0
        self._anim_event    = Clock.schedule_interval(self._tick_anim, 1 / 60)

    def _tick_anim(self, dt):
        self._anim_progress += dt / ANIM_DURATION
        if self._anim_progress >= 1.0:
            self._anim_progress = 1.0
            self._anim_active   = False
            self.tablero[self._anim_to] = self._anim_final
            self._draw()
            if not self._paused and not self._reviewing:
                self._pending_event = Clock.schedule_once(self._next_move, MOVE_DELAY)
            return False
        self._draw()

    @staticmethod
    def _ease(t):
        return t * t * (3.0 - 2.0 * t)

    # ── Dibujo ────────────────────────────────────────────────────────────────

    def _coord_tex(self, text, sz):
        """Texture de texto para coordenadas, cacheada por (texto, tamaño)."""
        key = (text, sz)
        if key not in self._coord_cache:
            lbl = CoreLabel(text=text, font_size=sz, bold=True,
                            color=COORD_COLOR)
            lbl.refresh()
            self._coord_cache[key] = lbl.texture
        return self._coord_cache[key]

    def _draw(self, *_):
        w, h   = self.width, self.height
        frame  = max(20, min(w, h) // 36)   # grosor del marco proporcional
        sq     = max(1, (min(w, h) - 2 * frame) // 8)
        ps     = int(sq * 0.85)
        poff   = (sq - ps) // 2
        bx, by = self.pos

        # Origen del tablero centrado dentro del widget
        board_px = sq * 8
        ox = bx + (w - board_px) // 2
        oy = by + (h - board_px) // 2

        self.canvas.clear()
        with self.canvas:

            # ── Fondo del widget ─────────────────────────────────────────
            Color(0.10, 0.07, 0.04, 1)
            Rectangle(pos=self.pos, size=self.size)

            # ── Marco exterior de madera oscura ──────────────────────────
            Color(*BOARD_FRAME)
            Rectangle(pos=(ox - frame, oy - frame),
                      size=(board_px + 2 * frame, board_px + 2 * frame))

            # ── Borde interior dorado ────────────────────────────────────
            Color(*BOARD_FRAME_MID)
            Line(rectangle=(ox - frame + 3, oy - frame + 3,
                             board_px + 2 * frame - 6,
                             board_px + 2 * frame - 6),
                 width=1.5)

            # ── Sombra interior del tablero ──────────────────────────────
            Color(0.08, 0.04, 0.02, 1)
            Line(rectangle=(ox - 2, oy - 2, board_px + 4, board_px + 4),
                 width=2)

            # ── Textura de tablero (skin) ────────────────────────────────
            if self._board_texture:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._board_texture,
                          pos=(ox, oy), size=(board_px, board_px))

            # ── Casillas ─────────────────────────────────────────────────
            sq_alpha = 0.28 if self._board_texture else 1.0
            for i in range(64):
                row, col = i // 8, i % 8
                r, g, b, _ = LIGHT_SQUARE if (row + col) % 2 == 1 else DARK_SQUARE
                Color(r, g, b, sq_alpha)
                Rectangle(pos=(ox + col * sq, oy + row * sq), size=(sq, sq))

            # ── Resaltado último movimiento ──────────────────────────────
            if self._anim_from is not None:
                for idx in (self._anim_from, self._anim_to):
                    r, c = idx // 8, idx % 8
                    Color(*HIGHLIGHT)
                    Rectangle(pos=(ox + c * sq, oy + r * sq), size=(sq, sq))

            # ── Etiquetas de coordenadas ─────────────────────────────────
            font_sz = max(9, sq // 6)
            pad     = max(3, frame // 4)
            for i in range(8):
                # Letras de columna — parte inferior del marco
                tex = self._coord_tex(COLS[i], font_sz)
                tw, th = tex.width, tex.height
                Color(*COORD_COLOR)
                Rectangle(texture=tex,
                          pos=(ox + i * sq + (sq - tw) // 2,
                               oy - frame + pad),
                          size=(tw, th))
                # Números de fila — parte izquierda del marco
                tex2 = self._coord_tex(str(i + 1), font_sz)
                tw2, th2 = tex2.width, tex2.height
                Rectangle(texture=tex2,
                          pos=(ox - frame + pad,
                               oy + i * sq + (sq - th2) // 2),
                          size=(tw2, th2))

            # ── Piezas estáticas ─────────────────────────────────────────
            for i in range(64):
                nombre = PIECE_NAMES.get(self.tablero[i])
                if nombre and nombre in self.textures:
                    row, col = i // 8, i % 8
                    pw  = int(ps * PIECE_WIDTH_SCALE.get(nombre, 1.0))
                    px  = ox + col * sq + (sq - pw) // 2
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(px, oy + row * sq + poff),
                              size=(pw, ps))

            # ── Pieza animada ─────────────────────────────────────────────
            if self._anim_active:
                fr2, fc2 = self._anim_from // 8, self._anim_from % 8
                tr2, tc2 = self._anim_to   // 8, self._anim_to   % 8
                t        = self._ease(self._anim_progress)
                nombre   = PIECE_NAMES.get(self._anim_piece)
                if nombre and nombre in self.textures:
                    pw    = int(ps * PIECE_WIDTH_SCALE.get(nombre, 1.0))
                    x_off = (sq - pw) // 2
                    ax    = ox + (fc2 + (tc2 - fc2) * t) * sq + x_off
                    ay    = oy + (fr2 + (tr2 - fr2) * t) * sq + poff
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(ax, ay), size=(pw, ps))

            # ── Overlay fin de partida ────────────────────────────────────
            if self._game_over:
                Color(0, 0, 0, 0.52)
                Rectangle(pos=(ox, oy), size=(board_px, board_px))


class ModeScreen(Screen):
    """Primera pantalla: el jugador elige entre Minimax y Machine Learning."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.06, 0.06, 0.10, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical', padding=[180, 60, 180, 60], spacing=20)

        root.add_widget(Label(
            text="Ajedrez",
            font_size=82, bold=True,
            color=(0.92, 0.82, 0.45, 1),
            size_hint=(1, None), height=130,
        ))

        root.add_widget(Label(
            text="Selecciona el tipo de análisis",
            font_size=20,
            color=(0.65, 0.65, 0.80, 1),
            size_hint=(1, None), height=36,
        ))

        root.add_widget(Widget(size_hint=(1, 0.6)))

        btn_minimax = Button(
            text="Análisis Minimax",
            size_hint=(0.60, None), height=88,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.18, 0.48, 0.78, 1),
            color=(1, 1, 1, 1),
            font_size=26, bold=True,
        )
        btn_minimax.bind(on_press=lambda _: self._elegir('minimax'))
        root.add_widget(btn_minimax)

        root.add_widget(Label(
            text="Búsqueda exhaustiva · Poda alfa-beta · Memoización DP",
            font_size=12,
            color=(0.45, 0.60, 0.78, 1),
            size_hint=(1, None), height=22,
        ))

        root.add_widget(Widget(size_hint=(1, None), height=28))

        btn_ml = Button(
            text="Análisis Machine Learning",
            size_hint=(0.60, None), height=88,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.38, 0.15, 0.58, 1),
            color=(1, 1, 1, 1),
            font_size=26, bold=True,
        )
        btn_ml.bind(on_press=lambda _: self._elegir('ml'))
        root.add_widget(btn_ml)

        root.add_widget(Label(
            text="Modelo de aprendizaje profundo — en desarrollo",
            font_size=12,
            color=(0.60, 0.42, 0.78, 1),
            size_hint=(1, None), height=22,
        ))

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _elegir(self, mode):
        App.get_running_app().game_mode = mode
        self.manager.current = 'ml_menu' if mode == 'ml' else 'menu'


class MLScreen(Screen):
    """Hub de opciones para el modo Machine Learning."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.06, 0.06, 0.10, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical',
                         padding=[180, 60, 180, 60], spacing=20)

        back_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44)
        btn_back = Button(
            text="< Tipo de análisis", size_hint=(None, 1), width=210,
            background_normal='', background_color=(0.22, 0.22, 0.30, 1),
            color=(0.80, 0.80, 0.92, 1), font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'mode'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Widget(size_hint=(1, 1)))
        root.add_widget(back_row)

        root.add_widget(Label(
            text="Machine Learning",
            font_size=70, bold=True, color=(0.92, 0.82, 0.45, 1),
            size_hint=(1, None), height=120,
        ))
        root.add_widget(Label(
            text="Entrena y prueba el motor de IA con tus propias partidas",
            font_size=17, color=(0.65, 0.65, 0.80, 1),
            size_hint=(1, None), height=30,
        ))
        root.add_widget(Widget(size_hint=(1, 0.5)))

        btn_entrenar = Button(
            text="Entrenar Modelo",
            size_hint=(0.55, None), height=88,
            pos_hint={'center_x': 0.5},
            background_normal='', background_color=(0.52, 0.15, 0.72, 1),
            color=(1, 1, 1, 1), font_size=26, bold=True,
        )
        btn_entrenar.bind(
            on_press=lambda _: setattr(self.manager, 'current', 'entrenar'))
        root.add_widget(btn_entrenar)
        root.add_widget(Label(
            text="Selecciona archivos PGN y entrena la red neuronal",
            font_size=12, color=(0.62, 0.45, 0.80, 1),
            size_hint=(1, None), height=22,
        ))

        root.add_widget(Widget(size_hint=(1, None), height=30))

        btn_probar = Button(
            text="Probar Modelo",
            size_hint=(0.55, None), height=88,
            pos_hint={'center_x': 0.5},
            background_normal='', background_color=(0.18, 0.48, 0.78, 1),
            color=(1, 1, 1, 1), font_size=26, bold=True,
        )
        btn_probar.bind(
            on_press=lambda _: setattr(self.manager, 'current', 'probar'))
        root.add_widget(btn_probar)
        root.add_widget(Label(
            text="Elige un modelo entrenado y observa cómo juega",
            font_size=12, color=(0.40, 0.60, 0.80, 1),
            size_hint=(1, None), height=22,
        ))

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size


class EntrenarScreen(Screen):
    """Selecciona PGNs, entrena el modelo y guárdalo con nombre personalizado."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pgn_btns    = {}    # {ruta: Button}
        self._pgn_selec   = set() # rutas actualmente seleccionadas
        self._motor       = None  # MotorML después de entrenar
        self._entrenando  = False
        self._base_modelo = None  # ruta del modelo a continuar (o None = nuevo)

        with self.canvas.before:
            Color(0.06, 0.07, 0.10, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg, on_enter=self._on_enter)

        # Outer: fondo completo con back+titulo
        outer = BoxLayout(orientation='vertical',
                          padding=[40, 20, 40, 12], spacing=8)

        # Back + título (ancho completo)
        back_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44)
        btn_back = Button(
            text="< ML", size_hint=(None, 1), width=90,
            background_normal='', background_color=(0.22, 0.22, 0.30, 1),
            color=(0.80, 0.80, 0.92, 1), font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'ml_menu'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Label(
            text="Entrenar Modelo",
            font_size=22, bold=True, color=(0.92, 0.82, 0.45, 1),
            halign='center',
        ))
        back_row.add_widget(Widget(size_hint=(None, 1), width=90))
        outer.add_widget(back_row)

        # Contenedor central de ancho fijo (900 px centrado)
        root = BoxLayout(orientation='vertical',
                         size_hint=(None, 1), width=900,
                         pos_hint={'center_x': 0.5}, spacing=10)

        # ── Continuar desde modelo existente ─────────────────────────────────
        root.add_widget(Label(
            text="Continuar entrenando desde modelo existente (opcional):",
            font_size=12, color=(0.70, 0.70, 0.85, 1),
            size_hint=(1, None), height=22,
            halign='left', valign='middle',
        ))
        base_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=40, spacing=8)
        self._lbl_base = Label(
            text="Nuevo modelo desde cero",
            font_size=12, color=(0.55, 0.80, 0.55, 1),
            size_hint=(1, 1), halign='left', valign='middle',
        )
        self._lbl_base.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], None)))
        btn_elegir_base = Button(
            text="Elegir modelo base",
            size_hint=(None, 1), width=180,
            background_normal='', background_color=(0.28, 0.28, 0.48, 1),
            color=(0.85, 0.85, 1.0, 1), font_size=13, bold=True,
        )
        btn_elegir_base.bind(on_press=self._popup_elegir_base)
        btn_limpiar_base = Button(
            text="Limpiar",
            size_hint=(None, 1), width=80,
            background_normal='', background_color=(0.45, 0.14, 0.14, 1),
            color=(1, 0.75, 0.75, 1), font_size=12,
        )
        btn_limpiar_base.bind(on_press=self._limpiar_base)
        base_row.add_widget(self._lbl_base)
        base_row.add_widget(btn_elegir_base)
        base_row.add_widget(btn_limpiar_base)
        root.add_widget(base_row)

        # Label PGNs
        root.add_widget(Label(
            text="Archivos PGN disponibles — selecciona con cuáles entrenar:",
            font_size=13, color=(0.70, 0.70, 0.85, 1),
            size_hint=(1, None), height=26,
            halign='left', valign='middle',
        ))

        # ScrollView PGNs
        pgn_scroll = ScrollView(size_hint=(1, None), height=160,
                                do_scroll_x=False, bar_width=6)
        self._pgn_grid = GridLayout(cols=1, size_hint_y=None,
                                    spacing=4, padding=[4, 4])
        self._pgn_grid.bind(minimum_height=self._pgn_grid.setter('height'))
        pgn_scroll.add_widget(self._pgn_grid)
        root.add_widget(pgn_scroll)

        # Botones sel/desel
        sel_row = BoxLayout(orientation='horizontal',
                            size_hint=(1, None), height=38, spacing=8)
        btn_all  = Button(
            text="Seleccionar todo",
            background_normal='', background_color=(0.18, 0.28, 0.18, 1),
            color=(0.80, 1.0, 0.80, 1), font_size=13,
        )
        btn_none = Button(
            text="Deseleccionar todo",
            background_normal='', background_color=(0.28, 0.14, 0.14, 1),
            color=(1.0, 0.80, 0.80, 1), font_size=13,
        )
        btn_all.bind(on_press=lambda _: self._seleccionar(True))
        btn_none.bind(on_press=lambda _: self._seleccionar(False))
        sel_row.add_widget(btn_all)
        sel_row.add_widget(btn_none)
        root.add_widget(sel_row)

        # Botón entrenar
        self._btn_entrenar = Button(
            text="Iniciar Entrenamiento",
            size_hint=(1, None), height=58,
            background_normal='', background_color=(0.18, 0.68, 0.28, 1),
            color=(1, 1, 1, 1), font_size=20, bold=True,
        )
        self._btn_entrenar.bind(on_press=self._iniciar_entrenamiento)
        root.add_widget(self._btn_entrenar)

        outer.add_widget(root)

        # Log de progreso
        root.add_widget(Label(
            text="Progreso:", font_size=12, color=(0.60, 0.60, 0.75, 1),
            size_hint=(1, None), height=20,
            halign='left', valign='middle',
        ))
        self._log_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False,
                                      bar_width=6)
        self._log_grid   = GridLayout(cols=1, size_hint_y=None,
                                      spacing=2, padding=[4, 4])
        self._log_grid.bind(minimum_height=self._log_grid.setter('height'))
        self._log_scroll.add_widget(self._log_grid)
        root.add_widget(self._log_scroll)

        # Sección guardar (oculta hasta completar entrenamiento)
        self._guardar_box = BoxLayout(orientation='vertical',
                                      size_hint=(1, None), height=0,
                                      spacing=6, opacity=0)
        root.add_widget(self._guardar_box)
        self.add_widget(outer)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _on_enter(self, *_):
        self._refrescar_pgns()

    def _refrescar_pgns(self):
        self._pgn_grid.clear_widgets()
        self._pgn_btns.clear()
        self._pgn_selec.clear()
        rutas = sorted(glob.glob(os.path.join(PARTIDAS_DIR_ML, '*.pgn')))
        if not rutas:
            self._pgn_grid.add_widget(Label(
                text="No hay archivos .pgn en la carpeta de aprendizaje.",
                font_size=12, color=(0.70, 0.50, 0.50, 1),
                size_hint=(1, None), height=32,
            ))
            return
        for ruta in rutas:
            nombre = os.path.basename(ruta)
            btn = Button(
                text=f"  {nombre}",
                size_hint=(1, None), height=36,
                background_normal='',
                background_color=(0.16, 0.24, 0.20, 1),
                color=(0.85, 0.95, 0.85, 1),
                font_size=12, halign='left', valign='middle',
            )
            btn.bind(on_press=lambda b, r=ruta: self._toggle_pgn(r))
            self._pgn_btns[ruta] = btn
            self._pgn_grid.add_widget(btn)

    def _toggle_pgn(self, ruta):
        if ruta in self._pgn_selec:
            self._pgn_selec.discard(ruta)
            self._pgn_btns[ruta].background_color = (0.16, 0.24, 0.20, 1)
        else:
            self._pgn_selec.add(ruta)
            self._pgn_btns[ruta].background_color = (0.20, 0.58, 0.28, 1)

    def _seleccionar(self, estado):
        self._pgn_selec.clear()
        for ruta, btn in self._pgn_btns.items():
            if estado:
                self._pgn_selec.add(ruta)
                btn.background_color = (0.20, 0.58, 0.28, 1)
            else:
                btn.background_color = (0.16, 0.24, 0.20, 1)

    def _popup_elegir_base(self, *_):
        rutas = sorted(glob.glob(os.path.join(MODELOS_DIR_ML, '*.keras')))
        content = BoxLayout(orientation='vertical', spacing=8, padding=12)
        if not rutas:
            content.add_widget(Label(text="No hay modelos guardados todavía.",
                                     color=(1, 0.6, 0.6, 1)))
        else:
            scroll = ScrollView(size_hint=(1, 1))
            grid   = GridLayout(cols=1, size_hint_y=None, spacing=4)
            grid.bind(minimum_height=grid.setter('height'))
            popup_ref = [None]
            for ruta in rutas:
                nombre = os.path.splitext(os.path.basename(ruta))[0]
                b = Button(
                    text=f"  {nombre}",
                    size_hint=(1, None), height=44,
                    background_normal='', background_color=(0.16, 0.24, 0.40, 1),
                    color=(0.85, 0.90, 1.0, 1), font_size=13,
                    halign='left', valign='middle',
                )
                b.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
                def _elegir(_, r=ruta, n=nombre):
                    self._base_modelo = r
                    self._lbl_base.text = f"Base: {n}"
                    self._lbl_base.color = (0.90, 0.75, 0.30, 1)
                    if popup_ref[0]:
                        popup_ref[0].dismiss()
                b.bind(on_press=_elegir)
                grid.add_widget(b)
            scroll.add_widget(grid)
            content.add_widget(scroll)

        btn_cancel = Button(
            text="Cancelar", size_hint=(1, None), height=40,
            background_normal='', background_color=(0.30, 0.18, 0.18, 1),
            color=(1, 0.8, 0.8, 1), font_size=13,
        )
        content.add_widget(btn_cancel)
        popup = Popup(title="Elegir modelo base", content=content,
                      size_hint=(0.75, 0.65))
        popup_ref[0] = popup
        btn_cancel.bind(on_press=popup.dismiss)
        popup.open()

    def _limpiar_base(self, *_):
        self._base_modelo = None
        self._lbl_base.text  = "Nuevo modelo desde cero"
        self._lbl_base.color = (0.55, 0.80, 0.55, 1)

    def _iniciar_entrenamiento(self, *_):
        if self._entrenando:
            return
        seleccionados = list(self._pgn_selec)
        if not seleccionados:
            self._agregar_log("Selecciona al menos un archivo PGN.")
            return

        self._entrenando            = True
        self._btn_entrenar.disabled = True
        self._log_grid.clear_widgets()
        self._guardar_box.height  = 0
        self._guardar_box.opacity = 0
        self._guardar_box.clear_widgets()
        self._agregar_log(f"Archivos seleccionados: {len(seleccionados)}")
        base = self._base_modelo
        if base:
            self._agregar_log(f"Continuando desde: {os.path.basename(base)}")
        self._agregar_log("Cargando TensorFlow... (puede tardar ~30 s la 1a vez)")

        def _train():
            try:
                import tensor_aprendizaje

                Clock.schedule_once(lambda dt: self._agregar_log(
                    "TensorFlow listo. Procesando partidas..."), 0)

                motor = tensor_aprendizaje.MotorML()
                if base:
                    motor.cargar_modelo(base)

                def cb_carga(nombre, total, proc):
                    Clock.schedule_once(lambda dt: self._agregar_log(
                        f"  [{proc}/{total}] {nombre}"), 0)

                def cb_epoch(epoch, total, loss):
                    Clock.schedule_once(lambda dt: self._agregar_log(
                        f"  Epoch {epoch:3d}/{total}   val_loss = {loss:.4f}"), 0)

                history = motor.entrenar(archivos=seleccionados,
                                         callback_carga=cb_carga,
                                         callback_progreso=cb_epoch)
                if history is not None:
                    self._motor = motor
                    Clock.schedule_once(lambda dt: self._agregar_log(
                        "Entrenamiento completado."), 0)
                    Clock.schedule_once(lambda dt: self._mostrar_guardar(), 0)
                else:
                    Clock.schedule_once(lambda dt: self._agregar_log(
                        "No hay posiciones suficientes para entrenar."), 0)

            except Exception as e:
                import traceback
                err_msg = str(e)
                Clock.schedule_once(lambda dt: self._agregar_log(
                    f"ERROR: {err_msg}"), 0)
                print(traceback.format_exc())
            finally:
                Clock.schedule_once(
                    lambda dt: setattr(self._btn_entrenar, 'disabled', False), 0)
                self._entrenando = False

        threading.Thread(target=_train, daemon=True).start()

    def _agregar_log(self, texto):
        lbl = Label(
            text=texto,
            size_hint=(1, None), height=22,
            font_size=11, color=(0.78, 0.90, 0.78, 1),
            halign='left', valign='middle',
        )
        lbl.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], None)))
        self._log_grid.add_widget(lbl)
        self._log_scroll.scroll_y = 0

    def _mostrar_guardar(self):
        box = self._guardar_box
        box.clear_widgets()
        box.height  = 110
        box.opacity = 1

        box.add_widget(Label(
            text="── Guardar modelo ──",
            size_hint=(1, None), height=26,
            font_size=13, bold=True, color=(0.92, 0.82, 0.45, 1),
        ))
        fila = BoxLayout(orientation='horizontal',
                         size_hint=(1, None), height=44, spacing=8)
        ti = TextInput(
            hint_text="Nombre del modelo...",
            size_hint=(1, 1),
            background_color=(0.14, 0.16, 0.22, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            font_size=15, multiline=False,
        )
        btn_save = Button(
            text="Guardar",
            size_hint=(None, 1), width=120,
            background_normal='', background_color=(0.18, 0.48, 0.78, 1),
            color=(1, 1, 1, 1), font_size=15, bold=True,
        )
        btn_save.bind(on_press=lambda _: self._guardar(ti.text))
        fila.add_widget(ti)
        fila.add_widget(btn_save)
        box.add_widget(fila)

    def _guardar(self, nombre):
        if not nombre.strip():
            self._agregar_log("Escribe un nombre antes de guardar.")
            return
        try:
            ruta = self._motor.guardar_con_nombre(nombre.strip())
            self._agregar_log(f"Guardado: {os.path.basename(ruta)}")
        except Exception as e:
            self._agregar_log(f"Error al guardar: {e}")


class ProbarModeloScreen(Screen):
    """Selecciona un modelo entrenado y lanza una partida para probarlo."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sel_ruta = None
        self._mod_btns = {}

        with self.canvas.before:
            Color(0.06, 0.07, 0.10, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg, on_enter=self._on_enter)

        # Outer: fondo completo con back+titulo
        outer = BoxLayout(orientation='vertical',
                          padding=[40, 20, 40, 20], spacing=12)

        # Back + título (ancho completo)
        back_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44)
        btn_back = Button(
            text="< ML", size_hint=(None, 1), width=90,
            background_normal='', background_color=(0.22, 0.22, 0.30, 1),
            color=(0.80, 0.80, 0.92, 1), font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'ml_menu'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Label(
            text="Probar Modelo",
            font_size=22, bold=True, color=(0.92, 0.82, 0.45, 1),
            halign='center',
        ))
        back_row.add_widget(Widget(size_hint=(None, 1), width=90))
        outer.add_widget(back_row)

        # Contenedor central de ancho fijo (800 px centrado)
        root = BoxLayout(orientation='vertical',
                         size_hint=(None, 1), width=800,
                         pos_hint={'center_x': 0.5}, spacing=14)

        root.add_widget(Label(
            text="Selecciona el modelo y el color que jugará contra el minimax:",
            font_size=13, color=(0.70, 0.70, 0.85, 1),
            size_hint=(1, None), height=28,
            halign='center',
        ))

        # Lista de modelos
        mod_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False,
                                bar_width=6)
        self._mod_grid = GridLayout(cols=1, size_hint_y=None,
                                    spacing=6, padding=[4, 4])
        self._mod_grid.bind(minimum_height=self._mod_grid.setter('height'))
        mod_scroll.add_widget(self._mod_grid)
        root.add_widget(mod_scroll)

        # Selector de color
        self._ml_turno = 0  # 0=blancas, 1=negras
        color_row = BoxLayout(orientation='horizontal',
                              size_hint=(1, None), height=44, spacing=6)
        color_row.add_widget(Label(
            text="ML juega con:",
            font_size=13, color=(0.75, 0.75, 0.90, 1),
            size_hint=(None, 1), width=140,
            halign='right', valign='middle',
        ))
        self._btn_blancas = Button(
            text="Blancas",
            size_hint=(1, 1),
            background_normal='', background_color=(0.25, 0.50, 0.25, 1),
            color=(1, 1, 1, 1), font_size=14, bold=True,
        )
        self._btn_negras = Button(
            text="Negras",
            size_hint=(1, 1),
            background_normal='', background_color=(0.18, 0.18, 0.26, 1),
            color=(0.75, 0.75, 0.90, 1), font_size=14,
        )
        self._btn_blancas.bind(on_press=lambda _: self._set_color(0))
        self._btn_negras.bind(on_press=lambda _: self._set_color(1))
        color_row.add_widget(self._btn_blancas)
        color_row.add_widget(self._btn_negras)
        root.add_widget(color_row)

        self._btn_probar = Button(
            text="Iniciar batalla  ML vs Minimax",
            size_hint=(1, None), height=64,
            background_normal='', background_color=(0.18, 0.48, 0.78, 1),
            color=(1, 1, 1, 1), font_size=20, bold=True,
            disabled=True,
        )
        self._btn_probar.bind(on_press=self._probar)
        root.add_widget(self._btn_probar)
        outer.add_widget(root)
        self.add_widget(outer)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _on_enter(self, *_):
        self._refrescar_modelos()

    def _refrescar_modelos(self):
        self._mod_grid.clear_widgets()
        self._mod_btns.clear()
        self._sel_ruta = None
        self._btn_probar.disabled = True

        rutas = sorted(glob.glob(os.path.join(MODELOS_DIR_ML, '*.keras')))
        if not rutas:
            self._mod_grid.add_widget(Label(
                text="No hay modelos entrenados todavía.\nEntrena uno primero.",
                font_size=13, color=(0.70, 0.50, 0.50, 1),
                size_hint=(1, None), height=64,
                halign='center',
            ))
            return
        for ruta in rutas:
            nombre = os.path.splitext(os.path.basename(ruta))[0]
            fila = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=48, spacing=4)
            btn = Button(
                text=f"  {nombre}",
                size_hint=(1, 1),
                background_normal='', background_color=(0.16, 0.20, 0.34, 1),
                color=(0.80, 0.85, 1.0, 1),
                font_size=14, halign='left', valign='middle',
            )
            btn.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
            btn.bind(on_press=lambda b, r=ruta: self._seleccionar(r))
            self._mod_btns[ruta] = btn
            btn_del = Button(
                text="Borrar",
                size_hint=(None, 1), width=80,
                background_normal='', background_color=(0.55, 0.12, 0.12, 1),
                color=(1, 0.82, 0.82, 1), font_size=13, bold=True,
            )
            btn_del.bind(on_press=lambda _, r=ruta: self._confirmar_borrar(r))
            fila.add_widget(btn)
            fila.add_widget(btn_del)
            self._mod_grid.add_widget(fila)

    def _seleccionar(self, ruta):
        for b in self._mod_btns.values():
            b.background_color = (0.16, 0.20, 0.34, 1)
        if ruta in self._mod_btns:
            self._mod_btns[ruta].background_color = (0.16, 0.52, 0.26, 1)
        self._sel_ruta = ruta
        self._btn_probar.disabled = False

    def _confirmar_borrar(self, ruta):
        nombre = os.path.splitext(os.path.basename(ruta))[0]
        content = BoxLayout(orientation='vertical', spacing=12, padding=16)
        content.add_widget(Label(
            text=f"¿Borrar el modelo\n[b]{nombre}[/b]?",
            markup=True, font_size=14, color=(1, 0.85, 0.85, 1),
            halign='center',
        ))
        botones = BoxLayout(orientation='horizontal',
                            size_hint=(1, None), height=48, spacing=12)
        btn_si  = Button(
            text="Sí, borrar",
            background_normal='', background_color=(0.65, 0.15, 0.15, 1),
            color=(1, 1, 1, 1), font_size=14, bold=True,
        )
        btn_no  = Button(
            text="Cancelar",
            background_normal='', background_color=(0.22, 0.22, 0.32, 1),
            color=(0.85, 0.85, 1.0, 1), font_size=14,
        )
        botones.add_widget(btn_si)
        botones.add_widget(btn_no)
        content.add_widget(botones)
        popup = Popup(title="Confirmar borrado", content=content,
                      size_hint=(0.65, 0.38))
        def _borrar(_):
            try:
                os.remove(ruta)
                meta = ruta.replace('.keras', '_meta.json')
                if os.path.exists(meta):
                    os.remove(meta)
            except Exception as e:
                print(f"Error al borrar: {e}")
            popup.dismiss()
            self._refrescar_modelos()
        btn_si.bind(on_press=_borrar)
        btn_no.bind(on_press=popup.dismiss)
        popup.open()

    def _set_color(self, turno):
        self._ml_turno = turno
        if turno == 0:
            self._btn_blancas.background_color = (0.25, 0.50, 0.25, 1)
            self._btn_blancas.bold = True
            self._btn_negras.background_color  = (0.18, 0.18, 0.26, 1)
            self._btn_negras.bold = False
        else:
            self._btn_negras.background_color  = (0.20, 0.20, 0.55, 1)
            self._btn_negras.bold = True
            self._btn_blancas.background_color = (0.18, 0.18, 0.26, 1)
            self._btn_blancas.bold = False

    def _probar(self, *_):
        if not self._sel_ruta:
            return
        app = App.get_running_app()
        app.ml_model_path = self._sel_ruta
        app.ml_turno      = self._ml_turno
        app.game_mode     = 'ml'
        assets_dir = SKINS[DEFAULT_SKIN]
        game = self.manager.get_screen('game')
        game.setup(assets_dir, 'ml')
        self.manager.current = 'game'


class MenuScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected  = DEFAULT_SKIN
        self._skin_btns = {}

        with self.canvas.before:
            Color(0.08, 0.08, 0.12, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical', padding=[200, 60, 200, 60], spacing=24)

        # Fila superior: botón volver al modo
        back_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=44)
        btn_back = Button(
            text="< Tipo de análisis",
            size_hint=(None, 1), width=200,
            background_normal='',
            background_color=(0.22, 0.22, 0.30, 1),
            color=(0.80, 0.80, 0.92, 1),
            font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'mode'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Widget(size_hint=(1, 1)))
        root.add_widget(back_row)

        root.add_widget(Label(
            text="Ajedrez",
            font_size=80, bold=True,
            color=(0.92, 0.82, 0.45, 1),
            size_hint=(1, None), height=130,
        ))

        root.add_widget(Widget(size_hint=(1, 0.15)))

        root.add_widget(Label(
            text="Skins",
            font_size=22, bold=True,
            color=(0.65, 0.65, 0.78, 1),
            size_hint=(1, None), height=36,
        ))

        skins_row = BoxLayout(orientation='horizontal', spacing=16,
                              size_hint=(1, None), height=64)
        for key, label in [('clasico', 'Clásico'), ('vocaloid', 'Vocaloid'), ('shield', 'Shield')]:
            btn = Button(
                text=label,
                background_normal='',
                background_color=COLOR_SKIN_SELECTED if key == self._selected else COLOR_SKIN_NORMAL,
                color=(1, 1, 1, 1),
                font_size=17, bold=True,
            )
            btn.bind(on_press=lambda _, k=key: self._select_skin(k))
            self._skin_btns[key] = btn
            skins_row.add_widget(btn)
        root.add_widget(skins_row)

        root.add_widget(Widget(size_hint=(1, 1)))

        start = Button(
            text="Iniciar Partida",
            size_hint=(0.45, None), height=72,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.18, 0.68, 0.28, 1),
            color=(1, 1, 1, 1),
            font_size=24, bold=True,
        )
        start.bind(on_press=self._start_game)
        root.add_widget(start)

        root.add_widget(Widget(size_hint=(1, None), height=16))

        partidas = Button(
            text="Partidas Guardadas",
            size_hint=(0.45, None), height=56,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.18, 0.38, 0.68, 1),
            color=(1, 1, 1, 1),
            font_size=20, bold=True,
        )
        partidas.bind(on_press=self._open_partidas)
        root.add_widget(partidas)

        root.add_widget(Widget(size_hint=(1, 0.08)))

        self.add_widget(root)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _select_skin(self, key):
        self._selected = key
        for k, btn in self._skin_btns.items():
            btn.background_color = COLOR_SKIN_SELECTED if k == key else COLOR_SKIN_NORMAL

    def _start_game(self, *_):
        assets_dir = SKINS[self._selected]
        mode       = App.get_running_app().game_mode
        game       = self.manager.get_screen('game')
        game.setup(assets_dir, mode)

        video_path = os.path.join(assets_dir, 'world_is_mine_bw.mp4')
        if self._selected == 'vocaloid' and os.path.isfile(video_path):
            game.pause_board()
            self.manager.get_screen('video').play(video_path)
            self.manager.current = 'video'
        else:
            self.manager.current = 'game'

    def _open_partidas(self, *_):
        self.manager.get_screen('partidas').cargar_lista()
        self.manager.current = 'partidas'


CROP_PX = 18  # píxeles recortados por cada borde del video

class VideoScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._assets_dir   = None
        self._transitioning = False
        self._video        = None

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def play(self, video_path):
        self._transitioning = False
        self.clear_widgets()

        # StencilView = ventana de recorte del tamaño del tablero
        clip = StencilView(
            size=(BOARD_WIDTH, BOARD_HEIGHT),
            size_hint=(None, None),
            pos=(0, 0),
        )

        # Video ligeramente mayor → los bordes quedan fuera del clip
        self._video = Video(
            source=video_path,
            state='play',
            allow_stretch=True,
            keep_ratio=False,
            size=(BOARD_WIDTH + CROP_PX * 2, BOARD_HEIGHT + CROP_PX * 2),
            size_hint=(None, None),
            pos=(-CROP_PX, -CROP_PX),
        )
        self._video.bind(eos=lambda *_: self._ir_al_juego())
        clip.add_widget(self._video)
        self.add_widget(clip)

    def on_touch_down(self, touch):
        self._ir_al_juego()
        return True

    def _ir_al_juego(self):
        if self._transitioning:
            return
        self._transitioning = True
        if self._video:
            self._video.state = 'stop'
        self.manager.transition = FadeTransition(duration=0.35)
        self.manager.current = 'game'
        Clock.schedule_once(lambda _: (
            self.manager.get_screen('game').resume_board(),
            setattr(self.manager, 'transition', NoTransition()),
        ), 0.4)


class PartidasScreen(Screen):
    """Pantalla de selección de partidas PGN guardadas.
    La lista se pobla desde PARTIDAS_DIR; la lógica de BD
    se conectará en un módulo separado (partidas_db.py)."""

    COLOR_ITEM_BG  = (0.14, 0.16, 0.22, 1)
    COLOR_ITEM_SEL = (0.18, 0.38, 0.68, 1)
    COLOR_VOLVER   = (0.22, 0.22, 0.30, 1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_skin = DEFAULT_SKIN
        self._skin_btns_p   = {}

        with self.canvas.before:
            Color(0.08, 0.08, 0.12, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical', padding=[60, 30, 60, 30], spacing=14)

        # ── Cabecera ──────────────────────────────────────────────────────────
        header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=56)
        btn_volver = Button(
            text="< Volver",
            size_hint=(None, 1), width=140,
            background_normal='',
            background_color=self.COLOR_VOLVER,
            color=(0.85, 0.85, 0.92, 1),
            font_size=16, bold=True,
        )
        btn_volver.bind(on_press=self._volver)
        header.add_widget(btn_volver)
        header.add_widget(Label(
            text="Partidas Guardadas",
            font_size=30, bold=True,
            color=(0.92, 0.82, 0.45, 1),
        ))
        header.add_widget(Widget(size_hint=(None, 1), width=140))
        root.add_widget(header)

        # ── Ruta activa ───────────────────────────────────────────────────────
        self._ruta_label = Label(
            text=f"Directorio: {PARTIDAS_DIR}",
            size_hint=(1, None), height=26,
            font_size=11,
            color=(0.50, 0.65, 0.85, 1),
            halign='left',
        )
        self._ruta_label.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], v[1])))
        root.add_widget(self._ruta_label)

        # ── Selector de skin ──────────────────────────────────────────────────
        skin_row = BoxLayout(orientation='horizontal', spacing=10,
                             size_hint=(1, None), height=48)
        skin_row.add_widget(Label(
            text="Skin:",
            size_hint=(None, 1), width=58,
            font_size=14, bold=True,
            color=(0.65, 0.65, 0.78, 1),
            halign='right',
        ))
        for key, lbl in [('clasico', 'Clásico'), ('vocaloid', 'Vocaloid'), ('shield', 'Shield')]:
            btn = Button(
                text=lbl,
                background_normal='',
                background_color=(COLOR_SKIN_SELECTED if key == self._selected_skin
                                  else COLOR_SKIN_NORMAL),
                color=(1, 1, 1, 1),
                font_size=14, bold=True,
            )
            btn.bind(on_press=lambda _, k=key: self._select_skin_p(k))
            self._skin_btns_p[key] = btn
            skin_row.add_widget(btn)
        root.add_widget(skin_row)

        # ── Lista de archivos PGN ─────────────────────────────────────────────
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._lista = GridLayout(cols=1, size_hint_y=None, spacing=4)
        self._lista.bind(minimum_height=self._lista.setter('height'))
        scroll.add_widget(self._lista)
        root.add_widget(scroll)

        # ── Botón cargar (se activa al seleccionar) ───────────────────────────
        self._btn_cargar = Button(
            text="Cargar partida seleccionada",
            size_hint=(0.45, None), height=56,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.18, 0.68, 0.28, 1),
            color=(1, 1, 1, 1),
            font_size=18, bold=True,
            opacity=0.35, disabled=True,
        )
        self._btn_cargar.bind(on_press=self._cargar_seleccionada)
        root.add_widget(self._btn_cargar)

        self.add_widget(root)

        self._seleccionada  = None
        self._item_buttons  = {}

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _volver(self, *_):
        self.manager.current = 'menu'

    def cargar_lista(self):
        """Lee PARTIDAS_DIR y muestra los archivos .pgn disponibles."""
        self._lista.clear_widgets()
        self._item_buttons.clear()
        self._seleccionada = None
        self._btn_cargar.disabled = True
        self._btn_cargar.opacity  = 0.35

        if not os.path.isdir(PARTIDAS_DIR):
            self._lista.add_widget(Label(
                text=f"Directorio no encontrado:\n{PARTIDAS_DIR}",
                size_hint=(1, None), height=60,
                color=(0.90, 0.40, 0.25, 1),
                font_size=14,
            ))
            return

        archivos = sorted(
            f for f in os.listdir(PARTIDAS_DIR)
            if f.lower().endswith('.pgn')
        )

        if not archivos:
            self._lista.add_widget(Label(
                text="No hay partidas guardadas (.pgn) en el directorio.",
                size_hint=(1, None), height=48,
                color=(0.65, 0.65, 0.72, 1),
                font_size=14,
            ))
            return

        for nombre in archivos:
            btn = Button(
                text=f"  {nombre}",
                size_hint=(1, None), height=44,
                background_normal='',
                background_color=self.COLOR_ITEM_BG,
                color=(0.88, 0.88, 0.92, 1),
                font_size=15,
                halign='left',
            )
            btn.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], v[1])))
            btn.bind(on_press=lambda _, n=nombre: self._seleccionar(n))
            self._item_buttons[nombre] = btn
            self._lista.add_widget(btn)

    def _seleccionar(self, nombre):
        self._seleccionada = nombre
        for n, btn in self._item_buttons.items():
            btn.background_color = (
                self.COLOR_ITEM_SEL if n == nombre else self.COLOR_ITEM_BG
            )
        self._btn_cargar.disabled = False
        self._btn_cargar.opacity  = 1.0

    def _select_skin_p(self, key):
        self._selected_skin = key
        for k, btn in self._skin_btns_p.items():
            btn.background_color = (COLOR_SKIN_SELECTED if k == key
                                    else COLOR_SKIN_NORMAL)

    def _cargar_seleccionada(self, *_):
        if not self._seleccionada:
            return
        ruta       = os.path.join(PARTIDAS_DIR, self._seleccionada)
        assets_dir = SKINS[self._selected_skin]
        game       = self.manager.get_screen('game')
        try:
            game.setup_replay(ruta, assets_dir)
        except Exception as e:
            self._lista.clear_widgets()
            self._item_buttons.clear()
            self._lista.add_widget(Label(
                text=f"Error al cargar la partida:\n{e}",
                size_hint=(1, None), height=60,
                color=(0.90, 0.40, 0.25, 1),
                font_size=13,
            ))
            return
        self.manager.current = 'game'


class GameScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._board = None

    def setup(self, assets_dir, mode='minimax'):
        self.clear_widgets()
        self._board = None
        is_ml = (mode == 'ml')
        Window.size = (ML_BOARD_SIZE + PANEL_WIDTH, BOARD_HEIGHT) if is_ml else (BOARD_WIDTH + PANEL_WIDTH, BOARD_HEIGHT)

        # Columna izquierda: tablero (arriba) + chat (abajo, sólo en modo ML)
        left_col  = BoxLayout(orientation='vertical', size_hint=(1, 1))
        board_row = BoxLayout(orientation='horizontal', size_hint=(1, 1))

        board = ChessBoard(
            assets_dir=assets_dir,
            on_move=None,           # se conecta después de crear el panel
            on_status=None,
            size_hint=(1, 1),       # ocupa todo el board_row; _draw adapta el tamaño
        )

        # Cargar motor ML si hay un modelo seleccionado
        app = App.get_running_app()
        if is_ml and getattr(app, 'ml_model_path', None):
            try:
                import tensor_aprendizaje
                motor = tensor_aprendizaje.MotorML()
                if motor.cargar_modelo(app.ml_model_path):
                    board._motor_ml       = motor
                    board._motor_ml_turno = getattr(app, 'ml_turno', None)
            except Exception as e:
                print(f"Error cargando motor ML: {e}")

        board_row.add_widget(board)

        chat = ChatPanel(
            size_hint=(1, None),
            height=CHAT_HEIGHT if is_ml else 0,
            opacity=1 if is_ml else 0,
        )

        left_col.add_widget(board_row)
        left_col.add_widget(chat)

        # Panel de movimientos/costes SIEMPRE a la derecha
        panel = MovePanel(size_hint=(None, 1), width=PANEL_WIDTH)
        panel.set_mode(mode)

        main = BoxLayout(orientation='horizontal')
        main.add_widget(left_col)
        main.add_widget(panel)

        # Conectar callbacks ahora que panel existe
        board.on_move_cb   = panel.add_entry
        board.on_status_cb = panel.set_status

        self._board  = board
        panel.board  = board

        self.add_widget(main)

    def setup_replay(self, pgn_path, assets_dir):
        """Carga un PGN y reproduce la partida movimiento a movimiento."""
        mode = App.get_running_app().game_mode
        movs = partidas_pgn.pgn_a_movimientos(pgn_path)
        self.setup(assets_dir, mode)
        self._board._replay_moves = movs
        self._board._replay_idx   = 0

    def pause_board(self):
        if self._board:
            self._board.pause()

    def resume_board(self):
        if self._board:
            self._board.resume()


class ChessApp(App):
    game_mode     = 'minimax'  # se actualiza en ModeScreen._elegir
    ml_model_path = None       # ruta del modelo seleccionado en ProbarModeloScreen
    ml_turno      = 0          # 0=ML juega blancas, 1=ML juega negras

    def build(self):
        self.title = "Ajedrez - Kivy"
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(ModeScreen(name='mode'))
        sm.add_widget(MLScreen(name='ml_menu'))
        sm.add_widget(EntrenarScreen(name='entrenar'))
        sm.add_widget(ProbarModeloScreen(name='probar'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(VideoScreen(name='video'))
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(PartidasScreen(name='partidas'))
        return sm


if __name__ == "__main__":
    ChessApp().run()
