# Proyecto Final — Introducción al Desarrollo de Videojuegos (MISW4407)

Proyecto final en grupo del curso *Introducción al desarrollo de videojuegos* de la Universidad de los Andes.

## Descripción

Un shooter espacial multidireccional en 2D basado en el juego de arcade *Bosconian* (versión Sharp X68000). El jugador pilota una nave que se mueve sola por un mundo con wraparound: las entidades que salen por un borde reaparecen por el opuesto. Para pasar cada ronda hay que destruir todas las bases enemigas, mientras se esquivan rocas, minas y naves enemigas que persiguen al jugador.

El objetivo académico es aplicar los conceptos vistos en el curso:

- Patrón **Game Loop**
- Arquitectura **ECS** (Entidad-Componente-Sistema) con [Esper](https://github.com/benmoran56/esper)
- Patrones **Command**, **State**, **Service Locator** y **Scene**
- Colisiones AABB con hitbox, cámara, parallax, sprites y animación 2D
- IA con *steering behaviours*
- Configuración del juego (niveles, jugador, enemigos, recursos) en archivos externos (JSON)
- Despliegue para escritorio y web

### Características principales

- Escena de introducción, 10 rondas, instrucciones y créditos
- Fondo de estrellas con color, parpadeo y parallax
- Cámara que sigue al jugador y minimapa
- Jugador con aceleración, disparo doble y habilidad especial
- Bases enemigas con seis torretas y núcleo
- Enemigos de tipo I, P y E
- Obstáculos: rocas, minas y rocas indestructibles
- Sistema de alertas (verde, amarilla y roja), puntaje, puntaje máximo y vidas
- Sonidos por evento y música por escena

> Resolución: 256x208 px (o 256x256 px con franjas negras de 24 px arriba y abajo).

## Integrantes — Gaming Team

| Apellidos          | Nombre         | Correo                                                     |
| ------------------ | -------------- | ---------------------------------------------------------- |
| Martínez Vélez     | Valeria        | [v.martinezv2@uniandes.edu.co](mailto:v.martinezv2@uniandes.edu.co) |
| Hurtado Cruz       | Edwin          | [eh.hurtado@uniandes.edu.co](mailto:eh.hurtado@uniandes.edu.co)     |
| Villacris Gónzalez | Maria Catalina | [m.villacris@uniandes.edu.co](mailto:m.villacris@uniandes.edu.co)   |
| Leal Barrios       | Esteban        | [e.leal1@uniandes.edu.co](mailto:e.leal1@uniandes.edu.co)           |

## Cómo ejecutar el juego

### Jugar en el navegador

La versión web está publicada en itch.io y se actualiza sola con cada cambio que entra a `main`:

**https://ehhurtadoc-uniandes.itch.io/bosconian**

### Requisitos para escritorio

- Python 3.12
- [pygame-ce](https://pyga.me/) 2.5.8 (se instala con `requirements.txt`)
- [Esper](https://github.com/benmoran56/esper) ya viene incluido en la carpeta `esper/` del repositorio, así que no hay que instalarlo.

### Instalación

```bash
git clone https://github.com/ehhurtadoc-uniandes/GamingTeam-Bosconian.git
cd GamingTeam-Bosconian

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Ejecución en escritorio

```bash
python main.py
```

### Ejecución web en local

La versión web se construye con [pygbag](https://pypi.org/project/pygbag/):

```bash
pip install pygbag==0.9.2
python -m pygbag .
```

Luego hay que abrir `http://localhost:8000` en el navegador.

### Pruebas

```bash
python -m unittest discover -s tests -t .
```

## Controles

| Acción                   | Teclado                  | Gamepad                  |
| ------------------------ | ------------------------ | ------------------------ |
| Mover / cambiar dirección | Flechas (dos a la vez para diagonal) | Stick izquierdo o cruceta |
| Disparar                 | `Z`                      | A / ✕                    |
| Escudo (segunda habilidad) | `X`                    | B / ◯                    |
| Pausa                    | `P` / `Esc`              | Start                    |
| Menús: elegir            | Flechas                  | Stick o cruceta          |
| Menús: aceptar           | `Z` / `Enter` / `Espacio` | A / ✕                   |
| Menús: volver            | `Esc` / `X`              | B / ◯                    |

Si en el título no se toca nada durante 15 segundos, empieza el modo atractor: una demo y luego las instrucciones. Cualquier tecla vuelve al título.

## Modo trampa

Atajos para ver rápido todas las características del juego. Funcionan durante la partida (no en pausa ni durante el "BLAST OFF!") y se activan o desactivan en `assets/cfg/cheats.json` con `"enabled"`. Al usar una trampa se muestra un aviso abajo en la pantalla.

| Tecla | Trampa |
| ----- | ------ |
| `N`   | Pasar a la siguiente ronda; desde la última, a la escena de victoria. No funciona con la nave explotando |
| `I`   | Invencible: nada mata al jugador y la nave atraviesa enemigos, balas y obstáculos (activar / desactivar) |
| `O`   | Disparo especial aunque la ronda no lo dé (activar / desactivar) |
| `J`   | Sumar 10.000 puntos, para ver las vidas extra y el HI-SCORE |

Las trampas activas siguen activas al cambiar de ronda, al reaparecer y al continuar.

En la escena de título también se puede **elegir la ronda** con izquierda y derecha sobre `< RONDA n >`.

### Teclas de depuración

Con `"enabled": true` en `assets/cfg/debug.json`:

| Tecla | Acción |
| ----- | ------ |
| `1` `2` `3` | Crear un enemigo I, P o E en el borde de la pantalla |
| `H`   | Mostrar u ocultar las hitbox |
| `K`   | Hacer explotar al jugador y a los enemigos |
| `L`   | Matar al jugador (pierde una vida) |

## Créditos y recursos

Las imágenes, sonidos y fuentes son recursos de licencia libre proporcionados por el curso o creados por el equipo, respetando los derechos de autor y la resolución original del juego.
