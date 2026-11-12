import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, CTagEnemyBullet


def system_enemy_bullet_collision(world: esper.World) -> None:
    """Un enemigo que choca con una bala de torreta muere, y la bala también (LC-BAS-05.1).

    No suma puntos: no lo mató el jugador. Las bases no tienen CTagEnemy, así que
    las balas las atraviesan. Mientras no esté la HitBox (#15) se usa el
    rectángulo de CTransform + CSurface; la explosión llegará con #16.

    El borrado es diferido, así que se ignoran las entidades ya marcadas en este
    paso (p. ej. una bala vencida en system_lifetime o un enemigo que se fue).
    """
    bullets = [(entity, _rect(c_t, c_s))
               for entity, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagEnemyBullet)
               if world.entity_exists(entity)]
    if not bullets:
        return
    used_bullets = set()
    for enemy, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagEnemy):
        if not world.entity_exists(enemy):
            continue
        enemy_rect = _rect(c_t, c_s)
        for bullet, bullet_rect in bullets:
            if bullet not in used_bullets and enemy_rect.colliderect(bullet_rect):
                used_bullets.add(bullet)
                world.delete_entity(enemy)
                world.delete_entity(bullet)
                break


def _rect(c_t: CTransform, c_s: CSurface) -> pygame.Rect:
    return pygame.Rect(c_t.pos, c_s.area.size)
