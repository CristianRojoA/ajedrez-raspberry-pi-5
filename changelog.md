# Changelog — Motor de Ajedrez Autónomo (MAA)

Todos los cambios técnicos y de arquitectura de este proyecto quedan documentados en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) con etiquetas de rol:

- **[PM]** — Project Manager (Gestión, documentación, coordinación)
- **[ARCH]** — Arquitectura (Diseño de sistema, hardware, ML)
- **[DEV]** — Desarrollo (Implementación de código)
- **[QA]** — Quality Assurance (Pruebas, métricas, validación)

---

## [Unreleased] — Trabajo en progreso (Hito 3 → Auditoría QA)

### Por hacer
- [ ] Congelar código para la sesión de auditoría QA (28/05/2026)
- [ ] Exportar métricas CSV de inferencia ML (O(1)) vs encoding (O(n))
- [ ] Ajustar `PARTIDAS_DIR` de rutas Windows (`D:\...`) a rutas relativas de Raspberry Pi
- [ ] Reemplazar referencias a `minimax` en `game_mode` por el modo `ml` como predeterminado en `vistafrancisco.py`
- [ ] Generar `requirements.txt` final con versiones fijadas

---

## [3.2] — 2026-05-05 (Migración de Paradigma IA — SRS v3.2)

### Añadido
- **[ARCH]** `tensor_aprendizaje.py` — Módulo central de ML con la clase `MotorML`:
  - Arquitectura de red neuronal residual dual (cabeza de política + cabeza de valor), inspirada en AlphaZero/LeelaChessZero.
  - Función `tablero_a_tensor()`: encoding del estado del tablero a tensor `(8×8×14)`. Complejidad **O(n)** con n=64.
  - Función `predecir()`: forward pass del modelo Keras. Complejidad de inferencia **O(1)** (arquitectura fija).
  - Entrenamiento supervisado desde archivos PGN con `python-chess`.
  - Guardado de modelos en `modelos_ml/` con metadatos JSON.
- **[ARCH]** `modelos_ml/` — Directorio con modelos pre-entrenados:
  - `Campeonato_noviembre.keras` (v1), `Campeonato_noviembre_2.keras` (v2), `Campeonato_noviembre_3.keras` (v3)
  - `motor_ml_20260503_215250.keras` — último modelo entrenado (50 epochs, 4 bloques residuales, 128 filtros)
  - Metadatos JSON asociados a cada modelo (`policy_size: 4096`, `input_shape: [8,8,14]`)
- **[DEV]** `vista_screens_ml.py` — Nuevas pantallas de la interfaz ML:
  - `EntrenarScreen`: selección de PGNs, opción de continuar desde modelo existente, barra de progreso de entrenamiento.
  - `ProbarModeloScreen`: enfrenta modelo ML vs Minimax en N partidas con reporte de win rate.
- **[DEV]** `vista_screens_inicio.py` — Pantalla `MLScreen`: menú de navegación entre modos ML (Entrenar / Probar / Jugar con ML).
- **[DEV]** `test_modelo.py` — Script de benchmark: ML (blancas/negras alternadas) vs Minimax depth-2, con corte a 150 movimientos.
- **[PM]** SRS v3.2 (`docs/SRS_29148_v3.2_Motor_de_Ajedrez_ML.docx`):
  - CR-003 aprobado: migración oficial de paradigma de IA.
  - Glosario expandido: *Inferencia de Red Neuronal*, *Encoding (Codificación de Tensor)*, *Red Neuronal Residual (ResNet)*, *ONNX / TensorFlow Lite*.
  - `SRS-RF005` reescrito: pipeline completo de inferencia ML.
  - Notación asintótica actualizada: O(1) para inferencia, O(n) para encoding y generación de movimientos.

### Cambiado
- **[ARCH]** Paradigma de IA: **Minimax + Poda Alfa-Beta → Aprendizaje Supervisado (Red Neuronal Residual)**.
  - El motor Minimax (`modeloraul.py`) se conserva como modo alternativo y como oponente de referencia en `test_modelo.py`.
- **[ARCH]** Complejidad temporal redefinida en el SRS:
  - ~~O(b^d)~~ → **O(1)** para la fase de inferencia de la red neuronal.
  - O(n) para generación de movimientos y encoding (n = 64 casillas).
- **[DEV]** `vistafrancisco.py` — `ChessApp` actualizado con soporte dual de modo:
  - `game_mode = 'minimax'` (legacy) o `game_mode = 'ml'` con `ml_model_path` y `ml_turno`.
  - Nuevas pantallas registradas en el `ScreenManager`: `ml_menu`, `entrenar`, `probar`.
- **[PM]** `README.md` — Reescritura completa: documentación del stack ML, estructura de archivos, instrucciones de instalación y guía de métricas Big-O.

