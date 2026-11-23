"""Condición de alerta del nivel: VERDE, AMARILLA y ROJA (LC-ALE-01 a LC-ALE-05, RF-15, #29).

- El nivel empieza en VERDE, sin enemigos. A los green_duration segundos de juego pasa a AMARILLA.
- Destruir una base en AMARILLA la pone en VERDE durante base_destroyed_green_duration segundos.
- Al llegar el tiempo total de juego a red_after pasa a ROJA, desde cualquier estado, y ya no baja.

system_alert solo corre mientras PlayScene está en PLAYING, así que el BLAST OFF y la pausa
detienen el tiempo. Cada cambio de estado pide su sonido a SoundsService.
"""
import esper
import pygame

from src.ecs.components.c_alert import AlertState, CAlert
from src.ecs.components.c_alert_boost import CAlertBoost
from src.ecs.components.c_alert_text import CAlertText
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_text import CText
from src.ecs.components.c_velocity import CVelocity
from src.engine.service_locator import ServiceLocator


def get_alert(world: esper.World) -> CAlert | None:
    """La alerta del nivel, o None si el mundo no tiene (p. ej. en pruebas de otros sistemas)."""
    alerts = world.get_component(CAlert)
    return alerts[0][1] if alerts else None


def record_base_destroyed(world: esper.World) -> None:
    """Registra que cayó una base. Lo llama destroy_base; system_alert lo procesa en su siguiente paso."""
    for _, c_alert in world.get_component(CAlert):
        c_alert.bases_destroyed += 1


def system_alert(world: esper.World, delta_time: float) -> list[AlertState]:
    """Avanza la alerta delta_time segundos de juego y aplica sus efectos al spawner.

    Devuelve los estados a los que entró en este paso, en orden; cada uno ya pidió su sonido.
    Va antes de system_enemy_spawner y system_base_core, para que un cambio de alerta afecte
    las apariciones de este mismo paso.
    """
    changes = []
    for _, c_alert in world.get_component(CAlert):
        changes += _update_alert(c_alert, delta_time)
        apply_alert_to_spawners(world, c_alert)
    return changes


def _update_alert(c_alert: CAlert, delta_time: float) -> list[AlertState]:
    settings = c_alert.settings
    changes: list[AlertState] = []
    # Varias bases en el mismo paso cuentan como una sola destrucción.
    base_destroyed = c_alert.bases_destroyed > 0
    c_alert.bases_destroyed = 0
    # Si este paso llega a ROJA, gana ROJA: no tiene sentido un VERDE que dura cero segundos.
    if base_destroyed and c_alert.total_time + delta_time < settings.red_after:
        if c_alert.state == AlertState.YELLOW:
            _enter(c_alert, AlertState.GREEN, changes, temporary_green=True)
        elif c_alert.state == AlertState.GREEN and c_alert.temporary_green:
            c_alert.time_in_state = 0.0
        # En el VERDE inicial no cambia nada, y en ROJA las bases ya no bajan la alerta.

    # Se procesan los umbrales en orden: un paso largo puede pasar por VERDE -> AMARILLA -> ROJA.
    remaining = delta_time
    while c_alert.state != AlertState.RED:
        to_red = settings.red_after - c_alert.total_time
        to_end = _green_duration(c_alert) - c_alert.time_in_state \
            if c_alert.state == AlertState.GREEN else float("inf")
        step = max(0.0, min(remaining, to_red, to_end))
        c_alert.total_time += step
        c_alert.time_in_state += step
        remaining -= step
        if step >= to_red:
            # Se fija el valor exacto para que un error de redondeo no deje el umbral sin cruzar.
            c_alert.total_time = settings.red_after
            _enter(c_alert, AlertState.RED, changes)
        elif step >= to_end:
            _enter(c_alert, AlertState.YELLOW, changes)
        else:
            break
    if c_alert.state == AlertState.RED:
        c_alert.total_time += remaining
        c_alert.time_in_state += remaining
    return changes


def _green_duration(c_alert: CAlert) -> float:
    if c_alert.temporary_green:
        return c_alert.settings.base_destroyed_green_duration
    return c_alert.settings.green_duration


def _enter(c_alert: CAlert, state: AlertState, changes: list[AlertState],
           temporary_green: bool = False) -> None:
    c_alert.state = state
    c_alert.time_in_state = 0.0
    c_alert.temporary_green = temporary_green
    changes.append(state)
    ServiceLocator.sounds_service.play(c_alert.sounds[state])


def apply_alert_to_spawners(world: esper.World, c_alert: CAlert) -> None:
    """VERDE apaga el spawner (su time_to_spawn queda congelado); AMARILLA y ROJA lo prenden.

    En ROJA el temporizador avanza con red_rate_multiplier; siguen rigiendo max_alive y el
    máximo de un enemigo por paso de system_enemy_spawner.
    """
    for _, c_sp in world.get_component(CEnemySpawner):
        c_sp.active = c_alert.state != AlertState.GREEN
        c_sp.rate_multiplier = alert_rate_multiplier(c_alert)


def alert_rate_multiplier(c_alert: CAlert | None) -> float:
    """Ritmo del spawner y de los núcleos: red_rate_multiplier en ROJA, 1 en los demás."""
    if c_alert is not None and c_alert.state == AlertState.RED:
        return c_alert.settings.red_rate_multiplier
    return 1.0


def alert_allows_launch(c_alert: CAlert | None) -> bool:
    """Los núcleos lanzan E en AMARILLA y ROJA, no en VERDE. Sin alerta, siempre."""
    return c_alert is None or c_alert.state != AlertState.GREEN


def system_alert_speed(world: esper.World) -> None:
    """En ROJA multiplica una sola vez max_speed y la velocidad de cada enemigo, sin cambiar su dirección.

    Alcanza a los que estaban al entrar en ROJA y a los creados después (spawner, núcleos o
    depuración). Va después de system_enemy_spawner y system_base_core y antes de
    system_enemy_state, para que el E nuevo salga de AIM con la velocidad ya multiplicada.
    """
    c_alert = get_alert(world)
    if c_alert is None or c_alert.state != AlertState.RED:
        return
    factor = c_alert.settings.red_speed_multiplier
    c_st: CSteering
    c_v: CVelocity
    for enemy, (_, c_st, c_v) in world.get_components(CEnemy, CSteering, CVelocity):
        if world.has_component(enemy, CAlertBoost):
            continue
        c_st.max_speed *= factor
        c_v.vel *= factor
        world.add_component(enemy, CAlertBoost(factor))


def system_alert_hud(world: esper.World) -> None:
    """Muestra en el HUD el nombre de la condición actual con su color. Va antes de system_text."""
    c_alert = get_alert(world)
    if c_alert is None:
        return
    c_text: CText
    c_alert_text: CAlertText
    for _, (c_text, c_alert_text) in world.get_components(CText, CAlertText):
        look = c_alert_text.states[c_alert.state]
        c_text.text = look["text"]
        c_text.color = pygame.Color(look["color"])
