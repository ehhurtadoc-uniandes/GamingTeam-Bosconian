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
| `obstacles.min_distance` | no | Distancia mínima entre obstáculos, bases e inicio del jugador (por defecto 32). |
| `obstacles.rock` / `solid_rock` / `mine` | no | Cantidad de rocas, rocas indestructibles y minas. |

Los tipos de obstáculo (imágenes, puntos, hitbox, animación y explosión de la mina) están en
`assets/cfg/obstacles.json`.

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

### Niveles de prueba

`assets/cfg/levels.json` lista dos niveles de prueba, con una base horizontal y otra vertical cada uno:

1. `level_test.json`: `"core": { "mode": "static" }`.
2. `level_test_cycling.json`: el mismo nivel con `"core": { "mode": "cycling" }`.

Para jugarlos, en la pantalla de título se elige la ronda con izquierda/derecha (RONDA 1 o RONDA 2)
y se acepta JUGAR; la ronda elegida es `PlayScene.level_index`, el índice en `levels.json`.

## Claves que vienen después (semana 3)

Se agregarán sin romper los niveles que ya existen:

- `round`: número de ronda que muestra la interfaz "ROUND X".
- `music`: ruta de la música del nivel.

Si su área necesita otra clave en el nivel, avísenle a Catalina para agregarla aquí.
