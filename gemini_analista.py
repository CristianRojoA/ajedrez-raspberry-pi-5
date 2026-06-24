"""
gemini_analista.py — Analista táctico de ajedrez con Google Gemini.

Toma un movimiento del historial (board_before, board_after, etc.) y genera
una explicación lógica en lenguaje natural: qué sentido táctico tiene la jugada,
qué material gana/pierde, si ataca, defiende o controla el centro.

NO usa probabilidades del modelo ML — combina los datos REALES del motor
(material capturado, nodos evaluados) con análisis posicional de Gemini.

Requiere: pip install google-generativeai
La API key se lee de la variable de entorno GEMINI_API_KEY o de config_gemini.py
"""

import os
import threading

# ── Códigos de piezas (deben coincidir con modeloraul.py) ────────────────────
_NOMBRES = {
    1: "peón", 2: "caballo", 3: "alfil", 4: "torre", 5: "reina", 6: "rey",
}
_COLS = "abcdefgh"
_VALOR = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}  # rey sin valor material


def _sq(idx):
    """Índice 0-63 → coordenada algebraica (ej: 'e4')."""
    return f"{_COLS[idx % 8]}{idx // 8 + 1}"


def _leer_api_key():
    """Busca la API key en variable de entorno o en config_gemini.py."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        import config_gemini
        return getattr(config_gemini, "GEMINI_API_KEY", None)
    except ImportError:
        return None


def _tablero_a_texto(tablero):
    """Convierte el arreglo de 64 enteros a un diagrama ASCII legible para Gemini."""
    filas = []
    for r in range(7, -1, -1):  # de la fila 8 a la 1
        celdas = []
        for c in range(8):
            p = tablero[r * 8 + c]
            if p == 0:
                celdas.append(".")
            else:
                letra = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}[abs(p)]
                celdas.append(letra if p > 0 else letra.lower())
        filas.append(f"{r + 1}  " + " ".join(celdas))
    filas.append("   a b c d e f g h")
    return "\n".join(filas)


def _describir_movimiento(entry):
    """Genera la descripción factual del movimiento a partir del historial."""
    desde = entry["desde"]
    hasta = entry["hasta"]
    pieza = entry["pieza_volando"]
    capturada = entry.get("capturada", 0)

    color = "blancas" if pieza > 0 else "negras"
    nombre = _NOMBRES.get(abs(pieza), "pieza")

    texto = f"Las {color} mueven {nombre} de {_sq(desde)} a {_sq(hasta)}."

    if capturada != 0:
        nombre_cap = _NOMBRES.get(abs(capturada), "pieza")
        valor_cap = _VALOR.get(abs(capturada), 0)
        texto += f" Captura un {nombre_cap} (vale {valor_cap} puntos)."

    # ¿Promoción?
    if abs(pieza) == 1 and (hasta // 8 == 7 or hasta // 8 == 0):
        texto += " El peón corona a reina."

    return texto, color, capturada


def _construir_prompt(entry, pregunta_usuario=None):
    """Arma el prompt completo para Gemini."""
    desc, color, capturada = _describir_movimiento(entry)
    diagrama_antes = _tablero_a_texto(entry["board_before"])
    diagrama_despues = _tablero_a_texto(entry["board_after"])

    stats = entry.get("stats", {})
    nodos = stats.get("nodos", 0)

    contexto = f"""Eres un profesor de ajedrez explicando una jugada a un estudiante principiante.

POSICIÓN ANTES DEL MOVIMIENTO:
{diagrama_antes}

MOVIMIENTO REALIZADO:
{desc}

POSICIÓN DESPUÉS DEL MOVIMIENTO:
{diagrama_despues}

(Notación: mayúsculas = blancas, minúsculas = negras. P=peón N=caballo B=alfil R=torre Q=reina K=rey)

El motor evaluó {nodos} posiciones para elegir esta jugada usando análisis de material y posición."""

    if pregunta_usuario:
        instruccion = f"""
El estudiante pregunta: "{pregunta_usuario}"

Responde su pregunta de forma clara y breve (máximo 3 frases). Explica la LÓGICA táctica
de la jugada: si ataca una pieza, defiende, controla el centro, prepara una amenaza, etc.
No menciones probabilidades ni tecnicismos de programación. Habla como profesor de ajedrez."""
    else:
        instruccion = """
Explica en máximo 3 frases por qué esta jugada tiene sentido táctico: ¿ataca algo?
¿defiende? ¿controla el centro? ¿prepara una amenaza? ¿gana material?
Habla claro y simple, como un profesor a un principiante. No uses tecnicismos de programación
ni hables de probabilidades."""

    return contexto + "\n" + instruccion


class AnalistaGemini:
    """Wrapper de Gemini para explicar jugadas. Maneja la conexión y los errores."""

    def __init__(self):
        self._modelo = None
        self._disponible = False
        self._error = None
        self._inicializar()

    def _inicializar(self):
        api_key = _leer_api_key()
        if not api_key:
            self._error = "Falta GEMINI_API_KEY (variable de entorno o config_gemini.py)"
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._modelo = genai.GenerativeModel("gemini-flash-latest")
            self._disponible = True
        except ImportError:
            self._error = "Falta instalar: pip install google-generativeai"
        except Exception as e:
            self._error = f"Error al conectar con Gemini: {e}"

    @property
    def disponible(self):
        return self._disponible

    @property
    def error(self):
        return self._error

    def explicar(self, entry, pregunta_usuario=None):
        """Versión síncrona — bloquea hasta recibir respuesta. Retorna str."""
        if not self._disponible:
            return f"[Analista no disponible: {self._error}]"
        try:
            prompt = _construir_prompt(entry, pregunta_usuario)
            respuesta = self._modelo.generate_content(prompt)
            return respuesta.text.strip()
        except Exception as e:
            return f"[Error al generar explicación: {e}]"

    def explicar_async(self, entry, callback, pregunta_usuario=None):
        """Versión asíncrona — no bloquea la UI de Kivy.
        Llama a callback(texto) cuando Gemini responde.
        IMPORTANTE: el callback se ejecuta en un thread aparte; en Kivy
        envuélvelo con Clock.schedule_once para tocar la UI de forma segura."""
        def _worker():
            texto = self.explicar(entry, pregunta_usuario)
            callback(texto)
        threading.Thread(target=_worker, daemon=True).start()