### Eliminado
- **[ARCH]** Toda dependencia de pantalla **TFT 2.4″ vía bus SPI**: eliminada del SRS, documentación y referencias en código.
- **[ARCH]** Referencias a **botones físicos GPIO** como método de inicio: reemplazadas por interfaz táctil 100% en Monitor Touch 10.1″.
- **[PM]** Término "Poda Alfa-Beta" del Glosario SRS: reemplazado por "Modelo ONNX/TensorFlow Lite".
- **[PM]** Término "Minimax" del Glosario SRS: reemplazado por "Inferencia de Red Neuronal".

---

## [3.1] — 2026-04-29 (Migración de Hardware de Visualización — SRS v3.1)

### Añadido
- **[ARCH]** Integración con **Monitor IPS Touch 10.1″** (resolución nativa 1920×1200) conectado vía HDMI/micro-HDMI o DSI.
- **[DEV]** `vista_config.py` — Resolución de la ventana Kivy configurada a 1520×960 con `Config.set()`.
- **[DEV]** `vista_tablero.py` — Widget del tablero con soporte de 3 skins (`clasico`, `shield`, `vocaloid_backup`).
- **[DEV]** `vista_paneles.py` — `MovePanel`: panel lateral con historial cronológico de movimientos en notación SAN. `ChatPanel`: panel auxiliar.
- **[DEV]** `vista_screens_juego.py` — Pantallas `MenuScreen`, `VideoScreen`, `PartidasScreen`, `GameScreen` con controles táctiles de Pausa/Reanudar.

### Cambiado
- **[ARCH]** Delegación del renderizado gráfico a la **GPU de la Raspberry Pi 5**, eliminando la carga sobre la CPU.
- **[ARCH]** Interfaz de control migrada de botones GPIO físicos a **controles táctiles** en la pantalla.

### Eliminado
- **[ARCH]** Pantalla TFT 2.4″ por bus SPI (`spidev`, `luma.lcd`): eliminada del stack tecnológico.
- **[ARCH]** Botones físicos GPIO como método de inicio de partida.

---

## [3.0] — 2026-04-22 (Migración de Plataforma y Correcciones QA — SRS v3.0)

### Añadido
- **[ARCH]** Ventilación activa (disipador + ventilador) sobre la CPU de la Raspberry Pi 5 para evitar thermal throttling durante la ejecución prolongada del motor.
- **[DEV]** `modeloraul.py` — Motor lógico FIDE completo en Python:
  - Generador de movimientos legales para las 6 piezas.
  - Enroque corto y largo, promoción automática de peón a reina.
  - Detección de jaque, jaque mate y tablas por ahogado.
  - Algoritmo Minimax con poda alfa-beta, memoización y estadísticas (`get_last_stats()`).
  - Penalización por repetición de posición en `elegir_movimiento()`.
- **[DEV]** `partidas_pgn.py` — Exportación de partidas a formato PGN con notación SAN completa.
- **[QA]** Integración de `gc.disable()` / `gc.enable()` alrededor de la llamada al Minimax para proteger las métricas de tiempo.
- **[QA]** Uso de `time.perf_counter()` para medición a nivel de microsegundos, evitando latencias de sincronización NTP.

### Cambiado
- **[DEV]** Lenguaje de implementación: **C++ (Arduino) → Python 3.11**.
- **[ARCH]** Hardware principal: **Arduino Mega 2560 → Raspberry Pi 5 (4 GB RAM)**.
- **[PM]** SRS adaptado a plantilla ISO/IEC/IEEE 29148:2018 con matriz de trazabilidad completa.

### Arreglado
- **[QA]** Resolución de todos los hallazgos de prioridad ALTA y MEDIA de la primera ronda de QA.
- **[DEV]** Corrección del generador de movimientos para el caso de jaque al propio rey tras enroque.

---

## [2.0] — 2026-04-03 (Reestructuración Mayor de Arquitectura — SRS v2.0)

### Añadido
- **[ARCH]** Migración a **Raspberry Pi 5** como plataforma principal (CR-001).
- **[PM]** Inclusión de reglas FIDE completas: Enroque (corto y largo), Captura al Paso (En Passant), Promoción de peón (CR-002).
- **[PM]** Adaptación del documento SRS al estándar ISO/IEC/IEEE 29148:2018.

### Cambiado
- **[ARCH]** Stack tecnológico redefinido: Arduino Mega → Raspberry Pi 5, C++ → Python.

---

## [1.0.0] — 2026-03-25 (Entrega Hito 1 — SRS v1.0)

### Añadido
- **[PM]** Creación y firma del documento SRS (Versión 1.0) con especificación inicial orientada a Arduino Mega 2560.
- **[ARCH]** Definición del stack tecnológico original: Arduino Mega 2560 (C++), pantalla TFT SPI 2.4″, botones GPIO.
- **[DEV]** Prototipo inicial del generador de movimientos en C++ para Arduino.
- **[PM]** Identificación de stakeholders y levantamiento de necesidades de negocio.
