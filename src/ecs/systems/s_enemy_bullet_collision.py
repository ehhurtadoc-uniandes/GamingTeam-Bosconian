import esper
import pygame

from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy_bullet import CTagEnemyBullet


def system_enemy_bullet_collision(world: esper.World) -> None:
    """Un enemigo que choca con una bala de torreta muere, y la bala también (LC-BAS-05.1).

    No suma puntos: no lo mató el jugador. Las bases no tienen CEnemy, así que
    las balas las atraviesan. Mientras no esté la HitBox (#15) se usa el
    rectángulo de CTransform + CSurface; la explosión llegará con #16.

    delete_entity marca la entidad como muerta en el acto (entity_exists da False),
    aunque se borre al final del paso. Así una bala que ya mató a un enemigo, o
    una que venció en system_lifetime, no vuelve a chocar.
    """
    bullets = [(entity, _rect(c_t, c_s))
               for entity, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagEnemyBullet)]
    for enemy, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CEnemy):
        if not world.entity_exists(enemy):
            continue
        enemy_rect = _rect(c_t, c_s)
        for bullet, bullet_rect in bullets:
            if world.entity_exists(bullet) and enemy_rect.colliderect(bullet_rect):
                world.delete_entity(enemy)
                world.delete_entity(bullet)
                break


def _rect(c_t: CTransform, c_s: CSurface) -> pygame.Rect:
    return pygame.Rect(c_t.pos, c_s.area.size)
