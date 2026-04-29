import random

# Códigos: Torre=4, Caballo=2, Alfil=3, Dama=5, Rey=6, Peón=1  (negativos = negras)

def inicializar_ajedrez():
    tablero = [0] * 64

    tablero[0], tablero[7]   =  4,  4   # Torres Blancas
    tablero[56], tablero[63] = -4, -4   # Torres Negras

    tablero[1], tablero[6]   =  2,  2   # Caballos Blancos
    tablero[57], tablero[62] = -2, -2   # Caballos Negros

    tablero[2], tablero[5]   =  3,  3   # Alfiles Blancos
    tablero[58], tablero[61] = -3, -3   # Alfiles Negros

    tablero[3],  tablero[59] =  5, -5   # Damas
    tablero[4],  tablero[60] =  6, -6   # Reyes

    for i in range(8):
        tablero[8  + i] =  1   # Peones Blancos (fila 1)
        tablero[48 + i] = -1   # Peones Negros  (fila 6)

    return tablero


def imprimir_ajedrez(tablero):
    for i in range(64):
        print(f"{tablero[i]:3d}", end="")
        if (i + 1) % 8 == 0:
            print()
    print()


# ── Movimientos válidos ───────────────────────────────────────────────────────

def _en_tablero(r, c):
    return 0 <= r <= 7 and 0 <= c <= 7


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
        dir_          = 1 if blanca else -1
        fila_inicial  = 1 if blanca else 6

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
                if tablero[nr * 8 + nc] != 0:  # captura: incluir pero parar
                    break
                nr, nc = nr + dr, nc + dc

    elif abs_p == 6:  # Rey
        for dr, dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nr, nc = r + dr, c + dc
            if puede_ir(nr, nc):
                movs.append(nr * 8 + nc)

    return movs


def get_all_moves(tablero, turno):
    """Retorna lista de (desde, hasta) para todos los movimientos del turno dado."""
    movs = []
    for i in range(64):
        p = tablero[i]
        if (turno == 0 and p > 0) or (turno == 1 and p < 0):
            for dest in get_valid_moves(tablero, i):
                movs.append((i, dest))
    return movs


def hacer_movimiento(tablero, desde, hasta):
    """Ejecuta el movimiento. Promoción automática de peón a reina."""
    tablero[hasta] = tablero[desde]
    tablero[desde] = 0
    if tablero[hasta] ==  1 and hasta // 8 == 7:
        tablero[hasta] =  5   # peón blanco → reina
    elif tablero[hasta] == -1 and hasta // 8 == 0:
        tablero[hasta] = -5   # peón negro  → reina


def elegir_movimiento_aleatorio(tablero, turno):
    """Devuelve (desde, hasta) aleatorio para el turno, o None si no hay movimientos."""
    movs = get_all_moves(tablero, turno)
    return random.choice(movs) if movs else None


# ── Funciones originales (conservadas) ───────────────────────────────────────

def mover_peon_automatico(tablero, turno):
    numero        = 1 if turno == 0 else -1
    nueva_posicion = 8 if turno == 0 else -8
    for i in range(64):
        if tablero[i] == numero:
            destino = i + nueva_posicion
            if 0 <= destino < 64 and tablero[destino] == 0:
                tablero[destino] = numero
                tablero[i] = 0
                print(f"Peón movido de {i} a {destino}")
                return True
    return False


def mover_caballo_automatico(tablero, turno):
    numero = 2 if turno == 0 else -2
    for i in range(64):
        if tablero[i] == numero:
            for mov in (-17, -15, -10, -6, 6, 10, 15, 17):
                destino = i + mov
                if 0 <= destino < 64 and tablero[destino] == 0:
                    tablero[destino] = numero
                    tablero[i] = 0
                    print(f"Caballo movido de {i} a {destino}")
                    return True
    return False


def main():
    tablero = inicializar_ajedrez()
    imprimir_ajedrez(tablero)
    p = 0
    while True:
        mover_peon_automatico(tablero, 0)
        imprimir_ajedrez(tablero)
        mover_peon_automatico(tablero, 1)
        imprimir_ajedrez(tablero)
        input(p)


if __name__ == "__main__":
    main()
