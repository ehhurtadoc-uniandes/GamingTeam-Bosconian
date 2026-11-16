# Formato del JSON de nivel

Cada nivel es un archivo en `assets/cfg/levels/`, y `assets/cfg/levels.json` los lista en orden.
Todas las posiciones están en **coordenadas de mundo** (el mundo mide lo que diga `world.json`,
hoy 1024 x 1536) y son el **centro** de lo que se crea.

```json
{
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
| `player_start` | no | Dónde empieza el jugador. Si falta, en el centro de la pantalla. |
| `bases` | no | Lista de bases (sin la clave, el nivel no tiene bases): centro (`pos`) y `orientation` (`horizontal` o `vertical`). La usa `create_bases`. |
| `spawner` | sí | Cómo aparecen los enemigos del nivel (lo usa `create_enemy_spawner`). |
| `obstacles` | no | Cuántos obstáculos de cada tipo se reparten al azar por el mundo. |
| `obstacles.seed` | no | Semilla del azar: con la misma semilla el nivel siempre sale igual. |
| `obstacles.min_distance` | no | Distancia mínima entre obstáculos, bases e inicio del jugador (por defecto 32). |
| `obstacles.rock` / `solid_rock` / `mine` | no | Cantidad de rocas, rocas indestructibles y minas. |

Los tipos de obstáculo (imágenes, puntos, hitbox, animación y explosión de la mina) están en
`assets/cfg/obstacles.json`.

## Claves que vienen después (semana 3)

Se agregarán sin romper los niveles que ya existen:

- `round`: número de ronda que muestra la interfaz "ROUND X".
- `special`: habilidad especial del nivel.
- `music`: ruta de la música del nivel.
- `core`: `normal` o `animated`, y si trae enemigo E.

Si su área necesita otra clave en el nivel, avísenle a Catalina para agregarla aquí.
