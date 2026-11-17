import esper

from src.create.prefab_text import create_interface_text
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause


def create_special_shot_message(world: esper.World, special_info: dict) -> int:
    message_info = special_info["message"]
    message = create_interface_text(world, message_info["text"], message_info)
    world.add_component(message, CLifetime(special_info["message_duration"]))
    world.add_component(message, CTagHideOnPause())
    return message
