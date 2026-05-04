"""
Enfrenta el modelo ML (blancas) vs minimax (negras) y viceversa.
Uso: python test_modelo.py [ruta_modelo.keras] [num_partidas]
"""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import tensor_aprendizaje
from modeloraul import (inicializar_ajedrez, elegir_movimiento, hacer_movimiento,
                        estado_juego, get_last_stats)

MODELO = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\ajedrez_dya\chees\modelos_ml\Campeonato_noviembre_3.keras"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
MAX_MOV = 150   # corte para evitar partidas infinitas

print(f"Cargando modelo: {os.path.basename(MODELO)}")
motor = tensor_aprendizaje.MotorML()
if not motor.cargar_modelo(MODELO):
    print("ERROR: no se pudo cargar el modelo.")
    sys.exit(1)
print("Modelo cargado.\n")

resultados = {'ML': 0, 'MM': 0, 'empate': 0}

for partida in range(1, N + 1):
    tablero  = inicializar_ajedrez()
    historial_rep = {}
    turno    = 0
    num_mov  = 0
    # Alternamos: partidas impares ML=blancas, pares ML=negras
    ml_turno = 0 if partida % 2 == 1 else 1

    while True:
        est = estado_juego(tablero, turno)
        if est == 'JAQUE_MATE':
            ganador = 'ML' if turno != ml_turno else 'MM'
            resultados[ganador] += 1
            print(f"  Partida {partida:2d}: JAQUE MATE en mov {num_mov} — gana {ganador}")
            break
        if est == 'TABLAS':
            resultados['empate'] += 1
            print(f"  Partida {partida:2d}: TABLAS en mov {num_mov}")
            break
        if num_mov >= MAX_MOV:
            resultados['empate'] += 1
            print(f"  Partida {partida:2d}: CORTE {MAX_MOV} movimientos — empate técnico")
            break

        if turno == ml_turno:
            mov, dist, valor = motor.predecir(tablero, turno, num_mov)
            origen = 'ML'
        else:
            mov = elegir_movimiento(tablero, turno, profundidad=2)
            origen = 'MM'

        if mov is None:
            resultados['empate'] += 1
            print(f"  Partida {partida:2d}: sin movimiento ({origen}) — empate")
            break

        hacer_movimiento(tablero, mov[0], mov[1])
        turno   = 1 - turno
        num_mov += 1

print(f"\n{'='*40}")
print(f"Resultados tras {N} partidas  (ML alterna blancas/negras):")
print(f"  ML gana  : {resultados['ML']}")
print(f"  Minimax  : {resultados['MM']}")
print(f"  Empates  : {resultados['empate']}")
print(f"  Win rate ML: {resultados['ML']/N*100:.0f}%")
