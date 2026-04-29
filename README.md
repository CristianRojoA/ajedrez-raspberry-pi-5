# ♟️ Jaque Mate al Big O: Ajedrez Autónomo en Arduino Mega

Este proyecto de 3er año de Ingeniería en Computación utiliza un **Arduino Mega** para ejecutar un motor de ajedrez contra sí mismo, con el fin de demostrar y analizar la **Notación Asintótica (Big O)** en un entorno de hardware limitado.

## 👥 Integrantes y Roles (Grupo 1)
* **Project Manager (PM):** Cristian - Coordinación General, Gestión y Documentación.
* **Arquitectos (ARCH):** Mauricio e Ignacio - Diseño de Hardware, Circuito y Gestión de Memoria Crítica.
* **Desarrolladores (DEV):** Francisco y Raúl - Motor de Ajedrez (Minimax / Alpha-Beta) e Interfaz Gráfica.
* **Tester:** Alvaro - Control de Calidad, Pruebas de Estrés y Análisis de Datos (Big O Logs).

## 🛠️ Tecnologías y Optimización
* **Microcontrolador:** Raspberry Pi 5 (4GB RAM).
* **Algoritmo:** Búsqueda Minimax optimizada con Poda Alpha Beta para mitigar la complejidad exponencial O(b^d).

## 📁 Estructura del Repositorio
* `/src`: Código fuente principal (.ino).
* `/assets`: Imágenes y sprites de las piezas para la SD.
* `/docs`: Diagramas de circuitos y manual de usuario.
* `/data`: Logs de tiempos de ejecución para gráficas de complejidad.
