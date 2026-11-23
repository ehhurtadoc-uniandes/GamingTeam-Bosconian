# Formato del JSON de nivel

Cada nivel es un archivo en `assets/cfg/levels/`, y `assets/cfg/levels.json` los lista en orden.
Todas las posiciones están en **coordenadas de mundo** (el mundo mide lo que diga `world.json`,
hoy 1024 x 1536) y son el **centro** de lo que se crea.

```json
{
  "special": true,
  "core": { "mode": "cycling" },
  "player_start": { "x": 512, "y": 768 },
  "bases": [
    { "pos": { "x": 56, "y": 48 }, "orientation": "horizontal" },
    { "pos": { "x": 204, "y": 150 }, "orientation": "vertical" }
  ],
  "spawner": { "...": "ver s_enemy_spawner" },
  "obstacles": {
    "seed": 1,
    "min_distance": 40,
    "rock": 40,
    "solid_rock": 10,
    "mine": 20
  }
}
```

| Clave | Obligatoria | Qué es |
|---|---|---|
| `special` | no | `true` si el nivel da la habilidad especial (tres balas al frente y una atrás); sin la clave, no la da. Al empezar el nivel sale el mensaje de `assets/cfg/player.json` > `special_shot`. |
| `core.mode` | no | Cómo se comporta el núcleo de **todas** las bases del nivel: `static` (siempre abierto, no lanza enemigos) o `cycling` (se abre y se cierra, y cada vez que termina de abrirse lanza un enemigo E). Sin el bloque `core` o sin `mode`, `static`. Ver abajo. |
| `player_start` | no | Dónde empieza el jugador. Si falta, en el centro de la pantalla. |
| `bases` | no | Lista de bases (sin la clave, el nivel no tiene bases): centro (`pos`) y `orientation` (`horizontal` o `vertical`). La usa `create_bases`. |
| `spawner` | sí | Cómo aparecen los enemigos del nivel (lo usa `create_enemy_spawner`). |
| `obstacles` | no | Cuántos obstáculos de cada tipo se reparten al azar por el mundo. |
| `obstacles.seed` | no | Semilla del azar: con la misma semilla el nivel siempre sale igual. |
| `obstacles.min_distance` | no | Distancia mínima entre obstáculos, al borde del cuerpo de las bases y al inicio del jugador (por defecto 32). |
| `obstacles.rock` / `solid_rock` / `mine` | no | Cantidad de rocas, rocas indestructibles y minas. |

Los tipos de obstáculo (imágenes, puntos, hitbox, animación, explosión de la mina y rapidez
de la roca indestructible, `speed`) están en `assets/cfg/obstacles.json`.

## Núcleo de las bases (`core`, #27)

El modo se elige por nivel; el aspecto y los tiempos están en `assets/cfg/base.json` > `core`:

```json
"core": {
  "size": { "w": 12, "h": 12 },
  "color": { "r": 255, "g": 60, "b": 160 },
  "hitbox": { "size": { "w": 8, "h": 8 } },
  "offset": { "x": 0, "y": 0 },
  "durations": { "closed": 3.0, "opening": 0.6, "open": 1.0, "closing": 0.6 },
  "states": {
    "closed": { "size": { "w": 6, "h": 6 }, "color": { "r": 110, "g": 40, "b": 90 } },
    "opening": { "size": { "w": 9, "h": 9 }, "color": { "r": 255, "g": 200, "b": 80 } },
    "open": { "color": { "r": 255, "g": 60, "b": 160 } },
    "closing": { "size": { "w": 9, "h": 9 }, "color": { "r": 255, "g": 120, "b": 40 } }
  }
}
```

- `durations`: segundos de cada estado, todos mayores que 0. Solo se usan en `cycling`.
- `states`: aspecto de cada estado, con `image` (sprite) o `color` (rectángulo). `size`, `hitbox` y
  lo que falte se toman de `core`. Al cambiar de estado el núcleo conserva su centro aunque cambie de
  tamaño, y en una base vertical se rota igual que el resto de piezas. Sin `states`, todos los estados
  usan el aspecto de `core` (como antes).
- `static`: el núcleo se ve con el aspecto `open` desde el principio y nunca lanza enemigos.
- `cycling`: empieza en `closed` y repite `closed` → `opening` → `open` → `closing`. Cada paso de
  `opening` a `open` lanza un E centrado en el núcleo, con el `spawner.wander_scale` del nivel (1.0 si
  falta). Es independiente del spawner: sale aunque no haya spawner, esté inactivo o se haya llegado a
  `max_alive`. Los E del núcleo sí cuentan para el `max_alive` del spawner.

Un `mode` desconocido, una duración que falte o no sea mayor que 0, o un estado sin `image`/`color`
dan un error al cargar el nivel que nombra el archivo y el campo.

### Modo de cada ronda

| Rondas | `core.mode` |
| --- | --- |
| 1 a 3 | `static`: el núcleo está siempre abierto y no lanza enemigos |
| 4 a 10 | `cycling`: el núcleo se abre, lanza un E y se cierra |

Así la dificultad sube con la ronda, como pide `LC-BAS-06.1`.

### Niveles de prueba

`level_test.json` (`static`) y `level_test_cycling.json` (`cycling`) tienen una base horizontal y otra
vertical cada uno. No están en `levels.json`: los usan las pruebas. Para jugarlos, se ponen en la lista.

## levels.json

```json
{
  "clear_delay": 2.0,
  "round_hud": { "label": { "...": "texto ROUND" }, "value": { "...": "número" } },
  "levels": ["assets/cfg/levels/level_01.json", "..."]
}
```

| Clave | Qué es |
|---|---|
| `levels` | Los niveles en orden. La ronda que se muestra es la posición en esta lista (la primera es la ronda 1). |
| `clear_delay` | Segundos que se espera, al destruir todas las bases, antes de pasar a la siguiente ronda (para que terminen las explosiones). |
| `round_hud` | Texto "ROUND" y su número, abajo en la columna del HUD: `anchor`, `alignment` y `color` de cada uno. |

Después de la última ronda se vuelve al título mientras no exista la escena de victoria (#36).
`level_test.json` ya no está en la lista; queda como nivel de prueba.

## Claves que pueden venir después

- `music`: ruta de la música del nivel.

Si su área necesita otra clave en el nivel, avísenle a Catalina para agregarla aquí.
