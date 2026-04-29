from kivy.config import Config
Config.set('graphics', 'width', '1050')
Config.set('graphics', 'height', '800')
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

from modeloraul import inicializar_ajedrez, elegir_movimiento_aleatorio, hacer_movimiento

ASSETS_DIR = os.path.join('assets', 'vocaloid_backup')

BOARD_WIDTH  = 800
BOARD_HEIGHT = 800
PANEL_WIDTH  = 250
SQUARE_SIZE  = BOARD_WIDTH // 8
PIECE_SIZE   = int(SQUARE_SIZE * 0.85)
PIECE_OFFSET = (SQUARE_SIZE - PIECE_SIZE) // 2

ANIM_DURATION = 0.40
MOVE_DELAY    = 0.55

LIGHT_SQUARE = (232/255, 235/255, 239/255, 1)
DARK_SQUARE  = (125/255, 135/255, 150/255, 1)
HIGHLIGHT    = (0.95, 0.85, 0.15, 0.45)

PIECE_NAMES = {
     1: "peon_b",    2: "caballo_b",  3: "alfill_b",  4: "torre_b",  5: "reina_b",  6: "rey_b",
    -1: "peon",     -2: "caballo",   -3: "alfil",    -4: "torre",   -5: "reina",   -6: "rey",
}

PIECE_LABELS = {
     1: "Peon",    2: "Caballo",  3: "Alfil",  4: "Torre",  5: "Reina",  6: "Rey",
    -1: "Peon",   -2: "Caballo", -3: "Alfil", -4: "Torre", -5: "Reina", -6: "Rey",
}

COLS = "abcdefgh"

COLOR_MOVE_NORMAL   = (0.15, 0.15, 0.20, 1)
COLOR_MOVE_SELECTED = (0.25, 0.38, 0.60, 1)
COLOR_BTN_PAUSE     = (0.18, 0.48, 0.78, 1)
COLOR_BTN_RESUME    = (0.18, 0.68, 0.28, 1)


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

    def _update_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def add_move(self, text, idx):
        btn = Button(
            text=f"  {idx + 1:>3}. {text}",
            size_hint=(1, None), height=28,
            background_normal='',
            background_color=COLOR_MOVE_NORMAL,
            color=(0.88, 0.88, 0.88, 1),
            font_size=12,
            halign='left',
        )
        btn.bind(
            size=lambda w, v: setattr(w, 'text_size', (v[0], v[1])),
            on_press=lambda _, i=idx: self._on_move_clicked(i),
        )
        self._move_list.add_widget(btn)
        self._move_buttons.append(btn)

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

    def __init__(self, on_move=None, **kwargs):
        super().__init__(**kwargs)
        self.tablero    = inicializar_ajedrez()
        self.textures   = self._load_assets()
        self.turno      = 0
        self.on_move_cb = on_move

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
        self._initial_board = self.tablero[:]
        self._history       = []   # list of dicts: board_before/after, desde, hasta, piezas

        self.bind(pos=self._draw, size=self._draw)
        self._draw()
        self._pending_event = Clock.schedule_once(self._next_move, 1.0)

    # ── Assets ───────────────────────────────────────────────────────────────

    def _load_assets(self):
        textures = {}
        for nombre in set(PIECE_NAMES.values()):
            path = os.path.join(ASSETS_DIR, f"{nombre}.png")
            if not os.path.isfile(path):
                print(f"Advertencia: no se encontró {path}")
                continue
            try:
                textures[nombre] = CoreImage(path).texture
            except Exception:
                print(f"Advertencia: no se pudo cargar {path}")
        return textures

    # ── Pausa / reanudación ───────────────────────────────────────────────────

    def pause(self):
        self._paused = True
        if self._pending_event:
            self._pending_event.cancel()
            self._pending_event = None
        if not self._live_saved:
            src = self._history[-1]['board_after'] if self._history else self._initial_board
            self._live_tablero = src[:]
            self._live_turno   = self.turno
            self._live_saved   = True

    def resume(self):
        self._paused    = False
        self._reviewing = False
        if self._live_saved and self._live_tablero is not None:
            self.tablero     = self._live_tablero[:]
            self.turno       = self._live_turno
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

        move = elegir_movimiento_aleatorio(self.tablero, self.turno)
        if move is None:
            print(f"Sin movimientos para {'blancas' if self.turno == 0 else 'negras'}. Partida terminada.")
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

        if self.on_move_cb:
            color  = "Blancas" if self.turno == 0 else "Negras"
            nombre = PIECE_LABELS.get(pieza_volando, "?")
            sq     = idx_to_sq(hasta)
            self.on_move_cb(f"[{color}] {nombre} {sq}", move_idx)

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
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(col * SQUARE_SIZE + PIECE_OFFSET,
                                   row * SQUARE_SIZE + PIECE_OFFSET),
                              size=(PIECE_SIZE, PIECE_SIZE))

            if self._anim_active:
                fr, fc = self._anim_from // 8, self._anim_from % 8
                tr, tc = self._anim_to   // 8, self._anim_to   % 8
                t  = self._ease(self._anim_progress)
                ax = (fc + (tc - fc) * t) * SQUARE_SIZE + PIECE_OFFSET
                ay = (fr + (tr - fr) * t) * SQUARE_SIZE + PIECE_OFFSET
                nombre = PIECE_NAMES.get(self._anim_piece)
                if nombre and nombre in self.textures:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(ax, ay), size=(PIECE_SIZE, PIECE_SIZE))


class ChessApp(App):
    def build(self):
        self.title = "Ajedrez - Kivy"
        root  = BoxLayout(orientation='horizontal')
        panel = MovePanel(size_hint=(None, 1), width=PANEL_WIDTH)
        board = ChessBoard(
            on_move=panel.add_move,
            size=(BOARD_WIDTH, BOARD_HEIGHT),
            size_hint=(None, None),
        )
        panel.board = board
        root.add_widget(board)
        root.add_widget(panel)
        return root


if __name__ == "__main__":
    ChessApp().run()
