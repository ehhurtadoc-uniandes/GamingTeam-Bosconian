"""Creación de la alerta del nivel y de su texto en el HUD (#29).

La configuración está en assets/cfg/alerts.json. El JSON del nivel puede traer un bloque
"alert" que reemplaza, solo para ese nivel, cualquiera de los tiempos y multiplicadores.
Sonidos y HUD solo se configuran en alerts.json. Ver docs/formato-niveles.md.
"""
import os

import esper
import pygame

from src.create.prefab_text import create_interface_text
from src.ecs.components.c_alert import AlertSettings, AlertState, CAlert
from src.ecs.components.c_alert_text import CAlertText
from src.ecs.systems.s_alert import apply_alert_to_spawners

# Campos que el bloque "alert" del nivel puede reemplazar.
TIME_FIELDS = ("green_duration", "base_destroyed_green_duration", "red_after")
MULTIPLIER_FIELDS = ("red_speed_multiplier", "red_rate_multiplier")


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_settings(values: dict, path: str, prefix: str, required: bool) -> dict[str, float]:
    """Valida los tiempos (> 0) y multiplicadores (>= 1) de values. Con required, deben estar todos."""
    checked = {}
    for field in TIME_FIELDS + MULTIPLIER_FIELDS:
        if field not in values:
            if required:
                raise ValueError(f"{path}: falta {prefix}{field}")
            continue
        value = values[field]
        if field in TIME_FIELDS and not (_number(value) and value > 0):
            raise ValueError(f"{path}: {prefix}{field} debe ser un número mayor que 0 (es {value!r})")
        if field in MULTIPLIER_FIELDS and not (_number(value) and value >= 1):
            raise ValueError(f"{path}: {prefix}{field} debe ser un número mayor o igual que 1 (es {value!r})")
        checked[field] = float(value)
    return checked


def load_alert_settings(alerts_info: dict, alerts_path: str,
                        level_info: dict, level_path: str) -> AlertSettings:
    """Valores de alerts.json con los del bloque "alert" del nivel encima.

    Lanza ValueError con el archivo y el campo si algo falta o no es válido. Se permite
    red_after <= green_duration: el nivel pasa a ROJA sin haber estado en AMARILLA.
    """
    values = _check_settings(alerts_info, alerts_path, "", required=True)
    level_alert = level_info.get("alert", {})
    if not isinstance(level_alert, dict):
        raise ValueError(f"{level_path}: alert debe ser un objeto")
    unknown = set(level_alert) - set(TIME_FIELDS + MULTIPLIER_FIELDS)
    if unknown:
        valid = ", ".join(TIME_FIELDS + MULTIPLIER_FIELDS)
        raise ValueError(f"{level_path}: alert.{sorted(unknown)[0]} no se puede cambiar por nivel "
                         f"(se puede: {valid}; sonidos y HUD van en alerts.json)")
    values.update(_check_settings(level_alert, level_path, "alert.", required=False))
    return AlertSettings(**values)


def load_alert_sounds(alerts_info: dict, alerts_path: str) -> dict[AlertState, str]:
    """Ruta del sonido de cada estado. Solo comprueba que el archivo exista, sin reproducirlo."""
    sounds = alerts_info.get("sounds")
    if not isinstance(sounds, dict):
        raise ValueError(f"{alerts_path}: falta sounds o no es un objeto")
    result = {}
    for state in AlertState:
        path = sounds.get(state.value)
        if not isinstance(path, str):
            raise ValueError(f"{alerts_path}: falta sounds.{state.value}")
        if not os.path.isfile(path):
            raise ValueError(f"{alerts_path}: sounds.{state.value} no existe ({path})")
        result[state] = path
    return result


def load_alert_hud(alerts_info: dict, alerts_path: str) -> dict:
    """Comprueba que el bloque "hud" traiga lo que usan create_alert_hud y system_alert_hud."""
    hud = alerts_info.get("hud")
    if not isinstance(hud, dict):
        raise ValueError(f"{alerts_path}: falta hud o no es un objeto")
    for part, keys in (("label", ("text", "anchor", "alignment", "color")),
                       ("value", ("anchor", "alignment"))):
        if not isinstance(hud.get(part), dict):
            raise ValueError(f"{alerts_path}: falta hud.{part}")
        for key in keys:
            if key not in hud[part]:
                raise ValueError(f"{alerts_path}: falta hud.{part}.{key}")
    states = hud.get("states")
    if not isinstance(states, dict):
        raise ValueError(f"{alerts_path}: falta hud.states")
    for state in AlertState:
        look = states.get(state.value)
        if not isinstance(look, dict) or not isinstance(look.get("text"), str) \
                or not isinstance(look.get("color"), dict):
            raise ValueError(f"{alerts_path}: hud.states.{state.value} necesita text y color")
    return hud


def create_alert(world: esper.World, alerts_info: dict, alerts_path: str,
                 level_info: dict, level_path: str) -> int:
    """Crea la alerta del nivel en VERDE, con el tiempo en cero. Entrar en VERDE aquí no suena.

    Apaga de una vez el spawner del nivel (si ya existe), para que no salga nada en VERDE.
    """
    settings = load_alert_settings(alerts_info, alerts_path, level_info, level_path)
    c_alert = CAlert(settings, load_alert_sounds(alerts_info, alerts_path))
    entity = world.create_entity(c_alert)
    apply_alert_to_spawners(world, c_alert)
    return entity


def create_alert_hud(world: esper.World, hud_info: dict) -> int:
    """Crea el texto CONDITION y el del nombre del estado. Devuelve la entidad del nombre."""
    create_interface_text(world, hud_info["label"]["text"], hud_info["label"])
    states = {}
    for state in AlertState:
        look = hud_info["states"][state.value]
        c = look["color"]
        states[state] = {"text": look["text"], "color": pygame.Color(c["r"], c["g"], c["b"])}
    green = hud_info["states"][AlertState.GREEN.value]
    value = create_interface_text(world, green["text"], dict(hud_info["value"], color=green["color"]))
    world.add_component(value, CAlertText(states))
    return value
