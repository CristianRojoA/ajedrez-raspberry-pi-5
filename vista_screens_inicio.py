from vista_config import *


def _make_btn_group(btn_text, sub_text, width_hint, btn_height=88, card_height=42):
    """Botón navy + tarjeta de subtítulo bordeada, sin espacio entre ellos."""
    grp = BoxLayout(
        orientation='vertical',
        size_hint=(width_hint, None),
        pos_hint={'center_x': 0.5},
        height=btn_height + card_height,
        spacing=0,
    )

    btn = Button(
        text=btn_text,
        size_hint=(1, None), height=btn_height,
        background_normal='',
        background_color=UI_NAVY,
        color=UI_WHITE,
        font_size=26, bold=True,
    )

    card = BoxLayout(size_hint=(1, None), height=card_height)
    with card.canvas.before:
        _bg  = Color(*UI_BG_PAGE)
        _bgr = RoundedRectangle(pos=card.pos, size=card.size, radius=[6])
        _bdc = Color(*UI_NAVY)
        _bdl = Line(width=1.5)

    def _upd(w, *_):
        _bgr.pos  = w.pos
        _bgr.size = w.size
        _bdl.rounded_rectangle = [w.x, w.y, w.width, w.height, 6]

    card.bind(pos=_upd, size=_upd)

    lbl = Label(
        text=sub_text, font_size=16,
        color=UI_TEXT_SOFT, halign='center',
    )
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], None)))
    card.add_widget(lbl)

    grp.add_widget(btn)
    grp.add_widget(card)
    return grp, btn


class ModeScreen(Screen):
    """Primera pantalla: el jugador elige entre Minimax y Machine Learning."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*UI_BG_PAGE)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical', padding=[180, 60, 180, 60], spacing=20)

        root.add_widget(Label(
            text="Ajedrez",
            font_size=82, bold=True,
            color=UI_NAVY,
            size_hint=(1, None), height=130,
        ))

        root.add_widget(Label(
            text="Selecciona el tipo de análisis",
            font_size=20,
            color=UI_TEXT_SOFT,
            size_hint=(1, None), height=36,
        ))

        root.add_widget(Widget(size_hint=(1, 0.6)))

        grp_minimax, btn_minimax = _make_btn_group(
            "Análisis Minimax",
            "Búsqueda exhaustiva · Poda alfa-beta · Memoización DP",
            width_hint=0.60,
        )
        btn_minimax.bind(on_press=lambda _: self._elegir('minimax'))
        root.add_widget(grp_minimax)

        root.add_widget(Widget(size_hint=(1, None), height=28))

        grp_ml, btn_ml = _make_btn_group(
            "Análisis Machine Learning",
            "Modelo de aprendizaje profundo — en desarrollo",
            width_hint=0.60,
        )
        btn_ml.bind(on_press=lambda _: self._elegir('ml'))
        root.add_widget(grp_ml)

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
            Color(*UI_BG_PAGE)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        root = BoxLayout(orientation='vertical',
                         padding=[180, 60, 180, 60], spacing=20)

        back_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44)
        btn_back = Button(
            text="< Tipo de análisis", size_hint=(None, 1), width=210,
            background_normal='', background_color=UI_NAVY,
            color=UI_WHITE, font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'mode'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Widget(size_hint=(1, 1)))
        root.add_widget(back_row)

        root.add_widget(Label(
            text="Machine Learning",
            font_size=70, bold=True, color=UI_NAVY,
            size_hint=(1, None), height=120,
        ))
        root.add_widget(Label(
            text="Entrena y prueba el motor de IA con tus propias partidas",
            font_size=17, color=UI_TEXT_SOFT,
            size_hint=(1, None), height=30,
        ))
        root.add_widget(Widget(size_hint=(1, 0.5)))

        grp_entrenar, btn_entrenar = _make_btn_group(
            "Entrenar Modelo",
            "Selecciona archivos PGN y entrena la red neuronal",
            width_hint=0.55,
        )
        btn_entrenar.bind(
            on_press=lambda _: setattr(self.manager, 'current', 'entrenar'))
        root.add_widget(grp_entrenar)

        root.add_widget(Widget(size_hint=(1, None), height=30))

        grp_probar, btn_probar = _make_btn_group(
            "Probar Modelo",
            "Elige un modelo entrenado y observa cómo juega",
            width_hint=0.55,
        )
        btn_probar.bind(
            on_press=lambda _: setattr(self.manager, 'current', 'probar'))
        root.add_widget(grp_probar)

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
