"""
tensor_aprendizaje.py
=====================
Motor de ajedrez con aprendizaje automático.

Arquitectura dual inspirada en AlphaZero / LeelaChessZero:
  · Red residual convolucional sobre representacion (8x8x14) de la posicion
  · Cabeza de politica: distribucion sobre los 4096 posibles movimientos
  · Cabeza de valor:    evaluacion en [-1, +1] desde la perspectiva del jugador

Flujo:
  1. Cargar PGNs de partidas\\partidas aprendizaje
  2. Convertir posiciones a tensores con python-chess (soporta castling, e.p.)
  3. Entrenar red dual con entrenamiento supervisado
  4. Predecir movimiento en modo ML desde vistafrancisco.py

Configuracion en model_config.yaml (se crea automaticamente si no existe).

Uso rapido:
    motor = MotorML()
    motor.entrenar()
    mov, dist, val = motor.predecir(tablero, turno)
"""

import os
import glob
import json
import io
import logging
import numpy as np
import yaml
import chess
import chess.pgn
from tensorflow import keras
from datetime import datetime

# python-chess imprime warnings por variantes desconocidas; los suprimimos
logging.getLogger('chess.pgn').setLevel(logging.CRITICAL)

# ─────────────────────────────────────────────────────────────────────────────
# Rutas y constantes
# ─────────────────────────────────────────────────────────────────────────────

_DIR         = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(_DIR, 'model_config.yaml')
MODELOS_DIR  = os.path.join(_DIR, 'modelos_ml')
PARTIDAS_DIR = os.path.join(_DIR, 'partidas', 'partidas aprendizaje')

NUM_PLANOS    = 14         # 6 blancas + 6 negras + turno + n movimiento
TAMANO_POLICY = 64 * 64   # desde x hasta -> 4096 indices posibles

# python-chess y modeloraul usan la misma numeracion: a1=0 ... h8=63
# Los tipos de pieza tambien coinciden (PAWN=1 ... KING=6)
_TIPO_A_CANAL = {
    chess.PAWN:   0, chess.KNIGHT: 1, chess.BISHOP: 2,
    chess.ROOK:   3, chess.QUEEN:  4, chess.KING:   5,
}
_PIEZA_A_CANAL = {
     1:  0,  2:  1,  3:  2,  4:  3,  5:  4,  6:  5,   # blancas canal 0-5
    -1:  6, -2:  7, -3:  8, -4:  9, -5: 10, -6: 11,   # negras  canal 6-11
}


# ─────────────────────────────────────────────────────────────────────────────
# Clase principal
# ─────────────────────────────────────────────────────────────────────────────

