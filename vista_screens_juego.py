from vista_config import *
from vista_paneles import ChatPanel, MovePanel
from vista_tablero import ChessBoard


class MenuScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected  = DEFAULT_SKIN
        self._skin_btns = {}

        with self.canvas.before:
            Color(*UI_BG_PAGE)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical', padding=[200, 60, 200, 60], spacing=24)

        # Fila superior: botón volver al modo
        back_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=44)
        btn_back = Button(
            text="< Tipo de análisis",
            size_hint=(None, 1), width=200,
            background_normal='',
            background_color=UI_NAVY,
            color=UI_WHITE,
            font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'mode'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Widget(size_hint=(1, 1)))
        root.add_widget(back_row)

        root.add_widget(Label(
            text="Ajedrez",
            font_size=80, bold=True,
            color=UI_NAVY,
            size_hint=(1, None), height=130,
        ))

        root.add_widget(Widget(size_hint=(1, 0.15)))

        root.add_widget(Label(
            text="Skins",
            font_size=22, bold=True,
            color=UI_TEXT_DARK,
            size_hint=(1, None), height=36,
        ))

        skins_row = BoxLayout(orientation='horizontal', spacing=16,
                              size_hint=(1, None), height=64)
        for key, label in [('clasico', 'Clásico'), ('vocaloid', 'Vocaloid'), ('shield', 'Shield')]:
            btn = Button(
                text=label,
                background_normal='',
                background_color=COLOR_SKIN_SELECTED if key == self._selected else COLOR_SKIN_NORMAL,
                color=UI_WHITE,
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
            background_color=UI_GREEN,
            color=UI_WHITE,
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
            background_color=UI_NAVY_MID,
            color=UI_WHITE,
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

    COLOR_ITEM_BG  = UI_BG_ITEM
    COLOR_ITEM_SEL = UI_NAVY_SEL
    COLOR_VOLVER   = UI_NAVY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_skin = DEFAULT_SKIN
        self._skin_btns_p   = {}

        with self.canvas.before:
            Color(*UI_BG_PAGE)
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
            color=UI_WHITE,
            font_size=16, bold=True,
        )
        btn_volver.bind(on_press=self._volver)
        header.add_widget(btn_volver)
        header.add_widget(Label(
            text="Partidas Guardadas",
            font_size=30, bold=True,
            color=UI_NAVY,
        ))
        header.add_widget(Widget(size_hint=(None, 1), width=140))
        root.add_widget(header)

        # ── Ruta activa ───────────────────────────────────────────────────────
        self._ruta_label = Label(
            text=f"Directorio: {PARTIDAS_DIR}",
            size_hint=(1, None), height=26,
            font_size=11,
            color=UI_TEXT_SOFT,
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
            color=UI_TEXT_DARK,
            halign='right',
        ))
        for key, lbl in [('clasico', 'Clásico'), ('vocaloid', 'Vocaloid'), ('shield', 'Shield')]:
            btn = Button(
                text=lbl,
                background_normal='',
                background_color=(COLOR_SKIN_SELECTED if key == self._selected_skin
                                  else COLOR_SKIN_NORMAL),
                color=UI_WHITE,
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
            background_color=UI_GREEN,
            color=UI_WHITE,
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
                color=UI_TEXT_SOFT,
                font_size=14,
            ))
            return

        for nombre in archivos:
            btn = Button(
                text=f"  {nombre}",
                size_hint=(1, None), height=44,
                background_normal='',
                background_color=self.COLOR_ITEM_BG,
                color=UI_TEXT_DARK,
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
