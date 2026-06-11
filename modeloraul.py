import random
import time
import csv
import os
import gc

from datetime import datetime

# Códigos: Torre=4, Caballo=2, Alfil=3, Dama=5, Rey=6, Peón=1  (negativos = negras)

def inicializar_ajedrez():
    tablero = [0] * 64

    tablero[0], tablero[7]   =  4,  4
    tablero[56], tablero[63] = -4, -4

    tablero[1], tablero[6]   =  2,  2
    tablero[57], tablero[62] = -2, -2

    tablero[2], tablero[5]   =  3,  3
    tablero[58], tablero[61] = -3, -3

    tablero[3],  tablero[59] =  5, -5
    tablero[4],  tablero[60] =  6, -6

    for i in range(8):
        tablero[8  + i] =  1
        tablero[48 + i] = -1

    return tablero


def imprimir_ajedrez(tablero):
    for i in range(64):
        print(f"{tablero[i]:2d}|", end="")
        if (i + 1) % 8 == 0:
            print()
    print()


# ── Utilidades ────────────────────────────────────────────────────────────────

def _en_tablero(r, c):
    return 0 <= r <= 7 and 0 <= c <= 7

def hash_tablero(tablero):
    return tuple(tablero)


# ── Movimientos válidos (API pública: índices) ────────────────────────────────

def get_valid_moves(tablero, desde):
    """Retorna lista de índices destino válidos para la pieza en 'desde'."""
    pieza = tablero[desde]
    if pieza == 0:
        return []

    r, c   = desde // 8, desde % 8
    blanca = pieza > 0
    abs_p  = abs(pieza)
    movs   = []

    def es_propia(idx):
        t = tablero[idx]
        return (t > 0) if blanca else (t < 0)

    def puede_ir(nr, nc):
        return _en_tablero(nr, nc) and not es_propia(nr * 8 + nc)

    if abs_p == 1:  # Peón
        dir_         = 1 if blanca else -1
        fila_inicial = 1 if blanca else 6
        nr = r + dir_
        if _en_tablero(nr, c) and tablero[nr * 8 + c] == 0:
            movs.append(nr * 8 + c)
            if r == fila_inicial:
                nr2 = r + 2 * dir_
                if tablero[nr2 * 8 + c] == 0:
                    movs.append(nr2 * 8 + c)
        for dc in (-1, 1):
            nc = c + dc
            if _en_tablero(nr, nc):
                t = tablero[nr * 8 + nc]
                if (blanca and t < 0) or (not blanca and t > 0):
                    movs.append(nr * 8 + nc)

    elif abs_p == 2:  # Caballo
        for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
            nr, nc = r + dr, c + dc
            if puede_ir(nr, nc):
                movs.append(nr * 8 + nc)

    elif abs_p in (3, 4, 5):  # Alfil / Torre / Reina
        dirs = []
        if abs_p in (3, 5):
            dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
        if abs_p in (4, 5):
            dirs += [(-1,0),(1,0),(0,-1),(0,1)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while _en_tablero(nr, nc):
                if es_propia(nr * 8 + nc):
                    break
                movs.append(nr * 8 + nc)
                if tablero[nr * 8 + nc] != 0:
                    break
                nr, nc = nr + dr, nc + dc

    elif abs_p == 6:  # Rey
        for dr, dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nr, nc = r + dr, c + dc
            if puede_ir(nr, nc):
                movs.append(nr * 8 + nc)

    return movs


def get_all_moves(tablero, turno):
    """Retorna lista de (desde, hasta) para todos los movimientos pseudo-legales del turno."""
    movs = []
    for i in range(64):
        p = tablero[i]
        if (turno == 0 and p > 0) or (turno == 1 and p < 0):
            for dest in get_valid_moves(tablero, i):
                movs.append((i, dest))
    return movs


def hacer_movimiento(tablero, desde, hasta):
    """Ejecuta el movimiento en-lugar. Promoción automática de peón a reina."""
    tablero[hasta] = tablero[desde]
    tablero[desde] = 0
    if tablero[hasta] ==  1 and hasta // 8 == 7:
        tablero[hasta] =  5
    elif tablero[hasta] == -1 and hasta // 8 == 0:
        tablero[hasta] = -5


# ── Jaque, legalidad y estado de partida ─────────────────────────────────────

def esta_en_jaque(tablero, turno):
    """True si el rey del turno indicado está bajo ataque."""
    rey = 6 if turno == 0 else -6
    pos_rey = next((i for i in range(64) if tablero[i] == rey), -1)
    if pos_rey == -1:
        return True
    rival = 1 - turno
    return any(
        pos_rey in get_valid_moves(tablero, i)
        for i in range(64)
        if (rival == 0 and tablero[i] > 0) or (rival == 1 and tablero[i] < 0)
    )


def _movimientos_legales(tablero, turno):
    """Movimientos que no dejan al propio rey en jaque."""
    legales = []
    for desde, hasta in get_all_moves(tablero, turno):
        nuevo = tablero[:]
        hacer_movimiento(nuevo, desde, hasta)
        if not esta_en_jaque(nuevo, turno):
            legales.append((desde, hasta))
    return legales


def estado_juego(tablero, turno):
    """Retorna 'NORMAL', 'JAQUE_MATE' o 'TABLAS'."""
    if not _movimientos_legales(tablero, turno):
        return "JAQUE_MATE" if esta_en_jaque(tablero, turno) else "TABLAS"
    return "NORMAL"


# ── Evaluación estática ───────────────────────────────────────────────────────

_PESOS = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 100}