class MotorML:
    """
    Motor de ajedrez basado en aprendizaje automatico.

    Entrenamiento supervisado desde archivos PGN:
      Politica: movimiento jugado en cada posicion de la partida
      Valor:    resultado final (+1 blancas, -1 negras, 0 empate)
    """

    def __init__(self):
        self.config  = self._cargar_config()
        self.modelo  = None          # keras.Model una vez construido/cargado
        os.makedirs(MODELOS_DIR, exist_ok=True)

    # ── Configuracion ─────────────────────────────────────────────────────────

    def _cargar_config(self):
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, encoding='utf-8') as f:
                return yaml.safe_load(f)
        cfg = self._config_default()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
        print(f"Configuracion creada en: {CONFIG_PATH}")
        return cfg

    @staticmethod
    def _config_default():
        return {
            'modelo': {
                'filtros':            128,
                'bloques_residuales': 4,
                'dropout':            0.3,
            },
            'entrenamiento': {
                'epochs':        50,
                'batch_size':    256,
                'learning_rate': 0.001,
                'validacion':    0.15,
                'paciencia':     8,
            },
            'rutas': {
                'partidas': PARTIDAS_DIR,
                'modelos':  MODELOS_DIR,
            },
        }

    # ── Codificacion del tablero ──────────────────────────────────────────────

    @staticmethod
    def chess_board_a_tensor(board, num_mov=0):
        """Convierte un python-chess Board en tensor (8, 8, 14).

        Canales 0-5:  piezas blancas (peon, caballo, alfil, torre, dama, rey)
        Canales 6-11: piezas negras
        Canal 12:     turno (1.0 = blancas mueven)
        Canal 13:     numero de movimiento normalizado a [0, 1]
        """
        planes = np.zeros((8, 8, NUM_PLANOS), dtype=np.float32)
        for sq in range(64):
            pieza = board.piece_at(sq)
            if pieza is None:
                continue
            canal_base = _TIPO_A_CANAL[pieza.piece_type]
            offset     = 0 if pieza.color == chess.WHITE else 6
            planes[sq // 8, sq % 8, canal_base + offset] = 1.0
        planes[:, :, 12] = 1.0 if board.turn == chess.WHITE else 0.0
        planes[:, :, 13] = min(num_mov / 100.0, 1.0)
        return planes

    @staticmethod
    def tablero_a_tensor(tablero, turno, num_mov=0):
        """Convierte el tablero de modeloraul (lista 64 ints) en tensor (8, 8, 14).
        Usado en inferencia desde vistafrancisco.py.
        """
        planes = np.zeros((8, 8, NUM_PLANOS), dtype=np.float32)
        for sq, pieza in enumerate(tablero):
            canal = _PIEZA_A_CANAL.get(pieza)
            if canal is not None:
                planes[sq // 8, sq % 8, canal] = 1.0
        planes[:, :, 12] = 1.0 if turno == 0 else 0.0
        planes[:, :, 13] = min(num_mov / 100.0, 1.0)
        return planes

    # ── Codificacion de movimientos ───────────────────────────────────────────

    @staticmethod
    def mov_a_idx(desde, hasta):
        return desde * 64 + hasta

    @staticmethod
    def idx_a_mov(idx):
        return idx // 64, idx % 64

    @staticmethod
    def _chess_move_a_idx(move):
        """Convierte un python-chess Move en indice de politica (from*64 + to)."""
        return move.from_square * 64 + move.to_square

    # ── Carga y parseo de PGNs ────────────────────────────────────────────────

    @staticmethod
    def _resultado_a_valor(result):
        """'1-0' -> 1.0,  '0-1' -> -1.0,  cualquier empate -> 0.0"""
        if result == '1-0':
            return 1.0
        if result == '0-1':
            return -1.0
        return 0.0

    def _procesar_pgn(self, ruta, reservorio, max_ej, callback_partida=None):
        """Lee un PGN aplicando reservoir sampling sobre 'reservorio' (lista in-place).

        Nunca supera max_ej elementos en reservorio — sin importar cuántas
        posiciones haya en el archivo.
        """
        import random as _rnd

        try:
            with open(ruta, encoding='utf-8', errors='ignore') as f:
                texto = f.read()
        except Exception:
            return

        lector    = io.StringIO(texto)
        n_partida = 0
        n_vistos  = 0   # total de ejemplos vistos (para reservoir sampling)

        while True:
            try:
                game = chess.pgn.read_game(lector)
            except Exception:
                continue
            if game is None:
                break

            variante = game.headers.get('Variant', 'Standard').strip().lower()
            if variante not in ('standard', 'chess', '', 'normal',
                                'from position', 'untimed'):
                continue

            try:
                valor_final = self._resultado_a_valor(
                    game.headers.get('Result', '*')
                )
                board   = game.board()
                num_mov = 0

                for move in game.mainline_moves():
                    tensor   = self.chess_board_a_tensor(board, num_mov)
                    move_idx = self._chess_move_a_idx(move)
                    valor    = valor_final if board.turn == chess.WHITE else -valor_final
                    ej       = (tensor, move_idx, valor)
                    n_vistos += 1

                    if len(reservorio) < max_ej:
                        reservorio.append(ej)
                    else:
                        # Reservoir sampling: reemplazar con probabilidad max_ej/n_vistos
                        j = _rnd.randint(0, n_vistos - 1)
                        if j < max_ej:
                            reservorio[j] = ej

                    board.push(move)
                    num_mov += 1

                n_partida += 1
                if callback_partida and n_partida % 500 == 0:
                    callback_partida(n_partida, len(reservorio))
            except Exception:
                pass

    def cargar_ejemplos_pgn(self, directorio=None, archivos=None,
                            callback=None, max_ejemplos=500_000):
        """Carga PGNs con reservoir sampling — nunca supera max_ejemplos en RAM."""
        if archivos is not None:
            lista = sorted(archivos)
        else:
            if directorio is None:
                directorio = self.config['rutas']['partidas']
            lista = sorted(glob.glob(os.path.join(directorio, '*.pgn')))

        if not lista:
            print("No se encontraron archivos .pgn")
            return []

        print(f"Cargando {len(lista)} archivo(s) PGN (max {max_ejemplos:,} pos.)...")
        reservorio = []
        for i, ruta in enumerate(lista):
            nombre = os.path.basename(ruta)
            if callback:
                callback(f"{nombre} — procesando...", len(lista), i + 1)

            def _cb(n, ej, _nom=nombre, _i=i):
                msg = f"  {_nom}: {n} partidas | {ej:,} pos. en muestra"
                print(msg)
                if callback:
                    callback(msg, len(lista), _i + 1)

            self._procesar_pgn(ruta, reservorio, max_ejemplos,
                               callback_partida=_cb)
            print(f"  [{i+1}/{len(lista)}] {nombre} — muestra acumulada: {len(reservorio):,}")
            if callback:
                callback(f"  ✓ {nombre} | muestra: {len(reservorio):,}", len(lista), i + 1)

        print(f"\nTotal de posiciones en muestra: {len(reservorio):,}")
        return reservorio

    def resumir_partidas(self, directorio=None):
        """Muestra un resumen de los PGNs disponibles sin procesarlos."""
        if directorio is None:
            directorio = self.config['rutas']['partidas']

        archivos = sorted(glob.glob(os.path.join(directorio, '*.pgn')))
        resumen  = {'archivos': len(archivos), 'detalle': []}

        for ruta in archivos:
            try:
                with open(ruta, encoding='utf-8', errors='ignore') as f:
                    texto = f.read()
                lector  = io.StringIO(texto)
                n       = 0
                while chess.pgn.read_game(lector) is not None:
                    n += 1
                resumen['detalle'].append({'archivo': os.path.basename(ruta),
                                           'partidas': n})
            except Exception as e:
                resumen['detalle'].append({'archivo': os.path.basename(ruta),
                                           'error': str(e)})

        total = sum(d.get('partidas', 0) for d in resumen['detalle'])
        resumen['total_partidas'] = total

        print(f"\nPGNs en: {directorio}")
        print(f"{'Archivo':<45} {'Partidas':>8}")
        print('-' * 55)
        for d in resumen['detalle']:
            if 'error' in d:
                print(f"  {d['archivo']:<43}  ERROR: {d['error']}")
            else:
                print(f"  {d['archivo']:<43}  {d['partidas']:>7}")
        print('-' * 55)
        print(f"  {'TOTAL':<43}  {total:>7}")
        return resumen

    # ── Arquitectura de la red ────────────────────────────────────────────────

    @staticmethod
    def _bloque_residual(x, filtros):
        """Bloque residual estilo AlphaZero (dos Conv + BatchNorm + skip)."""
        shortcut = x
        x = keras.layers.Conv2D(filtros, 3, padding='same', use_bias=False)(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.ReLU()(x)
        x = keras.layers.Conv2D(filtros, 3, padding='same', use_bias=False)(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Add()([x, shortcut])
        x = keras.layers.ReLU()(x)
        return x

    def construir_modelo(self):
        """Construye y compila la red dual (politica + valor)."""
        cfg     = self.config['modelo']
        filtros = cfg.get('filtros', 128)
        bloques = cfg.get('bloques_residuales', 4)
        dropout = cfg.get('dropout', 0.3)
        lr      = self.config['entrenamiento'].get('learning_rate', 0.001)

        entrada = keras.Input(shape=(8, 8, NUM_PLANOS), name='tablero')

        # Bloque convolucional inicial
        x = keras.layers.Conv2D(filtros, 3, padding='same', use_bias=False)(entrada)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.ReLU()(x)

        # Torre de bloques residuales
        for _ in range(bloques):
            x = self._bloque_residual(x, filtros)

        # ── Cabeza de politica ────────────────────────────────────────────
        p = keras.layers.Conv2D(2, 1, padding='same', use_bias=False)(x)
        p = keras.layers.BatchNormalization()(p)
        p = keras.layers.ReLU()(p)
        p = keras.layers.Flatten()(p)
        p = keras.layers.Dense(TAMANO_POLICY, activation='softmax',
                               name='policy')(p)

        # ── Cabeza de valor ───────────────────────────────────────────────
        v = keras.layers.Conv2D(1, 1, padding='same', use_bias=False)(x)
        v = keras.layers.BatchNormalization()(v)
        v = keras.layers.ReLU()(v)
        v = keras.layers.Flatten()(v)
        v = keras.layers.Dense(256, activation='relu')(v)
        if dropout > 0:
            v = keras.layers.Dropout(dropout)(v)
        v = keras.layers.Dense(1, activation='tanh', name='value')(v)

        modelo = keras.Model(inputs=entrada, outputs=[p, v])
        modelo.compile(
            optimizer=keras.optimizers.Adam(learning_rate=lr),
            loss={
                'policy': 'sparse_categorical_crossentropy',
                'value':  'mean_squared_error',
            },
            loss_weights={'policy': 1.0, 'value': 1.0},
            metrics={
                'policy': 'accuracy',
                'value':  'mae',
            },
        )
        return modelo

    # ── Entrenamiento ─────────────────────────────────────────────────────────

    def entrenar(self, directorio=None, archivos=None,
                 callback_carga=None, callback_progreso=None):
        """Pipeline completo: PGNs -> tensores -> entrenamiento -> guardado.

        archivos          : lista de rutas PGN especificas (opcional).
        callback_carga    : fn(nombre, total, proc) — progreso de carga de archivos.
        callback_progreso : fn(epoch, total, loss)  — progreso por epoca.
        Retorna el objeto History de Keras, o None si no hay datos.
        """
        ejemplos = self.cargar_ejemplos_pgn(directorio=directorio,
                                            archivos=archivos,
                                            callback=callback_carga)
        if not ejemplos:
            return None

        print(f"\nPreparando arrays ({len(ejemplos):,} posiciones)...")
        # sparse_categorical_crossentropy: Y_policy es un vector de índices enteros
        # (N,) en lugar de one-hot (N, 4096) — 4096x menos memoria
        X        = np.stack([e[0] for e in ejemplos])          # (N, 8, 8, 14)
        Y_policy = np.array([e[1] for e in ejemplos],
                            dtype=np.int32)                    # (N,)
        Y_value  = np.array([[e[2]] for e in ejemplos], dtype=np.float32)

        cfg = self.config['entrenamiento']

        if self.modelo is None:
            print("Construyendo modelo...")
            self.modelo = self.construir_modelo()
            self.modelo.summary()

        callbacks_lista = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=cfg.get('paciencia', 8),
                restore_best_weights=True,
                verbose=1,
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=4,
                min_lr=1e-5, verbose=1,
            ),
        ]

        if callback_progreso:
            total_epochs = cfg.get('epochs', 50)

            class _CB(keras.callbacks.Callback):
                def on_epoch_end(self_, epoch, logs=None):
                    loss = logs.get('val_loss', logs.get('loss', 0.0))
                    callback_progreso(epoch + 1, total_epochs, loss)

            callbacks_lista.append(_CB())

        print("\nIniciando entrenamiento...")
        history = self.modelo.fit(
            X,
            {'policy': Y_policy, 'value': Y_value},
            epochs=cfg.get('epochs', 50),
            batch_size=cfg.get('batch_size', 256),
            validation_split=cfg.get('validacion', 0.15),
            callbacks=callbacks_lista,
            verbose=1,
        )

        return history

    # ── Persistencia ──────────────────────────────────────────────────────────

    def guardar_con_nombre(self, nombre):
        """Guarda el modelo con nombre personalizado. Retorna la ruta."""
        import re
        nombre_clean = re.sub(r'[^\w\-]', '_', nombre.strip()) or 'modelo'
        ruta = os.path.join(MODELOS_DIR, f'{nombre_clean}.keras')
        if os.path.exists(ruta):
            i = 2
            while os.path.exists(
                    os.path.join(MODELOS_DIR, f'{nombre_clean}_{i}.keras')):
                i += 1
            ruta = os.path.join(MODELOS_DIR, f'{nombre_clean}_{i}.keras')
        self.modelo.save(ruta)
        meta = {
            'nombre':      nombre,
            'timestamp':   datetime.now().strftime('%Y%m%d_%H%M%S'),
            'config':      self.config,
            'policy_size': TAMANO_POLICY,
        }
        with open(ruta.replace('.keras', '_meta.json'),
                  'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        return ruta

    # ── Inferencia ────────────────────────────────────────────────────────────

    def predecir_con_minimax(self, tablero, turno, num_mov=0, profundidad=2):
        """
        Modo híbrido: usa la policy de la red para ordenar los movimientos
        antes de pasarlos al Minimax. Esto combina lo mejor de ambos mundos:
        - La red aporta intuición posicional
        - El Minimax corrige errores tácticos

        Complejidad asintotica (ver analizar_complejidad()):
          Red:     O(B·F² + F·P)  — forward pass fijo, no crece con la posicion
          Orden:   O(M·log M)     — M movimientos legales (M ≤ 218)
          Minimax: O(k·b^(d-1))   — k candidatos top-policy, b ramas, d-1 niv.
          TOTAL:   O(B·F² + k·b^(d-1))
        """
        from modeloraul import _minimax, _movimientos_legales, hacer_movimiento, _search_stats

        if self.modelo is None:
            raise RuntimeError("Modelo no cargado.")

        # 1. Obtener distribución de política de la red
        tensor = self.tablero_a_tensor(tablero, turno, num_mov)
        X = tensor[np.newaxis, ...]
        policy_vec, value_arr = self.modelo.predict(X, verbose=0)
        policy_vec = policy_vec[0]

        # 2. Obtener movimientos legales y ordenarlos por probabilidad ML
        legales = _movimientos_legales(tablero, turno)
        if not legales:
            return None, {}, float(value_arr[0, 0])

        # Ordenar de mayor a menor probabilidad según la policy  O(M log M)
        legales_ordenados = sorted(
            legales,
            key=lambda mov: float(policy_vec[self.mov_a_idx(*mov)]),
            reverse=True
        )

        # 3. Pasar los mejores N movimientos al Minimax (move ordering)
        candidatos = legales_ordenados[:12]

        mejor = None
        if turno == 0:  # blancas: maximizar
            mejor_val = float('-inf')
            alpha = float('-inf')
            for desde, hasta in candidatos:
                nuevo = tablero[:]
                hacer_movimiento(nuevo, desde, hasta)
                val = _minimax(nuevo, profundidad - 1, 1, alpha, float('inf'))
                if val > mejor_val:
                    mejor_val = val
                    mejor = (desde, hasta)
                alpha = max(alpha, mejor_val)
        else:  # negras: minimizar
            mejor_val = float('inf')
            beta = float('inf')
            for desde, hasta in candidatos:
                nuevo = tablero[:]
                hacer_movimiento(nuevo, desde, hasta)
                val = _minimax(nuevo, profundidad - 1, 0, float('-inf'), beta)
                if val < mejor_val:
                    mejor_val = val
                    mejor = (desde, hasta)
                beta = min(beta, mejor_val)

        dist = {(d, h): float(policy_vec[self.mov_a_idx(d, h)]) for d, h in legales}
        return mejor, dist, float(value_arr[0, 0])

    predecir = predecir_con_minimax

    def analizar_complejidad(self, profundidad=2, k_candidatos=12,
                             b_medio=30, m_movimientos=30):
        """Imprime el analisis de complejidad asintotica de la inferencia ML.

        Variables:
          B = bloques residuales,  F = filtros,  P = tamano politica (4096)
          M = movimientos legales en la posicion  (max 218, prom ~30)
          k = candidatos pasados al minimax (top-k de la policy)
          d = profundidad del minimax hibrido
          b = factor de ramificacion promedio

        Retorna dict con los numeros calculados.
        """
        cfg = self.config['modelo']
        F   = cfg.get('filtros', 128)
        B   = cfg.get('bloques_residuales', 4)
        P   = TAMANO_POLICY          # 4096
        S   = 64                     # 8×8 fijo
        C   = NUM_PLANOS             # 14 canales
        d, k, b, M = profundidad, k_candidatos, b_medio, m_movimientos

        # FLOPs aproximados de cada fase de la red
        flops_conv_ini   = S * C * F * 9                  # Conv2D(F,3x3) entrada
        flops_bloque     = 2 * S * F * F * 9              # dos Conv2D por bloque res.
        flops_policy     = S * F * 2 + S * 2 * P          # Conv 1x1 + Dense(4096)
        flops_value      = S * F + S * 256 + 256          # Conv 1x1 + Dense(256) + Dense(1)
        flops_red        = flops_conv_ini + B * flops_bloque + flops_policy + flops_value

        nodos_hibrido    = k * (b ** (d - 1)) if d > 1 else k
        nodos_minimax_p  = b ** d
        nodos_alpha_beta = int(b ** (d / 2))

        lineas = [
            "=" * 62,
            "  Complejidad de inferencia ML — por decision",
            "=" * 62,
            f"  Arquitectura : B={B} bloques residuales, F={F} filtros, P={P}",
            f"  Busqueda     : d={d} prof., k={k} candidatos, b≈{b} ramas",
            "",
            f"  {'Fase':<32} {'Complejidad':<18} FLOPs aprox",
            "  " + "-" * 58,
            f"  {'Codificacion tablero':<32} {'O(1)':<18} {S} casillas fijas",
            f"  {'Conv inicial':<32} {'O(S·C·F·9)':<18} {flops_conv_ini:>10,}",
            f"  {f'Torre residual ({B} bloques)':<32} {'O(B·F²·S·9)':<18} {B*flops_bloque:>10,}",
            f"  {'Cabeza policy':<32} {'O(S·F·P)':<18} {flops_policy:>10,}",
            f"  {'Cabeza valor':<32} {'O(S·F)':<18} {flops_value:>10,}",
            f"  {'Red total (forward pass)':<32} {'O(B·F²+F·P)':<18} {flops_red:>10,}",
            f"  {'Ordenar movimientos':<32} {'O(M·log M)':<18} M≤218, prom M≈{M}",
            f"  {f'Minimax hibrido (top-{k})':<32} {'O(k·b^(d-1))':<18} {nodos_hibrido:>10,} nodos",
            "  " + "-" * 58,
            f"  {'TOTAL':<32} O(B·F² + k·b^(d-1))",
            "",
            "  Comparacion con Minimax puro:",
            f"  {'Minimax puro  d='+str(d)+':':<32} O(b^d)        {nodos_minimax_p:>8,} nodos",
            f"  {'Alpha-beta    d='+str(d)+':':<32} O(b^(d/2))    {nodos_alpha_beta:>8,} nodos (mejor caso)",
            f"  {'ML hibrido    d='+str(d)+',k='+str(k)+':':<32} O(k·b^(d-1)) {nodos_hibrido:>8,} nodos",
            "",
            "  Nota: la red es O(1) respecto al estado del tablero",
            "  (entrada siempre 8x8x14 fija). La ganancia real del",
            "  modo hibrido es reducir la raiz del arbol de b^d",
            "  a k·b^(d-1), con k << b.",
            "=" * 62,
        ]
        for linea in lineas:
            print(linea)

        return {
            'flops_red':              flops_red,
            'nodos_hibrido':          nodos_hibrido,
            'nodos_minimax_puro':     nodos_minimax_p,
            'nodos_alphabeta_mejor':  nodos_alpha_beta,
            'complejidad':            f'O(B·F² + k·b^(d-1))',
        }

    # ── Persistencia ──────────────────────────────────────────────────────────

    def guardar_modelo(self):
        """Guarda el modelo en formato .keras + metadatos JSON.
        Retorna la ruta del archivo guardado.
        """
        ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
        ruta = os.path.join(MODELOS_DIR, f'motor_ml_{ts}.keras')
        self.modelo.save(ruta)

        meta = {
            'timestamp':   ts,
            'config':      self.config,
            'input_shape': list(self.modelo.input_shape[1:]),
            'policy_size': TAMANO_POLICY,
        }
        with open(ruta.replace('.keras', '_meta.json'),
                  'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return ruta

    def cargar_modelo(self, ruta=None):
        """Carga el modelo mas reciente (o la ruta indicada).
        Retorna True si se cargo correctamente.
        """
        if ruta is None:
            archivos = sorted(
                glob.glob(os.path.join(MODELOS_DIR, '*.keras'))
            )
            if not archivos:
                print("No hay modelos entrenados en:", MODELOS_DIR)
                return False
            ruta = archivos[-1]

        try:
            self.modelo = keras.models.load_model(ruta)
            print(f"Modelo cargado: {os.path.basename(ruta)}")
            return True
        except Exception as e:
            print(f"Error al cargar modelo: {e}")
            return False

    # ── Informacion ───────────────────────────────────────────────────────────

    def info(self):
        """Devuelve un dict con el estado actual del motor ML."""
        archivos = sorted(glob.glob(os.path.join(MODELOS_DIR, '*.keras')))
        return {
            'modelo_cargado':      self.modelo is not None,
            'modelos_disponibles': len(archivos),
            'ultimo_modelo':       os.path.basename(archivos[-1])
                                   if archivos else None,
            'config':              self.config,
            'partidas_dir':        self.config['rutas']['partidas'],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton global (lazy)
# ─────────────────────────────────────────────────────────────────────────────

_instancia = None


def obtener_motor():
    """Instancia global del motor ML. Carga el ultimo modelo si existe."""
    global _instancia
    if _instancia is None:
        _instancia = MotorML()
        _instancia.cargar_modelo()
    return _instancia


# ─────────────────────────────────────────────────────────────────────────────
# Ejecucion directa: entrenar o mostrar info
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    motor = MotorML()

    if len(sys.argv) > 1 and sys.argv[1] == 'info':
        motor.resumir_partidas()
        print()
        print(motor.info())
    else:
        motor.entrenar()
