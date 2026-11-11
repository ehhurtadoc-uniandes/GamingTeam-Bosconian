# Preguntas para el equipo — Enemigos e IA

Decisiones que tomamos de forma provisional al implementar el área de enemigos y
que hay que validar con el equipo. Cada pregunta indica el valor que se usa hoy y
dónde cambiarlo. Cuando se resuelva, anotar la respuesta y la fecha.

## #11 — Prototipo de steering (LC-ENE-02)

1. **Velocidad del jugador (LC-ENE-02.2).** Los enemigos deben ir "un poco más
   rápido" que el jugador. Hoy se supone que el jugador va a 60 px/s, y por eso I y P
   van a 70 px/s. ¿Cuál es la velocidad real del jugador (área Jugador y combate, #16)?
   ¿Su velocidad cambia (aceleración, habilidad especial)?
   *Dónde:* `max_speed` en `assets/cfg/enemies.json`.
   - Respuesta:

2. **Tamaño del mundo y wraparound (RF-06).** `system_steering` recibe `world_size`
   para perseguir por el camino más corto cruzando bordes. ¿Cuál es el tamaño real del
   mundo? ¿Quién implementa el sistema de wraparound (área Mundo y niveles)? Ese
   sistema y el nuestro tienen que usar el mismo `world_size`.
   - Respuesta:

3. **Dificultad (LC-ENE-02.1).** "Dependiendo de la dificultad, se aproximan más
   al jugador o se desvían más". Hoy `create_enemy` recibe `wander_scale`, que
   multiplica el desvío aleatorio: más alto = se desvía más. ¿Una dificultad mayor
   significa que se acercan más (menos desvío) o al revés? ¿Dónde se configura la
   dificultad de cada ronda (¿`levels.json`?) y quién se la pasa al spawner?
   - Respuesta:

4. **Punto al que se persigue.** Se persigue `CTransform.pos` del jugador (esquina
   superior izquierda). Mientras jugador y enemigos sean de 8x8 da igual, pero con
   sprites de distinto tamaño conviene usar el centro. ¿Se adopta el centro como
   convención en todo el equipo?
   - Respuesta:

5. **Sprites y rotación.** Hoy los enemigos son cuadrados de color. ¿Cuándo
   estarán los sprites? ¿Las naves rotan según la dirección de la velocidad (¿8 o 16
   direcciones?) o se usa una animación fija?
   - Respuesta:

6. **Pruebas.** Usamos `unittest` (`python -m unittest discover -s tests`). ¿Lo
   adoptamos como convención del equipo? ¿Agregamos CI en GitHub Actions?
   - Respuesta:

## #18 — Enemigos tipo I, P y E (patrón State)

7. **Qué significa que un enemigo "se va" (LC-TEN-01).** Como el mundo hace
   wraparound, nunca sale de verdad. Hoy se elimina la entidad cuando se está
   alejando del jugador **y** su distancia a él supera `despawn_distance` (100 px),
   o cuando pasa `duration` en el estado (5 s para I en LEAVE, 6 s para E). ¿Basta así,
   o debe eliminarse al salir del área de la cámara (eso depende del sistema de
   cámara)? Ojo: `despawn_distance` tiene que ser menor que la mitad del mundo, o
   nunca se cumple.
   - Respuesta:

8. **Borrado de entidades en el motor real.** `system_enemy_state` usa
   `world.delete_entity(entity)` diferido, como en el curso. El motor (área Motor y
   escenas) debe llamar a `world._clear_dead_entities()` (o a `world.process()`) en
   cada frame, como `game_engine` de modulo4. ¿Está contemplado? Propuesta de
   convención: **todos los sistemas borran en diferido**. Si un sistema borra con
   `immediate=True` una entidad que otro ya marcó en diferido en el mismo frame,
   `_clear_dead_entities()` lanza `KeyError` (comprobado con nuestro esper).
   - Respuesta (2026-11-11): sí. `Scene.simulate` llama a
     `_clear_dead_entities()` después de cada `do_update` (#2, PR #65/#67). Sigue
     pendiente acordar la convención de borrar siempre en diferido.

9. **Orden de los sistemas.** En cada frame debe ser
   `system_enemy_state` → `system_steering` → `system_movement` → wraparound.
   ¿Quién arma este orden en la escena de juego?
   - Respuesta (2026-11-11): cada área agrega sus sistemas en `PlayScene.do_update`.
     Este PR deja ahí `system_enemy_state` → `system_steering` → `system_movement`; el
     wraparound (#7) va después del movimiento.

10. **Puntos y explosión (RF-10.2, #16).** `CTagEnemy.points` guarda 50/60/70.
    ¿El sistema de combate/puntaje lee ese campo al destruir un enemigo? Cuando un
    enemigo "se va" (pregunta 7) no explota ni da puntos: ¿de acuerdo?
    - Respuesta:

11. **Duraciones y velocidades.** Valores actuales: I persigue 6 s y luego huye; P
    persigue 2 s y luego vaga; E va a 100 px/s. ¿Se ajustan después de probarlos en
    el juego? ¿Cambian según la ronda?
    - Respuesta:

12. **Rapidez constante.** Con `constant_speed: true`, el steering solo cambia la
    dirección: el enemigo nunca frena y, si no alcanza al jugador, lo rodea. Sin eso,
    P se frenaba hasta ~28 px/s al vagar e incumplía LC-ENE-02.2. ¿Nos gusta este
    comportamiento?
    - Respuesta:

13. **Cómo se va I.** Hoy I huye del jugador (flee). La alternativa es que siga recto
    en la dirección que llevaba. ¿Cuál se parece más a lo que queremos?
    - Respuesta:

14. **¿P vaga para siempre?** Hoy P se queda en WANDER hasta que lo destruyan.
    ¿Debería irse en algún momento, como I?
    - Respuesta:

15. **Spawner (LC-ENE-01, LC-TEN-04).** `create_enemy` solo crea la nave. ¿Quién
    decide cuándo, dónde y de qué tipo sale cada enemigo (desde los bordes al azar o
    desde el núcleo de las bases cuando están abiertas)? ¿Hay un máximo de enemigos
    simultáneos?
    - Respuesta:

16. **E apunta una sola vez.** E apunta al jugador en el frame en que aparece
    (estado AIM) y luego va recto. ¿Debe apuntar a donde está el jugador, o a donde va
    a estar (anticipando su velocidad)?
    - Respuesta:
