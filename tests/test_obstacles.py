"""Pruebas de los obstáculos: rocas, rocas indestructibles y minas."""
import json
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from src.create.prefab_obstacle import create_obstacle, create_obstacles
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_animation import system_animation
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.ecs.systems.s_obstacles import (hit_obstacle, obstacle_hitbox, system_mine_blast,
                                        system_player_bullet_obstacle)
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta

WORLD = pygame.Vector2(1024, 1536)
with open("assets/cfg/obstacles.json", encoding="utf-8") as f:
    OBSTACLES = json.load(f)


class TestObstacles(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.addCleanup(pygame.quit)
        self.world = esper.World()

    def center(self, entity):
        c_t = self.world.component_for_entity(entity, CTransform)
        c_s = self.world.component_for_entity(entity, CSurface)
        return c_t.pos + pygame.Vector2(c_s.area.size) / 2

    def test_obstaculo_queda_centrado_y_sin_velocidad(self):
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 200), random.Random(0))
        self.assertEqual(self.center(rock), pygame.Vector2(100, 200))
        self.assertEqual(len(self.world.components_for_entity(rock)), 3)

    def test_mina_animada_muestra_un_cuadro(self):
        mine = create_obstacle(self.world, OBSTACLES, ObstacleKind.MINE, pygame.Vector2(50, 50), random.Random(0))
        c_s = self.world.component_for_entity(mine, CSurface)
        self.assertEqual(c_s.area.size, (16, 16))
        system_animation(self.world, 0.3)
        self.assertEqual(self.world.component_for_entity(mine, CAnimation).current_frame, 1)
        self.assertEqual(c_s.area.x, 16)

    def test_create_obstacles_cantidad_y_distancia_minima(self):
        level = {"obstacles": {"seed": 3, "min_distance": 40, "rock": 10, "solid_rock": 3, "mine": 5}}
        avoid = [pygame.Vector2(500, 500)]
        created = create_obstacles(self.world, OBSTACLES, level, WORLD, avoid)
        self.assertEqual(len(created), 18)
        centers = [self.center(e) for e in created]
        for i, a in enumerate(centers):
            self.assertGreaterEqual(wrapped_delta(a, avoid[0], WORLD).length(), 40)
            for b in centers[i + 1:]:
                self.assertGreaterEqual(wrapped_delta(a, b, WORLD).length(), 40)

    def test_misma_semilla_mismo_nivel(self):
        level = {"obstacles": {"seed": 7, "rock": 5}}
        a = [self.center(e) for e in create_obstacles(self.world, OBSTACLES, level, WORLD, [])]
        b = [self.center(e) for e in create_obstacles(esper.World(), OBSTACLES, level, WORLD, [])]
        self.assertEqual(a, b)

    def test_hitbox_mas_pequena_que_el_sprite(self):
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 100), random.Random(0))
        c_t, c_s, c_obs = (self.world.component_for_entity(rock, t) for t in (CTransform, CSurface, CObstacle))
        hitbox = obstacle_hitbox(c_t, c_s, c_obs)
        self.assertEqual(hitbox.w, c_s.area.w - 2 * c_obs.hitbox_margin)
        self.assertEqual(hitbox.center, pygame.Rect(c_t.pos, c_s.area.size).center)

    def test_roca_se_destruye_y_da_puntos(self):
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 100), random.Random(0))
        self.assertEqual(hit_obstacle(self.world, rock, OBSTACLES), 10)
        self.assertFalse(self.world.entity_exists(rock))

    def test_roca_indestructible_no_se_rompe(self):
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.SOLID_ROCK, pygame.Vector2(100, 100), random.Random(0))
        self.assertEqual(hit_obstacle(self.world, rock, OBSTACLES), 0)
        self.assertTrue(self.world.entity_exists(rock))

    def test_mina_explota_mata_enemigo_cercano_y_al_jugador(self):
        mine = create_obstacle(self.world, OBSTACLES, ObstacleKind.MINE, pygame.Vector2(100, 100), random.Random(0))
        near = self.world.create_entity(CTransform(pygame.Vector2(106, 96)),
                                        CSurface(pygame.Vector2(8, 8), pygame.Color(0, 0, 0)), CEnemy(EnemyType.I))
        far = self.world.create_entity(CTransform(pygame.Vector2(300, 300)),
                                       CSurface(pygame.Vector2(8, 8), pygame.Color(0, 0, 0)), CEnemy(EnemyType.I))
        self.assertEqual(hit_obstacle(self.world, mine, OBSTACLES), 20)
        self.world._clear_dead_entities()
        self.assertTrue(system_mine_blast(self.world, WORLD, pygame.Vector2(110, 110)))
        self.assertFalse(self.world.entity_exists(near))
        self.assertTrue(self.world.entity_exists(far))

    def test_explosion_se_borra_al_terminar(self):
        mine = create_obstacle(self.world, OBSTACLES, ObstacleKind.MINE, pygame.Vector2(100, 100), random.Random(0))
        hit_obstacle(self.world, mine, OBSTACLES)
        self.world._clear_dead_entities()
        for _ in range(60):
            system_animation(self.world, 1 / 60)
            system_mine_blast(self.world, WORLD, pygame.Vector2(900, 900))
            self.world._clear_dead_entities()
        self.assertEqual(self.world.get_component(CMineBlast), [])

    def test_bala_del_jugador_rompe_roca_y_suma_puntos(self):
        score_config = ServiceLocator.constants_service.score_config
        ServiceLocator.game_state_service.load(ServiceLocator.configs_service.get(score_config))
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 100), random.Random(0))
        bullet = self.world.create_entity(CTransform(pygame.Vector2(99, 99)),
                                          CSurface(pygame.Vector2(2, 2), pygame.Color(255, 255, 255)),
                                          CTagPlayerBullet())
        system_player_bullet_obstacle(self.world, OBSTACLES)
        self.assertFalse(self.world.entity_exists(rock))
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertEqual(ServiceLocator.game_state_service.score, 10)


if __name__ == "__main__":
    unittest.main()
