import esper

from src.create.prefab_text import create_interface_text


def create_round_hud(world: esper.World, round_info: dict, round_number: int) -> list[int]:
    """Texto "ROUND N" abajo en la columna del HUD (LC-RON-01, #32).

    No cambia durante el nivel: al pasar de nivel la escena se crea de nuevo con el número siguiente.
    """
    label = round_info["label"]
    return [create_interface_text(world, label["text"], label),
            create_interface_text(world, str(round_number), round_info["value"])]
