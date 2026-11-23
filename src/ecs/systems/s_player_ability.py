import random

import esper
import pygame

from src.create.prefab_obstacle import distance_to_area
from src.create.prefab_pickup import create_pickup
from src.create.prefab_shield import create_shield_aura
from src.ecs.components.c_ability_text import CAbilityText
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_pickup import CPickup
from src.ecs.components.c_pickup_spawner import CPickupSpawner
from src.ecs.components.c_player_ability import CPlayerAbility
from src.ecs.components.c_player_dead import CPlayerDead
from src.ecs.components.c_shield import CShield
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.components.tags.c_tag_hidden import CTagHidden
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_collision import system_collision
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


def _center(c_t: CTransform, c_s: CSurface) -> pygame.Vector2:
    return c_t.pos + pygame.Vector2(c_s.area.size) / 2


def pickup_position(world: esper.World, spawn_info: dict, world_size: pygame.Vector2,
                    player_center: pygame.Vector2, rng: random.Random) -> pygame.Vector2:
    bases = [(_center(c_t, c_s), pygame.Vector2(c_s.area.size))
             for _, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagBase)]
    for _ in range(spawn_info["place_tries"]):
        pos = pygame.Vector2(rng.uniform(0, world_size.x), rng.uniform(0, world_size.y))
        far_from_player = wrapped_delta(pos, player_center, world_size).length() >= spawn_info["min_player_distance"]
        far_from_bases = all(distance_to_area(pos, center, size, world_size) >= spawn_info["base_margin"]
                             for center, size in bases)
        if far_from_player and far_from_bases:
            return pos
    return pos


def system_pickup_spawner(world: esper.World, delta_time: float, pickup_info: dict,
                          world_size: pygame.Vector2, player_center: pygame.Vector2,
                          rng: random.Random = random) -> None:
    c_spawner: CPickupSpawner
    for _, c_spawner in world.get_component(CPickupSpawner):
        c_spawner.timer -= delta_time
        if c_spawner.timer > 0:
            continue
        c_spawner.timer = c_spawner.interval
        if world.get_component(CPickup) or rng.random() >= c_spawner.chance:
            continue
        pos = pickup_position(world, pickup_info["spawn"], world_size, player_center, rng)
        create_pickup(world, pickup_info, pos)


def system_pickup_collection(world: esper.World, world_size: pygame.Vector2) -> None:
    pair = (CollisionLayer.PLAYER, CollisionLayer.PICKUP)
    for player, pickup in system_collision(world, [pair], world_size)[pair]:
        if not world.entity_exists(pickup) or world.has_component(player, CPlayerDead):
            continue
        c_ability = world.try_component(player, CPlayerAbility)
        if c_ability is None or c_ability.charges >= c_ability.max_charges:
            continue
        c_ability.charges += 1
        world.delete_entity(pickup)
        ServiceLocator.sounds_service.play_effect("PICKUP")


def system_player_ability_activate(world: esper.World, ability_info: dict) -> bool:
    c_ability: CPlayerAbility
    for player, (c_ability, _) in world.get_components(CPlayerAbility, CTagPlayer):
        if world.has_component(player, CPlayerDead) or world.has_component(player, CShield):
            continue
        if c_ability.charges <= 0 or c_ability.cooldown_remaining > 0:
            continue
        c_ability.charges -= 1
        c_ability.cooldown_remaining = c_ability.cooldown
        center = _center(world.component_for_entity(player, CTransform), world.component_for_entity(player, CSurface))
        aura = create_shield_aura(world, ability_info["aura_image"], center)
        world.add_component(player, CShield(c_ability.duration, aura))
        ServiceLocator.sounds_service.play_effect("SHIELD_ON")
        return True
    return False


def system_player_ability(world: esper.World, delta_time: float, ability_info: dict) -> None:
    c_ability: CPlayerAbility
    for _, c_ability in world.get_component(CPlayerAbility):
        c_ability.cooldown_remaining = max(0.0, c_ability.cooldown_remaining - delta_time)
    c_shield: CShield
    c_t: CTransform
    c_s: CSurface
    for player, (c_shield, c_t, c_s) in world.get_components(CShield, CTransform, CSurface):
        c_shield.remaining -= delta_time
        c_shield.elapsed += delta_time
        if not world.entity_exists(c_shield.aura):
            world.remove_component(player, CShield)
            continue
        if c_shield.remaining <= 0:
            world.delete_entity(c_shield.aura)
            world.remove_component(player, CShield)
            continue
        aura_t = world.component_for_entity(c_shield.aura, CTransform)
        aura_s = world.component_for_entity(c_shield.aura, CSurface)
        aura_t.pos = _center(c_t, c_s) - pygame.Vector2(aura_s.area.size) / 2
        warning = c_shield.remaining <= ability_info["warning_time"]
        blink_off = warning and int(c_shield.elapsed / ability_info["blink_interval"]) % 2 == 1
        hidden = world.has_component(c_shield.aura, CTagHidden)
        if blink_off and not hidden:
            world.add_component(c_shield.aura, CTagHidden())
        elif not blink_off and hidden:
            world.remove_component(c_shield.aura, CTagHidden)


def system_ability_hud(world: esper.World, hud_info: dict) -> None:
    c_ability: CPlayerAbility
    for player, (c_ability, _) in world.get_components(CPlayerAbility, CTagPlayer):
        if world.has_component(player, CShield):
            text = hud_info["active_text"]
        else:
            text = hud_info["charges_format"].format(charges=c_ability.charges)
        c_text: CText
        for _, (c_text, _) in world.get_components(CText, CAbilityText):
            c_text.text = text
