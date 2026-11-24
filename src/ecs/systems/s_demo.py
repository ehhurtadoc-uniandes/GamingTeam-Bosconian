import esper
import pygame

from src.create.prefab_demo import create_demo_bullet
from src.create.prefab_explosion import create_explosion
from src.ecs.components.c_demo_gun import CDemoGun
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_demo_bullet import CTagDemoBullet
from src.ecs.components.tags.c_tag_demo_target import CTagDemoTarget


def system_demo_fire(world: esper.World, delta_time: float) -> None:
    c_t: CTransform
    c_s: CSurface
    c_g: CDemoGun
    for _, (c_t, c_s, c_g) in world.get_components(CTransform, CSurface, CDemoGun):
        c_g.remaining -= delta_time
        if c_g.remaining <= 0:
            c_g.remaining += c_g.interval
            nose = pygame.Vector2(c_t.pos.x + c_s.area.width / 2, c_t.pos.y)
            create_demo_bullet(world, c_g.bullet_info, nose)


def system_demo_hits(world: esper.World, explosion_info: dict) -> None:
    targets = world.get_components(CTransform, CSurface, CTagDemoTarget)
    c_t: CTransform
    c_s: CSurface
    for bullet, (b_t, b_s, _) in world.get_components(CTransform, CSurface, CTagDemoBullet):
        bullet_rect = pygame.Rect(b_t.pos, b_s.area.size)
        for target, (c_t, c_s, _) in targets:
            if not world.entity_exists(target):
                continue
            target_rect = pygame.Rect(c_t.pos, c_s.area.size)
            if bullet_rect.colliderect(target_rect):
                create_explosion(world, explosion_info, pygame.Vector2(target_rect.center), pygame.Vector2(0, 0))
                world.delete_entity(target)
                world.delete_entity(bullet)
                break