def _evaluar(tablero):

    t0 = time.perf_counter_ns()

    valor = sum(
        _PESOS.get(abs(p), 0) * (1 if p > 0 else -1)
        for p in tablero
        if p
    )

    t1 = time.perf_counter_ns()

    _metricas_actuales['evaluacion_us'] += (t1 - t0) // 1000
    _metricas_actuales['evaluacion_calls'] += 1

    return valor


# ── Minimax con alfa-beta, memoización e instrumentación ─────────────────────

_cache_minimax = {}
_search_stats  = {'nodos': 0, 'podas': 0, 'cache_hits': 0,
                  'profundidad': 0, 'movimientos_raiz': 0}

_historial_metricas = []

_metricas_actuales = {
    'evaluacion_us': 0,
    'minimax_us': 0,

    'evaluacion_calls': 0,
    'minimax_calls': 0
}

def reset_metricas():
    _metricas_actuales['evaluacion_us'] = 0
    _metricas_actuales['minimax_us'] = 0

    _metricas_actuales['evaluacion_calls'] = 0
    _metricas_actuales['minimax_calls'] = 0

def _minimax(tablero, prof, turno, alpha, beta):
    
    t0 = time.perf_counter_ns()

    _metricas_actuales['minimax_calls'] += 1
    
    key = (tuple(tablero), prof, turno)
    if key in _cache_minimax:
        _search_stats['cache_hits'] += 1
        t1 = time.perf_counter_ns()

        _metricas_actuales['minimax_us'] += (t1 - t0) // 1000
        return _cache_minimax[key]

    if prof == 0:
        _search_stats['nodos'] += 1
        t1 = time.perf_counter_ns()

        _metricas_actuales['minimax_us'] += (t1 - t0) // 1000
        return _evaluar(tablero)

    legales = _movimientos_legales(tablero, turno)
    if not legales:
        _search_stats['nodos'] += 1
        t1 = time.perf_counter_ns()

        _metricas_actuales['minimax_us'] += (t1 - t0) // 1000
        return _evaluar(tablero)

    if turno == 0:  # Blancas: maximizar
        val = float('-inf')
        for desde, hasta in legales:
            nuevo = tablero[:]
            hacer_movimiento(nuevo, desde, hasta)
            val = max(val, _minimax(nuevo, prof - 1, 1, alpha, beta))
            alpha = max(alpha, val)
            if beta <= alpha:
                _search_stats['podas'] += 1
                break
    else:           # Negras: minimizar
        val = float('inf')
        for desde, hasta in legales:
            nuevo = tablero[:]
            hacer_movimiento(nuevo, desde, hasta)
            val = min(val, _minimax(nuevo, prof - 1, 0, alpha, beta))
            beta = min(beta, val)
            if beta <= alpha:
                _search_stats['podas'] += 1
                break

    _cache_minimax[key] = val
    t1 = time.perf_counter_ns()

    _metricas_actuales['minimax_us'] += (t1 - t0) // 1000
    return val


