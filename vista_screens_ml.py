from vista_config import *


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
            Color(*UI_BG_PAGE)
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
            background_normal='', background_color=UI_NAVY_MID,
            color=UI_WHITE, font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'ml_menu'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Label(
            text="Entrenar Modelo",
            font_size=32, bold=True, color=UI_NAVY,
            halign='center',
        ))
        back_row.add_widget(Widget(size_hint=(None, 1), width=90))
        outer.add_widget(back_row)

        # Contenedor central — fluido, se adapta al ancho disponible
        root = BoxLayout(orientation='vertical',
                         size_hint=(1, 1), spacing=10)

        # ── Continuar desde modelo existente ─────────────────────────────────
        root.add_widget(Label(
            text="Continuar entrenando desde modelo existente (opcional):",
            font_size=16, bold=True, color=UI_TEXT_DARK,
            size_hint=(1, None), height=28,
            halign='left', valign='middle',
        ))
        base_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44, spacing=8)
        self._lbl_base = Label(
            text="Nuevo modelo desde cero",
            font_size=15, bold=True, color=UI_GREEN,
            size_hint=(1, 1), halign='left', valign='middle',
        )
        self._lbl_base.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], None)))
        btn_elegir_base = Button(
            text="Elegir modelo base",
            size_hint=(None, 1), width=180,
            background_normal='', background_color=UI_NAVY_MID,
            color=UI_WHITE, font_size=13, bold=True,
        )
        btn_elegir_base.bind(on_press=self._popup_elegir_base)
        btn_limpiar_base = Button(
            text="Limpiar",
            size_hint=(None, 1), width=80,
            background_normal='', background_color=UI_RED,
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
            font_size=16, bold=True, color=UI_TEXT_DARK,
            size_hint=(1, None), height=30,
            halign='left', valign='middle',
        ))

        # ScrollView PGNs
        pgn_scroll = ScrollView(
            size_hint=(1, None), height=160, do_scroll_x=False,
            scroll_type=['bars', 'content'],
            bar_width=14,
            bar_color=(0.08, 0.10, 0.43, 0.9),
            bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
        )
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
            background_normal='', background_color=UI_NAVY,
            color=UI_WHITE, font_size=13,
        )
        btn_none = Button(
            text="Deseleccionar todo",
            background_normal='', background_color=UI_RED,
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
            background_normal='', background_color=UI_GREEN,
            color=UI_WHITE, font_size=20, bold=True,
        )
        self._btn_entrenar.bind(on_press=self._iniciar_entrenamiento)
        root.add_widget(self._btn_entrenar)

        outer.add_widget(root)

        # Log de progreso
        root.add_widget(Label(
            text="Progreso:", font_size=16, bold=True, color=UI_TEXT_DARK,
            size_hint=(1, None), height=26,
            halign='left', valign='middle',
        ))
        self._log_scroll = ScrollView(
            size_hint=(1, 1), do_scroll_x=False,
            scroll_type=['bars', 'content'],
            bar_width=14,
            bar_color=(0.08, 0.10, 0.43, 0.9),
            bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
        )
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
                size_hint=(1, None), height=40,
                background_normal='',
                background_color=UI_BG_ITEM,
                color=UI_TEXT_DARK,
                font_size=15, halign='left', valign='middle',
            )
            btn.bind(on_press=lambda b, r=ruta: self._toggle_pgn(r))
            self._pgn_btns[ruta] = btn
            self._pgn_grid.add_widget(btn)

    def _toggle_pgn(self, ruta):
        if ruta in self._pgn_selec:
            self._pgn_selec.discard(ruta)
            self._pgn_btns[ruta].background_color = UI_BG_ITEM
            self._pgn_btns[ruta].color = UI_TEXT_DARK
        else:
            self._pgn_selec.add(ruta)
            self._pgn_btns[ruta].background_color = UI_NAVY
            self._pgn_btns[ruta].color = UI_WHITE

    def _seleccionar(self, estado):
        self._pgn_selec.clear()
        for ruta, btn in self._pgn_btns.items():
            if estado:
                self._pgn_selec.add(ruta)
                btn.background_color = UI_NAVY
                btn.color = UI_WHITE
            else:
                btn.background_color = UI_BG_ITEM
                btn.color = UI_TEXT_DARK

    def _popup_elegir_base(self, *_):
        rutas = sorted(glob.glob(os.path.join(MODELOS_DIR_ML, '*.keras')))
        content = BoxLayout(orientation='vertical', spacing=8, padding=12)
        if not rutas:
            content.add_widget(Label(text="No hay modelos guardados todavía.",
                                     color=(1, 0.6, 0.6, 1)))
        else:
            scroll = ScrollView(
                size_hint=(1, 1),
                scroll_type=['bars', 'content'],
                bar_width=14,
                bar_color=(0.08, 0.10, 0.43, 0.9),
                bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
            )
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
            size_hint=(1, None), height=24,
            font_size=14, color=UI_TEXT_DARK,
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
            font_size=13, bold=True, color=UI_GOLD,
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
        self._sel_ruta      = None
        self._mod_btns      = {}
        self._selected_skin = DEFAULT_SKIN
        self._skin_btns_p   = {}

        with self.canvas.before:
            Color(*UI_BG_PAGE)
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
            background_normal='', background_color=UI_NAVY_MID,
            color=UI_WHITE, font_size=13, bold=True,
        )
        btn_back.bind(on_press=lambda _: setattr(self.manager, 'current', 'ml_menu'))
        back_row.add_widget(btn_back)
        back_row.add_widget(Label(
            text="Probar Modelo",
            font_size=32, bold=True, color=UI_NAVY,
            halign='center',
        ))
        back_row.add_widget(Widget(size_hint=(None, 1), width=90))
        outer.add_widget(back_row)

        # Contenedor central — fluido, se adapta al ancho disponible
        root = BoxLayout(orientation='vertical',
                         size_hint=(1, 1), spacing=14)

        root.add_widget(Label(
            text="Selecciona el modelo y el color que jugará contra el minimax:",
            font_size=17, bold=True, color=UI_TEXT_DARK,
            size_hint=(1, None), height=34,
            halign='center',
        ))

        # Lista de modelos
        mod_scroll = ScrollView(
            size_hint=(1, 1), do_scroll_x=False,
            scroll_type=['bars', 'content'],
            bar_width=14,
            bar_color=(0.08, 0.10, 0.43, 0.9),
            bar_inactive_color=(0.08, 0.10, 0.43, 0.45),
        )
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
            font_size=16, bold=True, color=UI_TEXT_DARK,
            size_hint=(None, 1), width=160,
            halign='right', valign='middle',
        ))
        self._btn_blancas = Button(
            text="Blancas",
            size_hint=(1, 1),
            background_normal='', background_color=UI_GREEN,
            color=UI_WHITE, font_size=14, bold=True,
        )
        self._btn_negras = Button(
            text="Negras",
            size_hint=(1, 1),
            background_normal='', background_color=UI_BG_ITEM,
            color=UI_TEXT_DARK, font_size=14,
        )
        self._btn_blancas.bind(on_press=lambda _: self._set_color(0))
        self._btn_negras.bind(on_press=lambda _: self._set_color(1))
        color_row.add_widget(self._btn_blancas)
        color_row.add_widget(self._btn_negras)
        root.add_widget(color_row)

        # ── Selector de skin ─────────────────────────────────────────────
        skin_row = BoxLayout(orientation='horizontal',
                             size_hint=(1, None), height=44, spacing=6)
        skin_row.add_widget(Label(
            text="Skin:",
            font_size=16, bold=True, color=UI_TEXT_DARK,
            size_hint=(None, 1), width=160,
            halign='right', valign='middle',
        ))
        for key, lbl_txt in [('clasico', 'Clásico'),
                             ('vocaloid', 'Vocaloid'),
                             ('shield', 'Shield')]:
            btn = Button(
                text=lbl_txt,
                background_normal='',
                background_color=(COLOR_SKIN_SELECTED
                                  if key == self._selected_skin
                                  else COLOR_SKIN_NORMAL),
                color=UI_WHITE,
                font_size=14, bold=True,
            )
            btn.bind(on_press=lambda _, k=key: self._select_skin(k))
            self._skin_btns_p[key] = btn
            skin_row.add_widget(btn)
        root.add_widget(skin_row)

        self._btn_probar = Button(
            text="Iniciar batalla  ML vs Minimax",
            size_hint=(1, None), height=64,
            background_normal='', background_color=UI_NAVY,
            color=UI_WHITE, font_size=20, bold=True,
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

        # Buscar ambos formatos: .keras (TF completo) y .tflite (ARM-friendly)
        rutas_keras  = sorted(glob.glob(os.path.join(MODELOS_DIR_ML, '*.keras')))
        rutas_tflite = sorted(glob.glob(os.path.join(MODELOS_DIR_ML, '*.tflite')))
        # Evitar duplicados: si hay un .tflite con el mismo nombre que un .keras,
        # mostrar solo el .tflite (es el que funciona en la Raspberry)
        nombres_tflite = {os.path.splitext(os.path.basename(r))[0] for r in rutas_tflite}
        rutas_keras_filtradas = [r for r in rutas_keras
                                 if os.path.splitext(os.path.basename(r))[0] not in nombres_tflite]
        rutas = rutas_tflite + rutas_keras_filtradas

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
                background_normal='', background_color=UI_BG_ITEM,
                color=UI_TEXT_DARK,
                font_size=16, bold=True, halign='left', valign='middle',
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
            b.background_color = UI_BG_ITEM
            b.color = UI_TEXT_DARK
        if ruta in self._mod_btns:
            self._mod_btns[ruta].background_color = UI_NAVY
            self._mod_btns[ruta].color = UI_WHITE
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
                # Borrar metadata asociada (puede ser .keras o .tflite)
                meta = ruta.replace('.keras', '_meta.json').replace('.tflite', '_meta.json')
                if os.path.exists(meta):
                    os.remove(meta)
            except Exception as e:
                print(f"Error al borrar: {e}")
            popup.dismiss()
            self._refrescar_modelos()
        btn_si.bind(on_press=_borrar)
        btn_no.bind(on_press=popup.dismiss)
        popup.open()

    def _select_skin(self, key):
        self._selected_skin = key
        for k, btn in self._skin_btns_p.items():
            btn.background_color = (COLOR_SKIN_SELECTED if k == key
                                    else COLOR_SKIN_NORMAL)

    def _set_color(self, turno):
        self._ml_turno = turno
        if turno == 0:
            self._btn_blancas.background_color = UI_GREEN
            self._btn_blancas.color = UI_WHITE
            self._btn_blancas.bold = True
            self._btn_negras.background_color  = UI_BG_ITEM
            self._btn_negras.color = UI_TEXT_DARK
            self._btn_negras.bold = False
        else:
            self._btn_negras.background_color  = UI_GREEN
            self._btn_negras.color = UI_WHITE
            self._btn_negras.bold = True
            self._btn_blancas.background_color = UI_BG_ITEM
            self._btn_blancas.color = UI_TEXT_DARK
            self._btn_blancas.bold = False

    def _probar(self, *_):
        if not self._sel_ruta:
            return
        app = App.get_running_app()
        app.ml_model_path = self._sel_ruta
        app.ml_turno      = self._ml_turno
        app.game_mode     = 'ml'
        assets_dir = SKINS[self._selected_skin]
        ruta       = self._sel_ruta
        game       = self.manager.get_screen('game')
        loading    = self.manager.get_screen('loading')

        from vista_screens_juego import cargar_motor_ml
        loading.start(
            "Cargando modelo",
            trabajo_hilo=lambda: cargar_motor_ml(ruta),
            trabajo_ui=lambda motor: game.setup(assets_dir, 'ml', motor_ml=motor),
            al_terminar=lambda: setattr(self.manager, 'current', 'game'),
            al_error=lambda e: setattr(self.manager, 'current', 'probar'),
        )
        self.manager.current = 'loading'
