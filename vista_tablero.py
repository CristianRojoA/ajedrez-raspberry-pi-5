from vista_config import *
from modeloraul import guardar_csv, guardar_metrica_turno, reset_metricas


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
        self._csv_generado  = False

        self._replay_moves  = None   # list[(desde,hasta)] o None → modo normal
        self._replay_idx    = 0
        self._coord_cache   = {}
        self._motor_ml      = None   # MotorML si se juega en modo ML
        self._num_mov_ml    = 0
        self._motor_ml_turno = None  # 0=ML juega blancas, 1=negras, None=ambos

        self._captured_by_white = []  # piezas negras capturadas (esquina sup-der)
        self._captured_by_black = []  # piezas blancas capturadas (esquina inf-izq)

        self.bind(pos=self._draw, size=self._draw)
        self._draw()
        self._pending_event = Clock.schedule_once(self._next_move, 1.0)

    # ── Assets ───────────────────────────────────────────────────────────────

    def _rebuild_captures(self, up_to_idx=-1):
        self._captured_by_white = []
        self._captured_by_black = []
        entries = self._history[:up_to_idx + 1] if up_to_idx >= 0 else self._history
        for entry in entries:
            p = entry.get('capturada', 0)
            if p < 0:
                self._captured_by_white.append(p)
            elif p > 0:
                self._captured_by_black.append(p)

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
        self._rebuild_captures()
        if not self._anim_active:
            self._pending_event = Clock.schedule_once(self._next_move, MOVE_DELAY)

    def replay_move(self, idx):
        if idx < 0 or idx >= len(self._history):
            return
        if self._anim_active and self._anim_event:
            self._anim_event.cancel()
            self._anim_active = False

        self._reviewing = True
        self._rebuild_captures(idx)
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
        if self._game_over:
            return

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
            
            if not self._csv_generado:
                guardar_csv()
                self._csv_generado = True
            
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
            
            if not self._csv_generado:
                guardar_csv()
                self._csv_generado = True
                
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
                top3  = sorted(dist.items(), key=lambda x: -x[1])[:3] if dist else []
                stats = {
                    'tipo':        'ml',
                    'valor':       round(valor, 3),
                    'confianza':   conf,
                    'num_legales': len(dist),
                    'dist_top3':   [(idx_to_sq(d), idx_to_sq(h), round(p * 100, 1))
                                    for (d, h), p in top3],
                }
            except Exception as e:
                print(f"Error motor ML: {e}")
                return
        else:
            reset_metricas()
            move = elegir_movimiento(self.tablero, self.turno, historial=self._historial)
            stats = get_last_stats()
            if move is None:
                return
            guardar_metrica_turno(len(self._history))

        desde, hasta  = move
        board_before  = self.tablero[:]
        pieza_volando = self.tablero[desde]
        capturada     = board_before[hasta]

        hacer_movimiento(self.tablero, desde, hasta)
        pieza_final = self.tablero[hasta]
        board_after = self.tablero[:]

        if capturada < 0:
            self._captured_by_white.append(capturada)
        elif capturada > 0:
            self._captured_by_black.append(capturada)

        move_idx = len(self._history)
        self._history.append({
            'board_before':  board_before,
            'board_after':   board_after,
            'desde':         desde,
            'hasta':         hasta,
            'pieza_volando': pieza_volando,
            'pieza_final':   pieza_final,
            'capturada':     capturada,
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
            if jaque:
                en_jaque = "Negras" if self.turno == 0 else "Blancas"
                self.on_status_cb(f"¡{en_jaque} en jaque!")
            else:
                self.on_status_cb("")

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

            # ── Piezas capturadas ─────────────────────────────────────────
            _cgap    = 4                          # separación entre columnas
            _ideal   = min(sq * 2 // 3, 60)      # tamaño ideal de icono

            def _draw_caps(pieces, area_x, area_w, upward):
                if area_w < 16:
                    return
                # determinar número de columnas según espacio disponible
                nc = 2 if area_w >= 2 * _ideal + _cgap + 6 else 1
                if nc == 2:
                    cp = min(_ideal, (area_w - 6 - _cgap) // 2)
                    tw = 2 * cp + _cgap
                else:
                    cp = min(_ideal, area_w - 6)
                    tw = cp
                step = cp + max(2, cp // 8)
                sx   = area_x + (area_w - tw) // 2
                for k, piece in enumerate(pieces):
                    col_i = k % nc
                    row_i = k // nc
                    px_c  = sx + col_i * (cp + _cgap)
                    py_c  = (oy + row_i * step if upward
                             else oy + board_px - (row_i + 1) * step)
                    if upward and py_c + cp > oy + board_px:
                        break
                    if not upward and py_c < oy:
                        break
                    _n = PIECE_NAMES.get(piece)
                    if _n and _n in self.textures:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=self.textures[_n],
                                  pos=(px_c, py_c), size=(cp, cp))

            # Inf-izq ↑ : piezas blancas comidas (capturadas por negras)
            left_w  = max(0, (ox - frame) - bx)
            _draw_caps(sorted(self._captured_by_black, key=lambda p: abs(p)),
                       bx, left_w, upward=True)

            # Sup-der ↓ : piezas negras comidas (capturadas por blancas)
            right_x = ox + board_px + frame
            right_w = max(0, (bx + w) - right_x)
            _draw_caps(sorted(self._captured_by_white, key=lambda p: abs(p)),
                       right_x, right_w, upward=False)

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