def elegir_movimiento(tablero, turno, profundidad=2, historial=None):
    """Elige el mejor movimiento legal con minimax alfa-beta. Retorna (desde, hasta) o None."""
    if historial is None:
        historial = {}

    _search_stats.update({'nodos': 0, 'podas': 0, 'cache_hits': 0,
                          'profundidad': profundidad, 'movimientos_raiz': 0,
                          'candidatos_disponibles': 0})

    legales = _movimientos_legales(tablero, turno)
    if not legales:
        return None

    _search_stats['candidatos_disponibles'] = len(legales)
    random.shuffle(legales)
    legales = legales[:12]

    _search_stats['movimientos_raiz'] = len(legales)

    mejor = None
    if turno == 0:
        mejor_val = float('-inf')
        alpha_raiz = float('-inf')
        gc.disable()
        
        for desde, hasta in legales:
            nuevo = tablero[:]
            hacer_movimiento(nuevo, desde, hasta)
            penal = historial.get(hash_tablero(nuevo), 0) * 30
            val = _minimax(nuevo, profundidad - 1, 1, alpha_raiz, float('inf')) - penal
            if val > mejor_val:
                mejor_val = val
                mejor = (desde, hasta)
            alpha_raiz = max(alpha_raiz, mejor_val)
            
        gc.enable()
        
    else:
        mejor_val = float('inf')
        beta_raiz = float('inf')
        gc.disable()
        
        for desde, hasta in legales:
            nuevo = tablero[:]
            hacer_movimiento(nuevo, desde, hasta)
            penal = historial.get(hash_tablero(nuevo), 0) * 30
            val = _minimax(nuevo, profundidad - 1, 0, float('-inf'), beta_raiz) + penal
            if val < mejor_val:
                mejor_val = val
                mejor = (desde, hasta)
            beta_raiz = min(beta_raiz, mejor_val)
        gc.enable()

    return mejor


def get_last_stats():
    """Retorna una copia de las métricas de la última búsqueda."""
    return dict(_search_stats)

def guardar_metrica_turno(num_mov):

    nodos = _search_stats['nodos']
    profundidad = _search_stats['profundidad']

    branching_factor = 0

    if profundidad > 0 and nodos > 0:
        branching_factor = round(
            nodos ** (1 / profundidad),
            3
        )

    _historial_metricas.append({
        'turno': num_mov,

        'evaluacion_us':
            _metricas_actuales['evaluacion_us'],

        'minimax_us':
            _metricas_actuales['minimax_us'],

        'nodos':
            nodos,

        'podas':
            _search_stats['podas'],

        'cache_hits':
            _search_stats['cache_hits'],

        'profundidad':
            profundidad,

        'branching_factor':
            branching_factor,

        'tiempo_por_nodo_us':
            round(
                _metricas_actuales['minimax_us'] /
                max(nodos, 1),
                3
            )
    })
    
def guardar_csv():

    if not _historial_metricas:
        return

    os.makedirs("logs", exist_ok=True)

    nombre = (
        f"logs/bigO_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    with open(
        nombre,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=_historial_metricas[0].keys(),
            delimiter=';'
        )

        writer.writeheader()
        writer.writerows(_historial_metricas)

    print(f"\nCSV guardado: {nombre}")


# ── Main (sin bloqueos) ───────────────────────────────────────────────────────

def main():
    tablero  = inicializar_ajedrez()
    turno    = 0
    numero_movimiento = 0
    historial = {}

    while True:
        #imprimir_ajedrez(tablero)
        est = estado_juego(tablero, turno)
        if est == "JAQUE_MATE":
            print("Jaque mate. Gana", "Negras" if turno == 0 else "Blancas")
            guardar_csv()
            break
        elif est == "TABLAS":
            print("Empate por ahogado")
            guardar_csv()
            break

        h = hash_tablero(tablero)
        historial[h] = historial.get(h, 0) + 1
        if historial[h] >= 3:
            print("Empate por repetición.")
            guardar_csv()
            break
        
        reset_metricas()
        mov = elegir_movimiento(tablero, turno, historial=historial)
        hacer_movimiento(tablero, mov[0], mov[1])

        guardar_metrica_turno(numero_movimiento)

        numero_movimiento += 1
        
        if mov is None:
            guardar_csv()
            break
        hacer_movimiento(tablero, mov[0], mov[1])
        turno = 1 - turno
        #input("Enter...")


if __name__ == "__main__":
    main()