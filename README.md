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

> 🚧 **En construcción.** Estas instrucciones son tentativas y se actualizarán a medida que avance el proyecto.

### Requisitos

- Python 3.11 o superior
- [Pygame](https://www.pygame.org/) (pygame-ce)
- [Esper](https://pypi.org/project/esper/)

### Instalación

```bash
git clone <URL-DEL-REPOSITORIO>
cd ProyectoFinal

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

### Ejecución en web

La versión web se construirá con [pygbag](https://pypi.org/project/pygbag/):

```bash
pip install pygbag
pygbag .
```

Luego hay que abrir `http://localhost:8000` en el navegador.

### Versión publicada

El juego se publicará en [itch.io](https://itch.io). Enlace: *pendiente*.

## Controles

> Tentativos.

| Acción                     | Teclado              | Gamepad          |
| -------------------------- | -------------------- | ---------------- |
| Cambiar dirección          | Flechas direccionales | Joystick izquierdo |
| Disparar                   | `Z`                  | A / ✕            |
| Segunda habilidad (bono)   | `X`                  | B / ◯            |
| Pausa                      | `Esc` / `P`          | Start            |

## Modo trampa

*Pendiente.* Aquí se documentarán los atajos para acceder rápido a todas las características del juego (saltar de nivel, invencibilidad, etc.).

## Créditos y recursos

Las imágenes, sonidos y fuentes son recursos de licencia libre proporcionados por el curso o creados por el equipo, respetando los derechos de autor y la resolución original del juego.
