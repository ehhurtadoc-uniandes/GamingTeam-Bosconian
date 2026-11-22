# Formato del JSON de nivel

Cada nivel es un archivo en `assets/cfg/levels/`, y `assets/cfg/levels.json` los lista en orden.
Todas las posiciones están en **coordenadas de mundo** (el mundo mide lo que diga `world.json`,
hoy 1024 x 1536) y son el **centro** de lo que se crea.

```json
{
  "special": true,
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
| `player_start` | no | Dónde empieza el jugador. Si falta, en el centro de la pantalla. |
| `bases` | no | Lista de bases (sin la clave, el nivel no tiene bases): centro (`pos`) y `orientation` (`horizontal` o `vertical`). La usa `create_bases`. |
| `spawner` | sí | Cómo aparecen los enemigos del nivel (lo usa `create_enemy_spawner`). |
| `obstacles` | no | Cuántos obstáculos de cada tipo se reparten al azar por el mundo. |
| `obstacles.seed` | no | Semilla del azar: con la misma semilla el nivel siempre sale igual. |
| `obstacles.min_distance` | no | Distancia mínima entre obstáculos, al borde del cuerpo de las bases y al inicio del jugador (por defecto 32). |
| `obstacles.rock` / `solid_rock` / `mine` | no | Cantidad de rocas, rocas indestructibles y minas. |

Los tipos de obstáculo (imágenes, puntos, hitbox, animación, explosión de la mina y rapidez
de la roca indestructible, `speed`) están en `assets/cfg/obstacles.json`.

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
- `core`: `normal` o `animated`, y si trae enemigo E (LC-BAS-06.1).

Si su área necesita otra clave en el nivel, avísenle a Catalina para agregarla aquí.
