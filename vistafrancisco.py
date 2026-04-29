from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '800')
Config.set('graphics', 'resizable', '0')

import os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from modeloraul import inicializar_ajedrez, elegir_movimiento_aleatorio, hacer_movimiento

ASSETS_DIR = os.path.join('assets', 'vocaloid_backup')

WIDTH, HEIGHT  = 800, 800
SQUARE_SIZE    = WIDTH // 8
PIECE_SIZE     = int(SQUARE_SIZE * 0.85)
PIECE_OFFSET   = (SQUARE_SIZE - PIECE_SIZE) // 2

ANIM_DURATION  = 0.40   # segundos que dura el desplazamiento de la pieza
MOVE_DELAY     = 0.55   # pausa entre el fin de una animación y el siguiente turno

LIGHT_SQUARE   = (232/255, 235/255, 239/255, 1)
DARK_SQUARE    = (125/255, 135/255, 150/255, 1)
HIGHLIGHT      = (0.95, 0.85, 0.15, 0.45)   # amarillo semitransparente para último movimiento

PIECE_NAMES = {
     1: "peon_b",    2: "caballo_b",  3: "alfill_b",  4: "torre_b",  5: "reina_b",  6: "rey_b",
    -1: "peon",     -2: "caballo",   -3: "alfil",    -4: "torre",   -5: "reina",   -6: "rey",
}


class ChessBoard(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tablero  = inicializar_ajedrez()
        self.textures = self._load_assets()
        self.turno    = 0        # 0 = blancas, 1 = negras

        # ── Estado de animación ──────────────────────────────────────────────
        self._anim_active   = False
        self._anim_progress = 0.0
        self._anim_from     = None   # índice origen
        self._anim_to       = None   # índice destino
        self._anim_piece    = None   # código de pieza durante el vuelo
        self._anim_final    = None   # código que quedará en destino al terminar

        self.bind(pos=self._draw, size=self._draw)
        self._draw()
        Clock.schedule_once(self._next_move, 1.0)   # primer movimiento tras 1 s

    # ── Carga de assets ───────────────────────────────────────────────────────

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

    # ── Lógica de turno ───────────────────────────────────────────────────────

    def _next_move(self, *_):
        move = elegir_movimiento_aleatorio(self.tablero, self.turno)
        if move is None:
            print(f"Sin movimientos para {'blancas' if self.turno == 0 else 'negras'}. Partida terminada.")
            return

        desde, hasta = move
        pieza_volando = self.tablero[desde]          # pieza antes de mover (para dibujar en vuelo)
        hacer_movimiento(self.tablero, desde, hasta)
        pieza_final   = self.tablero[hasta]          # puede ser reina si hubo promoción

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
        # Ocultar destino durante el vuelo (la captura ya ocurrió en el modelo)
        self.tablero[hasta] = 0
        Clock.schedule_interval(self._tick_anim, 1 / 60)

    def _tick_anim(self, dt):
        self._anim_progress += dt / ANIM_DURATION
        if self._anim_progress >= 1.0:
            self._anim_progress = 1.0
            self._anim_active   = False
            self.tablero[self._anim_to] = self._anim_final   # restaurar pieza en destino
            self._draw()
            Clock.schedule_once(self._next_move, MOVE_DELAY)
            return False   # desregistrar este callback de Clock

        self._draw()

    @staticmethod
    def _ease(t):
        """Smoothstep: aceleración y desaceleración suaves."""
        return t * t * (3.0 - 2.0 * t)

    # ── Dibujo ────────────────────────────────────────────────────────────────

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:

            # 1. Casillas del tablero
            for i in range(64):
                row, col = i // 8, i % 8
                Color(*(LIGHT_SQUARE if (row + col) % 2 == 1 else DARK_SQUARE))
                Rectangle(pos=(col * SQUARE_SIZE, row * SQUARE_SIZE),
                          size=(SQUARE_SIZE, SQUARE_SIZE))

            # 2. Resaltado del último movimiento (origen y destino)
            if self._anim_from is not None:
                for idx in (self._anim_from, self._anim_to):
                    r, c = idx // 8, idx % 8
                    Color(*HIGHLIGHT)
                    Rectangle(pos=(c * SQUARE_SIZE, r * SQUARE_SIZE),
                              size=(SQUARE_SIZE, SQUARE_SIZE))

            # 3. Piezas estáticas
            for i in range(64):
                nombre = PIECE_NAMES.get(self.tablero[i])
                if nombre and nombre in self.textures:
                    row, col = i // 8, i % 8
                    Color(1, 1, 1, 1)
                    Rectangle(texture=self.textures[nombre],
                              pos=(col * SQUARE_SIZE + PIECE_OFFSET,
                                   row * SQUARE_SIZE + PIECE_OFFSET),
                              size=(PIECE_SIZE, PIECE_SIZE))

            # 4. Pieza en vuelo (dibujada encima de todo)
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
        board = ChessBoard(size=(WIDTH, HEIGHT), size_hint=(None, None))
        board.pos = (0, 0)
        return board


if __name__ == "__main__":
    ChessApp().run()
