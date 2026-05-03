from kivy.config import Config
Config.set('graphics', 'width', '1520')
Config.set('graphics', 'height', '960')
Config.set('graphics', 'resizable', '0')

import os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition

from modeloraul import (inicializar_ajedrez, elegir_movimiento,
                        hacer_movimiento, estado_juego, esta_en_jaque,
                        get_last_stats, hash_tablero)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKINS = {
    'clasico':  os.path.join(BASE_DIR, 'assets', 'clasico'),
    'vocaloid': os.path.join(BASE_DIR, 'assets', 'vocaloid_backup'),
    'shield':   os.path.join(BASE_DIR, 'assets', 'shield'),
}
DEFAULT_SKIN = 'vocaloid'

BOARD_WIDTH  = 960
BOARD_HEIGHT = 960
PANEL_WIDTH  = 560
SQUARE_SIZE  = BOARD_WIDTH // 8
PIECE_SIZE   = int(SQUARE_SIZE * 0.85)
PIECE_OFFSET = (SQUARE_SIZE - PIECE_SIZE) // 2

ANIM_DURATION = 0.40
MOVE_DELAY    = 0.55

LIGHT_SQUARE = (232/255, 235/255, 239/255, 1)
DARK_SQUARE  = (125/255, 135/255, 150/255, 1)
HIGHLIGHT    = (0.95, 0.85, 0.15, 0.45)

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

        self.board         = None
        self._move_buttons = []

    def set_status(self, text):
        self._status_label.text = text

    def _update_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def add_entry(self, text, idx, stats):
        b  = max(stats.get('movimientos_raiz', 1), 1)
        d  = stats.get('profundidad', 2)
        n  = stats.get('nodos', 0)
        p  = stats.get('podas', 0)
        ch = stats.get('cache_hits', 0)

        o_bruto  = b ** d
        o_optimo = max(int(b ** (d / 2)), 1)
        ahorro   = max(0, int(100 * (1 - n / max(o_bruto, 1))))
        b_ef     = round(n ** (1 / d), 1) if n > 0 else 0

        label_clean = text.replace('[', '').replace(']', '')

        detalle = (
            f"b (raiz)={b}   d={d}\n"
            f"Nodos eval: {n:>6,}\n"
            f"Podas a-b:  {p:>6,}\n"
            f"Hits cache: {ch:>6,}\n"
            f"------------------------\n"
            f"O(b^d) sin poda: O({o_bruto:,})\n"
            f"O(b^d/2) optimo: O({o_optimo:,})\n"
            f"O efectivo:      O({n:,})\n"
            f"b efectiva:      ~{b_ef}\n"
            f"Ahorro vs bruto: {ahorro}%"
        )

        detail_height = detalle.count('\n') * 15 + 27

        if ahorro >= 70:
            bg = (0.08, 0.20, 0.10, 1)
        elif ahorro >= 40:
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


class ChessBoard(Widget):

    def __init__(self, on_move=None, on_status=None, assets_dir=None, **kwargs):
        super().__init__(**kwargs)
        self._assets_dir  = assets_dir or SKINS[DEFAULT_SKIN]
        self.tablero      = inicializar_ajedrez()
        self.textures     = self._load_assets()
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

        move  = elegir_movimiento(self.tablero, self.turno, historial=self._historial)
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

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:

            for i in range(64):
                row, col = i // 8, i % 8
                Color(*(LIGHT_SQUARE if (row + col) % 2 == 1 else DARK_SQUARE))
                Rectangle(pos=(col * SQUARE_SIZE, row * SQUARE_SIZE),
                          size=(SQUARE_SIZE, SQUARE_SIZE))

            if self._anim_from is not None:
                for idx in (self._anim_from, self._anim_to):
                    r, c = idx // 8, idx % 8
                    Color(*HIGHLIGHT)
                    Rectangle(pos=(c * SQUARE_SIZE, r * SQUARE_SIZE),
                              size=(SQUARE_SIZE, SQUARE_SIZE))

            for i in range(64):
                nombre = PIECE_NAMES.get(self.tablero[i])
                if nombre and nombre in self.textures:
                    row, col = i // 8, i % 8
                    pw   = int(PIECE_SIZE * PIECE_WIDTH_SCALE.get(nombre, 1.0))
                    px   = col * SQUARE_SIZE + (SQUARE_SIZE - pw) // 2
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(px, row * SQUARE_SIZE + PIECE_OFFSET),
                              size=(pw, PIECE_SIZE))

            if self._anim_active:
                fr, fc = self._anim_from // 8, self._anim_from % 8
                tr, tc = self._anim_to   // 8, self._anim_to   % 8
                t      = self._ease(self._anim_progress)
                nombre = PIECE_NAMES.get(self._anim_piece)
                if nombre and nombre in self.textures:
                    pw    = int(PIECE_SIZE * PIECE_WIDTH_SCALE.get(nombre, 1.0))
                    x_off = (SQUARE_SIZE - pw) // 2
                    ax    = (fc + (tc - fc) * t) * SQUARE_SIZE + x_off
                    ay    = (fr + (tr - fr) * t) * SQUARE_SIZE + PIECE_OFFSET
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(ax, ay), size=(pw, PIECE_SIZE))

            if self._game_over:
                Color(0, 0, 0, 0.52)
                Rectangle(pos=self.pos, size=self.size)


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
        game = self.manager.get_screen('game')
        game.setup(SKINS[self._selected])
        self.manager.current = 'game'


class GameScreen(Screen):

    def setup(self, assets_dir):
        self.clear_widgets()
        layout = BoxLayout(orientation='horizontal')
        panel  = MovePanel(size_hint=(None, 1), width=PANEL_WIDTH)
        board  = ChessBoard(
            assets_dir=assets_dir,
            on_move=panel.add_entry,
            on_status=panel.set_status,
            size=(BOARD_WIDTH, BOARD_HEIGHT),
            size_hint=(None, None),
        )
        panel.board = board
        layout.add_widget(board)
        layout.add_widget(panel)
        self.add_widget(layout)


class ChessApp(App):
    def build(self):
        self.title = "Ajedrez - Kivy"
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        return sm


if __name__ == "__main__":
    ChessApp().run()
