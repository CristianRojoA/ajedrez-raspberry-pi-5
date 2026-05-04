"""Lógica de exportación/importación de partidas en formato PGN.
Las partidas se guardan en PARTIDAS_DIR con nombre YYYYMMDD_HHMMSS.pgn
"""

import os
import re
from datetime import datetime

from modeloraul import (get_valid_moves, get_all_moves, hacer_movimiento,
                        esta_en_jaque, estado_juego, inicializar_ajedrez)

PARTIDAS_DIR = r"D:\ajedrez_dya\chees\partidas"

_LETRA = {1: '', 2: 'N', 3: 'B', 4: 'R', 5: 'Q', 6: 'K'}
_COLS  = "abcdefgh"


def _sq(idx):
    return f"{_COLS[idx % 8]}{idx // 8 + 1}"


def mover_a_san(board_before, desde, hasta, board_after):
    """Convierte un movimiento (índices) al texto SAN estándar de PGN."""
    pieza  = board_before[desde]
    abs_p  = abs(pieza)
    blanca = pieza > 0
    turno  = 0 if blanca else 1

    # En passant: peón se mueve en diagonal pero casilla destino vacía
    es_captura = (board_before[hasta] != 0 or
                  (abs_p == 1 and desde % 8 != hasta % 8))

    # Promoción (siempre a reina por cómo funciona el motor)
    promocion = ''
    if abs_p == 1:
        if (blanca and hasta // 8 == 7) or (not blanca and hasta // 8 == 0):
            promocion = '=Q'

    if abs_p == 1:
        san = (f"{_COLS[desde % 8]}x{_sq(hasta)}{promocion}"
               if es_captura else f"{_sq(hasta)}{promocion}")
    else:
        # Desambiguación: otras piezas iguales que también podrían ir a 'hasta'
        ambiguos = [
            i for i in range(64)
            if i != desde
            and board_before[i] == pieza
            and hasta in get_valid_moves(board_before, i)
        ]
        desambig = ''
        if ambiguos:
            same_col = [i for i in ambiguos if i % 8 == desde % 8]
            same_row = [i for i in ambiguos if i // 8 == desde // 8]
            if not same_col:
                desambig = _COLS[desde % 8]
            elif not same_row:
                desambig = str(desde // 8 + 1)
            else:
                desambig = _sq(desde)

        cap = 'x' if es_captura else ''
        san = f"{_LETRA[abs_p]}{desambig}{cap}{_sq(hasta)}"

    # Sufijo jaque / jaque mate
    opp = 1 - turno
    if esta_en_jaque(board_after, opp):
        san += '#' if estado_juego(board_after, opp) == 'JAQUE_MATE' else '+'

    return san


def _stats_comment(stats):
    """Serializa stats como comentario PGN { DAA n=… p=… ch=… d=… mr=… cd=… }."""
    if not stats:
        return ''
    return (
        f'{{ DAA'
        f' n={stats.get("nodos", 0)}'
        f' p={stats.get("podas", 0)}'
        f' ch={stats.get("cache_hits", 0)}'
        f' d={stats.get("profundidad", 2)}'
        f' mr={stats.get("movimientos_raiz", 0)}'
        f' cd={stats.get("candidatos_disponibles", 0)}'
        f' }}'
    )


def historial_a_pgn(historial, resultado='*'):
    """Convierte la lista de movimientos al texto PGN con stats embebidos."""
    fecha = datetime.now().strftime('%Y.%m.%d')
    header = (
        f'[Event "Partida IA vs IA"]\n'
        f'[Site "Ajedrez Kivy"]\n'
        f'[Date "{fecha}"]\n'
        f'[White "Motor Blancas"]\n'
        f'[Black "Motor Negras"]\n'
        f'[Result "{resultado}"]\n\n'
    )

    # Una línea por par de movimientos: "1. e4 { DAA … } e5 { DAA … }"
    lines = []
    for i in range(0, len(historial), 2):
        num = i // 2 + 1
        w   = historial[i]
        w_san = mover_a_san(w['board_before'], w['desde'], w['hasta'], w['board_after'])
        w_cmt = _stats_comment(w.get('stats', {}))

        parts = [f"{num}.", w_san]
        if w_cmt:
            parts.append(w_cmt)

        if i + 1 < len(historial):
            b     = historial[i + 1]
            b_san = mover_a_san(b['board_before'], b['desde'], b['hasta'], b['board_after'])
            b_cmt = _stats_comment(b.get('stats', {}))
            parts.append(b_san)
            if b_cmt:
                parts.append(b_cmt)

        lines.append(' '.join(parts))

    lines.append(resultado)
    return header + '\n'.join(lines) + '\n'


# ── Lectura / parser PGN ──────────────────────────────────────────────────────

_PIEZA_MAP = {'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6}


def _legales(tablero, turno):
    """Movimientos legales usando sólo la API pública de modeloraul."""
    resultado = []
    for desde, hasta in get_all_moves(tablero, turno):
        copia = tablero[:]
        hacer_movimiento(copia, desde, hasta)
        if not esta_en_jaque(copia, turno):
            resultado.append((desde, hasta))
    return resultado


def san_a_movimiento(tablero, turno, san):
    """Convierte una cadena SAN a (desde, hasta) buscando entre los movimientos
    legales de la posición dada. Retorna None si no puede resolverlo."""
    # Limpiar marcadores que no afectan al destino
    s = san.replace('+', '').replace('#', '').replace('x', '').strip()

    # Enroque: no soportado por el motor, devolvemos None
    if s.startswith('O') or s.startswith('0'):
        return None

    # Promoción
    if '=' in s:
        s = s[:s.index('=')]

    legales = _legales(tablero, turno)

    if s and s[0].isupper():
        # ── Pieza (N, B, R, Q, K) ─────────────────────────────────────────
        abs_p = _PIEZA_MAP.get(s[0])
        if abs_p is None:
            return None
        pieza = abs_p if turno == 0 else -abs_p
        rest  = s[1:]                        # p.ej. "bd2" → rest="bd2", dest="d2"

        dest_sq  = rest[-2:]
        hasta    = (int(dest_sq[1]) - 1) * 8 + _COLS.index(dest_sq[0])
        disambig = rest[:-2]                 # '' | 'b' | '2' | 'b2'

        candidatos = [(d, h) for d, h in legales
                      if h == hasta and tablero[d] == pieza]

        for ch in disambig:
            if ch in _COLS:
                candidatos = [(d, h) for d, h in candidatos
                              if d % 8 == _COLS.index(ch)]
            elif ch.isdigit():
                candidatos = [(d, h) for d, h in candidatos
                              if d // 8 == int(ch) - 1]
    else:
        # ── Peón ──────────────────────────────────────────────────────────
        pieza   = 1 if turno == 0 else -1
        dest_sq = s[-2:]
        hasta   = (int(dest_sq[1]) - 1) * 8 + _COLS.index(dest_sq[0])

        candidatos = [(d, h) for d, h in legales
                      if h == hasta and tablero[d] == pieza]

        # Captura: el primer char indica la columna de origen
        if len(s) > 2 and s[0] in _COLS and s[0] != dest_sq[0]:
            fc = _COLS.index(s[0])
            candidatos = [(d, h) for d, h in candidatos if d % 8 == fc]

    return candidatos[0] if candidatos else None


_DAA_RE     = re.compile(
    r'\{ DAA n=(\d+) p=(\d+) ch=(\d+) d=(\d+) mr=(\d+) cd=(\d+) \}'
)
_RESULTADOS = {'1-0', '0-1', '1/2-1/2', '*'}


def leer_pgn_completo(ruta):
    """Lee un PGN y devuelve lista de (san, stats_dict).
    Si el archivo fue guardado por este motor, stats_dict contiene los datos DAA;
    de lo contrario es un dict vacío."""
    with open(ruta, encoding='utf-8') as f:
        text = f.read()

    # Eliminar cabeceras
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Extraer stats DAA en orden de aparición antes de borrar comentarios
    daa_stats = [
        {
            'nodos':                  int(m.group(1)),
            'podas':                  int(m.group(2)),
            'cache_hits':             int(m.group(3)),
            'profundidad':            int(m.group(4)),
            'movimientos_raiz':       int(m.group(5)),
            'candidatos_disponibles': int(m.group(6)),
        }
        for m in _DAA_RE.finditer(text)
    ]

    # Eliminar todos los comentarios y variantes para obtener SAN limpio
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'\([^)]*\)', '', text)

    san_list = []
    for tok in text.split():
        if tok in _RESULTADOS:
            break
        if re.match(r'^\d+\.+$', tok):
            continue
        san_list.append(tok)

    return [
        (san, daa_stats[i] if i < len(daa_stats) else {})
        for i, san in enumerate(san_list)
    ]


def pgn_a_movimientos(ruta):
    """Convierte un PGN en lista de (desde, hasta, stats) para el modo replay."""
    san_con_stats = leer_pgn_completo(ruta)
    tablero       = inicializar_ajedrez()
    turno         = 0
    movs          = []

    for san, stats in san_con_stats:
        mov = san_a_movimiento(tablero, turno, san)
        if mov is None:
            break
        movs.append((mov[0], mov[1], stats))
        hacer_movimiento(tablero, mov[0], mov[1])
        turno = 1 - turno

    return movs


# ── Escritura PGN ─────────────────────────────────────────────────────────────

def guardar_partida(historial, resultado='*', nombre=None):
    """Escribe el PGN en PARTIDAS_DIR. Retorna la ruta del archivo creado.

    nombre: nombre base sin extensión. Si es None se usa YYYYMMDD_HHMMSS.
    Si ya existe un archivo con ese nombre se añade un sufijo _2, _3, etc.
    """
    os.makedirs(PARTIDAS_DIR, exist_ok=True)

    base = nombre if nombre else datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta = os.path.join(PARTIDAS_DIR, base + '.pgn')

    # Evitar sobreescribir si el nombre ya existe
    if os.path.exists(ruta):
        n = 2
        while os.path.exists(os.path.join(PARTIDAS_DIR, f"{base}_{n}.pgn")):
            n += 1
        ruta = os.path.join(PARTIDAS_DIR, f"{base}_{n}.pgn")

    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(historial_a_pgn(historial, resultado))
    return ruta
