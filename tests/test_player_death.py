import os
import random
import unittest
from unittest import mock
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_enemy import create_enemy
from src.create.prefab_explosion import create_explosion_for
from src.create.prefab_obstacle import create_mine_blast, create_obstacle
from src.create.prefab_player import create_player
from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_explosion_burst import CExplosionBurst
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_player_dead import CPlayerDead
from src.ecs.components.c_player_invulnerable import CPlayerInvulnerable
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_hidden import CTagHidden
from src.ecs.systems.s_player_death import (is_vulnerable, kill_player, system_player_death,
                                            system_player_invulnerability, system_player_respawn)
from src.ecs.systems.s_camera import get_camera
from src.ecs.systems.s_player_fire import system_player_fire
from src.ecs.systems.s_player_movement import system_player_acceleration
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.defeat_scene import DefeatScene
from src.utils.wrap import wrapped_delta
from tests.test_input import key_event
from tests.test_obstacles import OBSTACLES
from tests.test_player_fire import PLAYER_INFO
from tests.test_turret import BULLET_INFO, ENEMIES_INFO

V = pygame.Vector2
RESPAWN = {"delay": 1.0, "invulnerable_time": 1.0, "blink_interval": 0.1}
# Inicio del nivel, lejos de donde muere el jugador en las pruebas (100, 100).
SPAWN = V(40, 40)


def reset_game_state():
    ServiceLocator.game_state_service.load(
        ServiceLocator.configs_service.get(ServiceLocator.constants_service.score_config))


def explosions(world):
    return [e for e, _ in world.get_component(CAnimation) if world.entity_exists(e)]


class TestMuerteDelJugador(unittest.TestCase):
    def setUp(self):
        # Las imágenes de los obstáculos necesitan una ventana.
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.addCleanup(pygame.quit)
        reset_game_state()
        self.world = esper.World()
        self.player = create_player(self.world, PLAYER_INFO, V(100, 100))

    def hit_with_enemy(self):
        return create_enemy(self.world, ENEMIES_INFO, V(100, 100), EnemyType.I)

    def test_choque_con_enemigo_mata_al_jugador_y_al_enemigo(self):
        enemy = self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertFalse(self.world.entity_exists(enemy))

    def test_choque_con_bala_enemiga_mata_al_jugador_y_a_la_bala(self):
        bullet = create_turret_bullet(self.world, BULLET_INFO, V(106, 106), V(1, 0))
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertFalse(self.world.entity_exists(bullet))

    def hit_with_obstacle(self, kind):
        return create_obstacle(self.world, OBSTACLES, kind, V(108, 108), random.Random(0))

    def test_choque_con_roca_mata_al_jugador_y_rompe_la_roca(self):
        rock = self.hit_with_obstacle(ObstacleKind.ROCK)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertFalse(self.world.entity_exists(rock))

    def test_choque_con_mina_mata_al_jugador_y_la_mina_explota(self):
        mine = self.hit_with_obstacle(ObstacleKind.MINE)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertFalse(self.world.entity_exists(mine))
        self.assertEqual(len(self.world.get_component(CMineBlast)), 1)

    def test_choque_con_roca_indestructible_mata_al_jugador_y_la_roca_sigue(self):
        rock = self.hit_with_obstacle(ObstacleKind.SOLID_ROCK)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertTrue(self.world.entity_exists(rock))

    def test_chocar_con_un_obstaculo_no_da_puntos(self):
        self.hit_with_obstacle(ObstacleKind.MINE)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(ServiceLocator.game_state_service.score, 0)

    def test_la_misma_mina_no_lo_mata_dos_veces(self):
        self.hit_with_obstacle(ObstacleKind.MINE)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        system_player_respawn(self.world, 1.01, RESPAWN, V(100, 100))
        system_player_invulnerability(self.world, 1.5, RESPAWN)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(is_vulnerable(self.world, self.player))
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_bala_del_propio_jugador_no_lo_mata(self):
        create_player_bullet(self.world, PLAYER_INFO["weapon"]["bullet"], V(106, 106), V(1, 0))
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertFalse(self.world.has_component(self.player, CPlayerDead))

    def test_sin_choque_no_pasa_nada(self):
        create_enemy(self.world, ENEMIES_INFO, V(300, 300), EnemyType.I)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(is_vulnerable(self.world, self.player))
        self.assertEqual(ServiceLocator.game_state_service.lives, 3)

    def test_pierde_una_vida(self):
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_queda_oculto_quieto_y_sin_velocidad(self):
        c_pm = self.world.component_for_entity(self.player, CPlayerMovement)
        system_player_acceleration(self.world, 2.0)
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CTagHidden))
        self.assertEqual(self.world.component_for_entity(self.player, CVelocity).vel, V(0, 0))
        self.assertEqual(c_pm.speed, 0.0)

    def test_provoca_varias_explosiones(self):
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(len(self.world.get_component(CExplosionBurst)), 1)
        self.assertEqual(len(explosions(self.world)), 1)

    def test_muerto_no_vuelve_a_perder_vidas(self):
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_muerto_no_acelera_ni_dispara(self):
        self.hit_with_enemy()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        system_player_acceleration(self.world, 1.0)
        system_player_fire(self.world)
        self.assertEqual(self.world.component_for_entity(self.player, CVelocity).vel, V(0, 0))
        self.assertEqual(self.world.component_for_entity(self.player, CPlayerWeapon).time_left, 0.0)

    def test_kill_player_directo(self):
        kill_player(self.world, self.player, RESPAWN)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_explosion_del_jugador_hereda_su_velocidad(self):
        self.world.component_for_entity(self.player, CVelocity).vel = V(30, 0)
        create_explosion_for(self.world, self.player)
        burst = self.world.get_component(CExplosionBurst)[0][0]
        self.assertEqual(self.world.component_for_entity(burst, CVelocity).vel, V(30, 0))


