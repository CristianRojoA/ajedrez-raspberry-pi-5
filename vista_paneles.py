from vista_config import *

try:
    from gemini_analista import AnalistaGemini
except Exception:
    AnalistaGemini = None


class ChatPanel(BoxLayout):
    """Panel de chat con análisis táctico vía Gemini.

    El usuario puede:
      - Escribir una pregunta (ej: "por qué moviste el caballo")
      - Tocar una jugada del historial (el tablero llama a explicar_jugada)
    Gemini explica la lógica táctica del movimiento combinando el material
    real capturado con análisis posicional.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=[8, 6, 8, 6], spacing=4, **kwargs)

        self.board = None              # se asigna desde GameScreen
        self._analista = None          # se crea perezosamente
        self._pensando = False

        with self.canvas.before:
            Color(*UI_BG_CARD)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self.add_widget(Label(
            text="Analista Táctico",
            size_hint=(1, None), height=26,
            font_size=13, bold=True,
            color=UI_NAVY,
        ))

        scroll = ScrollView(
            size_hint=(1, 1), do_scroll_x=False,
            scroll_type=['bars', 'content'],
            bar_width=12,
            bar_color=(0.08, 0.10, 0.43, 0.9),
            bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
        )
        self._msg_grid = GridLayout(cols=1, size_hint_y=None, spacing=2, padding=[4, 2])
        self._msg_grid.bind(minimum_height=self._msg_grid.setter('height'))
        scroll.add_widget(self._msg_grid)
        self.add_widget(scroll)

        self._add_msg("[Analista]", "Toca una jugada del historial o pregúntame por qué se hizo un movimiento.", system=True)

        input_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=36, spacing=6)
        self._input = TextInput(
            hint_text="Ej: ¿por qué moviste el caballo?",
            multiline=False,
            size_hint=(1, 1),
            font_size=12,
            background_color=UI_BG_ITEM,
            foreground_color=UI_TEXT_DARK,
            cursor_color=UI_NAVY,
        )
        self._input.bind(on_text_validate=self._send)
        btn_send = Button(
            text="Enviar",
            size_hint=(None, 1), width=72,
            background_normal='',
            background_color=UI_NAVY,
            color=UI_WHITE,
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
        color = UI_TEXT_SOFT if system else UI_TEXT_DARK
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

    def _get_analista(self):
        """Crea el analista la primera vez que se necesita."""
        if self._analista is None and AnalistaGemini is not None:
            self._analista = AnalistaGemini()
        return self._analista

    def _resolver_jugada(self, pregunta):
        """Decide qué jugada del historial explicar según la pregunta.
        Si la pregunta menciona un número de jugada lo usa; si no, usa la última."""
        if not self.board or not self.board._history:
            return None

        hist = self.board._history

        # ¿Mencionó un número? (ej: "jugada 5", "movimiento 3")
        import re
        m = re.search(r'\b(\d+)\b', pregunta)
        if m:
            idx = int(m.group(1)) - 1   # el usuario cuenta desde 1
            if 0 <= idx < len(hist):
                return hist[idx]

        # Por defecto, la última jugada
        return hist[-1]

    def _send(self, *_):
        txt = self._input.text.strip()
        if not txt:
            return
        self._add_msg("[Tú]", txt)
        self._input.text = ''

        if self._pensando:
            self._add_msg("[Analista]", "Espera, aún estoy pensando en la jugada anterior...", system=True)
            return

        entry = self._resolver_jugada(txt)
        if entry is None:
            self._add_msg("[Analista]", "Todavía no hay jugadas para analizar.", system=True)
            return

        self._preguntar_gemini(entry, txt)

    def explicar_jugada(self, idx):
        """Llamado desde el tablero/panel cuando el usuario toca una jugada."""
        if not self.board or idx < 0 or idx >= len(self.board._history):
            return
        if self._pensando:
            return
        entry = self.board._history[idx]
        self._add_msg("[Tú]", f"Explícame la jugada {idx + 1}")
        self._preguntar_gemini(entry, None)

    def _preguntar_gemini(self, entry, pregunta):
        """Lanza la consulta a Gemini en segundo plano."""
        analista = self._get_analista()
        if analista is None:
            self._add_msg("[Analista]", "Módulo Gemini no instalado (pip install google-generativeai).", system=True)
            return
        if not analista.disponible:
            self._add_msg("[Analista]", f"No disponible: {analista.error}", system=True)
            return

        self._pensando = True
        self._add_msg("[Analista]", "Analizando la jugada...", system=True)

        def _on_respuesta(texto):
            # Gemini responde en otro thread → volver al hilo de Kivy
            Clock.schedule_once(lambda dt: self._mostrar_respuesta(texto), 0)

        analista.explicar_async(entry, _on_respuesta, pregunta)

    def _mostrar_respuesta(self, texto):
        self._pensando = False
        self._add_msg("[Analista]", texto)


class MovePanel(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=[10, 10, 10, 10], spacing=6, **kwargs)

        self.board = None
        self.chat_panel = None

        with self.canvas.before:
            Color(*UI_BG_CARD)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.add_widget(Label(
            text="Movimientos",
            size_hint=(1, None), height=40,
            bold=True, font_size=18,
            color=UI_NAVY,
        ))

        self._status_label = Label(
            text="",
            size_hint=(1, None), height=28,
            font_size=12, bold=True,
            color=(0.95, 0.40, 0.20, 1),
        )
        self.add_widget(self._status_label)

        self._scroll = ScrollView(
            size_hint=(1, 1), do_scroll_x=False,
            scroll_type=['bars', 'content'],
            bar_width=14,
            bar_color=(0.08, 0.10, 0.43, 0.9),
            bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
        )
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
            background_color=UI_NAVY_MID,
            color=UI_WHITE,
            font_size=14, bold=True,
        )
        self._btn_guardar.bind(on_press=self._guardar_partida)
        self.add_widget(self._btn_guardar)

        self._btn_volver = Button(
            text="< Menú",
            size_hint=(1, None), height=40,
            background_normal='',
            background_color=UI_BG_ITEM,
            color=UI_TEXT_DARK,
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

    def _add_entry_ml(self, text, idx, stats):
        """Entrada ML con bloque expandible de análisis de complejidad."""
        B = 4; F = 128; P = 4096; k = 12; d = 2; b = 30

        valor       = stats.get('valor', 0.0)
        conf        = stats.get('confianza', 0.0)
        num_leg     = stats.get('num_legales', 0)
        top3        = stats.get('dist_top3', [])

        flops_red     = 64*14*F*9 + B*2*64*F*F*9 + 64*F*2 + 64*2*P + 64*F + 64*256 + 256
        nodos_hibrido = k * (b ** (d - 1))
        nodos_puro    = b ** d
        reduccion     = max(0, int(100 * (1 - nodos_hibrido / max(nodos_puro, 1))))

        if conf >= 40:
            bg = (0.82, 0.92, 0.84, 1)
        elif conf >= 15:
            bg = (0.95, 0.92, 0.80, 1)
        else:
            bg = (0.92, 0.82, 0.82, 1)

        top3_lines = ""
        for i, (sq_d, sq_h, prob) in enumerate(top3, 1):
            marker = "  <-- elegido" if i == 1 else ""
            top3_lines += f"\n  {i}. {sq_d}-{sq_h}  {prob:>5.1f}%{marker}"

        detalle = (
            f"Paradigma: Red neuronal residual dual (AlphaZero)\n"
            f"Estrategia complementaria: Minimax hibrido (top-{k})\n"
            f"------------------------------------------------\n"
            f"ARQUITECTURA DE LA RED\n"
            f"  B bloques residuales = {B:>5}\n"
            f"  F filtros por capa   = {F:>5}\n"
            f"  P tamano policy      = {P:>5}\n"
            f"  Complejidad red      = O(B*F^2+F*P)  ~{flops_red//1_000_000}M FLOPs\n"
            f"------------------------------------------------\n"
            f"SELECCION DEL MOVIMIENTO\n"
            f"  Movs. legales (M)    = {num_leg:>5}\n"
            f"  Ordenacion O(M*logM) = O({num_leg}*log{num_leg})\n"
            f"  Candidatos top-k     = {k:>5}\n"
            f"  Nodos hibrido O(k*b^(d-1)) = {nodos_hibrido:>5,}\n"
            f"  Nodos puro    O(b^d) = {nodos_puro:>5,}\n"
            f"  Reduccion vs puro    = {reduccion:>5}%\n"
            f"------------------------------------------------\n"
            f"EVALUACION DE LA POSICION\n"
            f"  Valor red [-1,+1]    = {valor:>+.3f}\n"
            f"  Confianza movimiento = {conf:>5.1f}%\n"
            f"------------------------------------------------\n"
            f"TOP MOVIMIENTOS (policy):{top3_lines}"
        )

        detail_height = detalle.count('\n') * 15 + 27
        label_clean   = text.replace('[', '').replace(']', '')

        container = BoxLayout(orientation='vertical', size_hint=(1, None), height=28)

        header = Button(
            text=f"  {idx + 1:>3}. {label_clean}",
            size_hint=(1, None), height=28,
            background_normal='',
            background_color=COLOR_MOVE_NORMAL,
            color=UI_TEXT_DARK,
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
            color=UI_TEXT_DARK,
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

    def set_status(self, text):
        self._status_label.text = text

    def _update_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def add_entry(self, text, idx, stats):
        if self._mode == 'ml':
            self._add_entry_ml(text, idx, stats)
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
            bg = (0.82, 0.92, 0.84, 1)
        elif ahorro >= 30:
            bg = (0.95, 0.92, 0.80, 1)
        else:
            bg = (0.92, 0.82, 0.82, 1)

        container = BoxLayout(orientation='vertical', size_hint=(1, None), height=28)

        header = Button(
            text=f"  {idx + 1:>3}. {label_clean}",
            size_hint=(1, None), height=28,
            background_normal='',
            background_color=COLOR_MOVE_NORMAL,
            color=UI_TEXT_DARK,
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
            color=UI_TEXT_DARK,
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
        # Si hay un panel de chat conectado, pedir la explicación táctica
        if getattr(self, 'chat_panel', None) is not None:
            self.chat_panel.explicar_jugada(idx)

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
            font_size=14, color=UI_TEXT_DARK,
            halign='left',
        ))

        entrada = TextInput(
            text=sugerido,
            multiline=False,
            size_hint=(1, None), height=42,
            font_size=15,
            background_color=UI_BG_ITEM,
            foreground_color=UI_TEXT_DARK,
            cursor_color=UI_NAVY,
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
            background_color=UI_BG_ITEM,
            color=UI_TEXT_DARK, font_size=14, bold=True,
        )
        btn_ok = Button(
            text="Guardar",
            background_normal='',
            background_color=UI_GREEN,
            color=UI_WHITE, font_size=14, bold=True,
        )
        botones.add_widget(btn_cancel)
        botones.add_widget(btn_ok)
        content.add_widget(botones)

        popup = Popup(
            title="Guardar partida",
            content=content,
            size_hint=(None, None), size=(480, 240),
            background_color=UI_BG_PAGE,
            title_color=UI_NAVY,
            title_size=16,
            separator_color=UI_NAVY,
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
                                      UI_NAVY_MID),
                    2.5,
                )
            except Exception as e:
                self._error_lbl.text = f"Error: {e}"

        btn_ok.bind(on_press=_on_guardar)
        entrada.bind(on_text_validate=_on_guardar)
        btn_cancel.bind(on_press=lambda _: popup.dismiss())

        popup.open()
