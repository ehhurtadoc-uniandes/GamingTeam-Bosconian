"""Pruebas de los obstáculos: rocas, rocas indestructibles y minas."""
import json
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from src.create.prefab_obstacle import create_obstacle, create_obstacles
from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_collision import hitbox_center
from src.ecs.systems.s_obstacles import hit_obstacle, system_mine_blast, system_player_bullet_obstacle
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta

WORLD = pygame.Vector2(1024, 1536)
with open("assets/cfg/obstacles.json", encoding="utf-8") as f:
    OBSTACLES = json.load(f)
BULLET_INFO = {"size": {"w": 3, "h": 3}, "color": {"r": 255, "g": 255, "b": 255}, "speed": 150}


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
        # Sprite, obstáculo, hitbox y posición: sin CVelocity, nada lo mueve.
        self.assertEqual(len(self.world.components_for_entity(rock)), 4)

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
        c_t, c_s, c_h = (self.world.component_for_entity(rock, t) for t in (CTransform, CSurface, CHitBox))
        margin = OBSTACLES["rock"]["hitbox_margin"]
        self.assertEqual(c_h.layer, CollisionLayer.OBSTACLE)
        self.assertEqual(c_h.size, pygame.Vector2(c_s.area.size) - pygame.Vector2(2 * margin, 2 * margin))
        self.assertEqual(hitbox_center(c_t, c_h), pygame.Vector2(100, 100))

    def test_hitbox_de_la_mina_es_de_un_cuadro(self):
        """La mina es una tira de dos cuadros: la hitbox sale del cuadro, no de la imagen completa."""
        mine = create_obstacle(self.world, OBSTACLES, ObstacleKind.MINE, pygame.Vector2(50, 50), random.Random(0))
        c_t, c_h = (self.world.component_for_entity(mine, t) for t in (CTransform, CHitBox))
        margin = OBSTACLES["mine"]["hitbox_margin"]
        self.assertEqual(c_h.size, pygame.Vector2(16 - 2 * margin, 16 - 2 * margin))
        self.assertEqual(hitbox_center(c_t, c_h), pygame.Vector2(50, 50))

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

    def reset_score(self):
        score_config = ServiceLocator.constants_service.score_config
        ServiceLocator.game_state_service.load(ServiceLocator.configs_service.get(score_config))

    def bullet(self, center):
        return create_player_bullet(self.world, BULLET_INFO, pygame.Vector2(center), pygame.Vector2(1, 0))

    def test_bala_del_jugador_rompe_roca_y_suma_puntos(self):
        self.reset_score()
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 100), random.Random(0))
        bullet = self.bullet((100, 100))
        system_player_bullet_obstacle(self.world, OBSTACLES, WORLD)
        self.assertFalse(self.world.entity_exists(rock))
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertEqual(ServiceLocator.game_state_service.score, 10)

    def test_roca_indestructible_absorbe_la_bala(self):
        self.reset_score()
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.SOLID_ROCK, pygame.Vector2(100, 100),
                               random.Random(0))
        bullet = self.bullet((100, 100))
        system_player_bullet_obstacle(self.world, OBSTACLES, WORLD)
        self.assertTrue(self.world.entity_exists(rock))
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertEqual(ServiceLocator.game_state_service.score, 0)

    def test_bala_rompe_roca_cruzando_el_borde_del_mundo(self):
        """Roca partida por el borde izquierdo y bala que llega por el derecho: en pantalla se tocan."""
        self.reset_score()
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(2, 100), random.Random(0))
        bullet = self.bullet((WORLD.x - 2, 100))
        system_player_bullet_obstacle(self.world, OBSTACLES, WORLD)
        self.assertFalse(self.world.entity_exists(rock))
        self.assertFalse(self.world.entity_exists(bullet))

    def test_bala_que_roza_el_sprite_pero_no_la_hitbox_no_choca(self):
        rock = create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(100, 100), random.Random(0))
        c_t = self.world.component_for_entity(rock, CTransform)
        # Centro de la bala (3x3) justo en la esquina del sprite: toca el sprite, no la caja recortada.
        bullet = self.bullet(c_t.pos)
        system_player_bullet_obstacle(self.world, OBSTACLES, WORLD)
        self.assertTrue(self.world.entity_exists(rock))
        self.assertTrue(self.world.entity_exists(bullet))

    def test_una_bala_no_rompe_dos_rocas(self):
        self.reset_score()
        rocks = [create_obstacle(self.world, OBSTACLES, ObstacleKind.ROCK, pygame.Vector2(x, 100), random.Random(0))
                 for x in (98, 102)]
        self.bullet((100, 100))
        system_player_bullet_obstacle(self.world, OBSTACLES, WORLD)
        self.assertEqual(sum(self.world.entity_exists(r) for r in rocks), 1)
        self.assertEqual(ServiceLocator.game_state_service.score, 10)


if __name__ == "__main__":
    unittest.main()