class TestReaparicion(unittest.TestCase):
    def setUp(self):
        reset_game_state()
        self.world = esper.World()
        self.player = create_player(self.world, PLAYER_INFO, V(100, 100))
        kill_player(self.world, self.player, RESPAWN)

    def test_no_reaparece_antes_del_retraso(self):
        self.assertFalse(system_player_respawn(self.world, 0.5, RESPAWN, SPAWN))
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))
        self.assertTrue(self.world.has_component(self.player, CTagHidden))

    def test_reaparece_despues_del_retraso_en_el_inicio_del_nivel(self):
        self.assertFalse(system_player_respawn(self.world, 1.01, RESPAWN, SPAWN))
        self.assertFalse(self.world.has_component(self.player, CPlayerDead))
        self.assertFalse(self.world.has_component(self.player, CTagHidden))
        self.assertEqual(self.world.component_for_entity(self.player, CTransform).pos, SPAWN)

    def test_muerto_no_se_mueve_al_inicio_antes_del_retraso(self):
        system_player_respawn(self.world, 0.5, RESPAWN, SPAWN)
        self.assertEqual(self.world.component_for_entity(self.player, CTransform).pos, V(100, 100))

    def test_reaparece_invulnerable_y_arranca_despacio(self):
        system_player_respawn(self.world, 1.01, RESPAWN, SPAWN)
        self.assertTrue(self.world.has_component(self.player, CPlayerInvulnerable))
        self.assertEqual(self.world.component_for_entity(self.player, CPlayerMovement).speed, 0.0)

    def test_invulnerable_no_muere_ni_mata(self):
        system_player_respawn(self.world, 1.01, RESPAWN, SPAWN)
        lives = ServiceLocator.game_state_service.lives
        enemy = create_enemy(self.world, ENEMIES_INFO, V(100, 100), EnemyType.I)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(ServiceLocator.game_state_service.lives, lives)
        self.assertTrue(self.world.entity_exists(enemy))
        self.assertFalse(self.world.has_component(self.player, CPlayerDead))

    def test_la_invulnerabilidad_termina_y_vuelve_a_ser_vulnerable(self):
        system_player_respawn(self.world, 1.01, RESPAWN, SPAWN)
        for _ in range(11):
            system_player_invulnerability(self.world, 0.1, RESPAWN)
        self.assertFalse(self.world.has_component(self.player, CPlayerInvulnerable))
        self.assertFalse(self.world.has_component(self.player, CTagHidden))
        self.assertTrue(is_vulnerable(self.world, self.player))

    def test_parpadea_mientras_es_invulnerable(self):
        system_player_respawn(self.world, 1.01, RESPAWN, SPAWN)
        system_player_invulnerability(self.world, 0.05, RESPAWN)
        self.assertFalse(self.world.has_component(self.player, CTagHidden))
        system_player_invulnerability(self.world, 0.1, RESPAWN)
        self.assertTrue(self.world.has_component(self.player, CTagHidden))
        system_player_invulnerability(self.world, 0.1, RESPAWN)
        self.assertFalse(self.world.has_component(self.player, CTagHidden))

    def test_vuelve_a_morir_despues_de_la_invulnerabilidad(self):
        system_player_respawn(self.world, 1.01, RESPAWN, SPAWN)
        system_player_invulnerability(self.world, 1.5, RESPAWN)
        create_enemy(self.world, ENEMIES_INFO, SPAWN, EnemyType.I)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertEqual(ServiceLocator.game_state_service.lives, 1)


class TestSinVidas(unittest.TestCase):
    def setUp(self):
        reset_game_state()
        ServiceLocator.game_state_service.lives = 0
        self.world = esper.World()
        self.player = create_player(self.world, PLAYER_INFO, V(100, 100))

    def test_con_cero_de_reserva_morir_es_fin_de_la_partida(self):
        kill_player(self.world, self.player, RESPAWN)
        self.assertTrue(self.world.component_for_entity(self.player, CPlayerDead).game_over)
        self.assertEqual(ServiceLocator.game_state_service.lives, 0)

    def test_avisa_el_fin_solo_despues_del_retraso_y_no_reaparece(self):
        kill_player(self.world, self.player, RESPAWN)
        self.assertFalse(system_player_respawn(self.world, 0.5, RESPAWN, SPAWN))
        self.assertTrue(system_player_respawn(self.world, 0.6, RESPAWN, SPAWN))
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))

    def test_con_vidas_de_reserva_no_es_fin(self):
        reset_game_state()
        kill_player(self.world, self.player, RESPAWN)
        self.assertFalse(self.world.component_for_entity(self.player, CPlayerDead).game_over)


class TestMuerteEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        reset_game_state()
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()
        self.world = self.scene.ecs_world
        for obstacle, _ in self.world.get_component(CObstacle):
            self.world.delete_entity(obstacle)
        self.world._clear_dead_entities()
        self.world.component_for_entity(self.scene._player_entity, CTransform).pos = V(600, 600)
        self.respawn = self.scene._respawn_info
        self.constants = ServiceLocator.constants_service

    def run_scene(self, seconds):
        for _ in range(int(seconds * 60)):
            self.scene.simulate(1 / 60)
            self.scene.do_draw(self.engine.screen)

    def test_config_real_tiene_respawn(self):
        for key in ("delay", "invulnerable_time", "blink_interval"):
            self.assertGreater(self.respawn[key], 0)

    def test_l_mata_al_jugador_y_pierde_una_vida(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)
        self.assertTrue(self.world.has_component(self.scene._player_entity, CPlayerDead))

    def test_l_no_mata_dos_veces_seguidas(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_el_jugador_reaparece(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.run_scene(self.respawn["delay"] + 0.2)
        player = self.scene._player_entity
        self.assertFalse(self.world.has_component(player, CPlayerDead))
        self.assertTrue(self.world.has_component(player, CPlayerInvulnerable))
        self.assertIsNone(self.engine._scene_name_to_switch)

    def test_el_jugador_reaparece_en_el_inicio_del_nivel(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.run_scene(self.respawn["delay"] + 0.05)
        pos = self.world.component_for_entity(self.scene._player_entity, CTransform).pos
        self.assertLess(pos.distance_to(self.scene._player_spawn_pos), 5)

    def test_la_camara_sigue_al_jugador_en_el_mismo_paso_en_que_reaparece(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        player = self.scene._player_entity
        while self.world.has_component(player, CPlayerDead):
            self.scene.simulate(1 / 60)
        c_t = self.world.component_for_entity(player, CTransform)
        c_s = self.world.component_for_entity(player, CSurface)
        center = c_t.pos + V(c_s.area.size) / 2
        camera = get_camera(self.world)
        self.assertLess(wrapped_delta(camera.center, center, camera.world_size).length(), 1)

    def test_los_enemigos_que_salen_al_reaparecer_no_aparecen_en_pantalla(self):
        # Muere a una pantalla a la derecha del inicio: la vista vieja y la nueva se tocan.
        player = self.scene._player_entity
        view_w = get_camera(self.world).viewport.w
        self.world.component_for_entity(player, CTransform).pos.update(self.scene._player_spawn_pos + V(view_w, 0))
        self.scene.simulate(1 / 60)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.world.component_for_entity(player, CPlayerDead).remaining = 0.0
        for _, c_sp in self.world.get_component(CEnemySpawner):
            c_sp.time_to_spawn = 0.0
            c_sp.active = True
            c_sp.max_alive = 1000
        before = {e for e, _ in self.world.get_component(CEnemy)}

        def left_side(view_size, size, margin, rng=None):
            return V(-size.x - margin, view_size.y / 2)

        # El enemigo sale por el borde izquierdo de la vista que recibe el spawner.
        with mock.patch("src.ecs.systems.s_enemy_spawner.offscreen_offset", left_side):
            self.scene.simulate(1 / 60)
        camera = get_camera(self.world)
        new = [e for e, _ in self.world.get_component(CEnemy) if e not in before]
        self.assertTrue(new)
        for enemy in new:
            c_t = self.world.component_for_entity(enemy, CTransform)
            c_s = self.world.component_for_entity(enemy, CSurface)
            delta = wrapped_delta(camera.center, c_t.pos + V(c_s.area.size) / 2, camera.world_size)
            self.assertGreater(abs(delta.x), camera.viewport.w / 2)

    def test_sin_vidas_pasa_a_la_escena_de_derrota(self):
        ServiceLocator.game_state_service.lives = 0
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.run_scene(self.respawn["delay"] - 0.2)
        self.assertIsNone(self.engine._scene_name_to_switch)
        self.run_scene(0.4)
        self.assertEqual(self.engine._scene_name_to_switch, "defeat")

    def blast_info(self):
        obstacles = ServiceLocator.configs_service.get(self.constants.obstacles_config)
        return obstacles["mine"]["blast"]

    def player_center(self):
        player = self.scene._player_entity
        return (self.world.component_for_entity(player, CTransform).pos
                + V(self.world.component_for_entity(player, CSurface).area.size) / 2)

    def test_la_explosion_de_una_mina_mata_al_jugador(self):
        create_mine_blast(self.world, self.blast_info(), self.player_center())
        self.scene.simulate(1 / 60)
        self.assertTrue(self.world.has_component(self.scene._player_entity, CPlayerDead))
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_una_explosion_lejana_no_mata_al_jugador(self):
        create_mine_blast(self.world, self.blast_info(), self.player_center() + V(200, 0))
        self.scene.simulate(1 / 60)
        self.assertFalse(self.world.has_component(self.scene._player_entity, CPlayerDead))

    def test_la_explosion_de_una_mina_no_mata_al_jugador_invulnerable(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.run_scene(self.respawn["delay"] + 0.2)
        lives = ServiceLocator.game_state_service.lives
        create_mine_blast(self.world, self.blast_info(), self.player_center())
        self.scene.simulate(1 / 60)
        self.assertEqual(ServiceLocator.game_state_service.lives, lives)

    def test_una_explosion_larga_no_resta_mas_de_una_vida(self):
        create_mine_blast(self.world, self.blast_info(), self.player_center())
        for _ in range(30):
            self.scene.simulate(1 / 60)
        self.assertEqual(ServiceLocator.game_state_service.lives, 2)

    def test_en_pausa_el_retraso_no_corre(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.scene.toggle_pause()
        self.run_scene(self.respawn["delay"] + 1.0)
        self.assertTrue(self.world.has_component(self.scene._player_entity, CPlayerDead))

    def test_los_enemigos_siguen_ahi_mientras_el_jugador_esta_muerto(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_l))
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_1))
        self.run_scene(0.5)
        self.assertTrue(self.world.entity_exists(self.scene._player_entity))

    def test_escena_de_derrota_existe_y_vuelve_al_titulo(self):
        defeat = self.engine._scenes["defeat"]
        self.assertIsInstance(defeat, DefeatScene)
        defeat.start()
        # Z acepta la opción elegida (SI = continuar); Escape elige NO y vuelve al título (#37).
        # Al entrar no se acepta nada durante input_delay, así que primero se deja pasar ese tiempo.
        for _ in range(60):
            defeat.simulate(1 / 60)
        defeat.process_events(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))
        self.assertEqual(self.engine._scene_name_to_switch, "title")
        defeat.simulate(1 / 60)
        defeat.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
