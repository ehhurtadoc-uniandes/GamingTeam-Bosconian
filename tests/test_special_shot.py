import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_player import create_player
from src.create.prefab_special_message import create_special_shot_message
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_special_shot import CSpecialShot
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_player_death import kill_player, system_player_respawn
from src.ecs.systems.s_player_fire import fan_directions, system_player_fire
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_input import key_event
from tests.test_player_death import RESPAWN, SPAWN, reset_game_state
from tests.test_player_fire import PLAYER_INFO

V = pygame.Vector2
SPECIAL_INFO = {
    "forward_bullets": 3,
    "spread_degrees": 20,
    "message_duration": 2.0,
    "message": {"text": "TRIPLE SHOT", "anchor": {"x": 96, "y": 40}, "alignment": "CENTER",
                "color": {"r": 255, "g": 255, "b": 255}},
}
INFO = dict(PLAYER_INFO, special_shot=SPECIAL_INFO)


def bullet_velocities(world):
    return [world.component_for_entity(e, CVelocity).vel for e, _ in world.get_component(CTagPlayerBullet)
            if world.entity_exists(e)]


class TestFanDirections(unittest.TestCase):
    def test_una_bala_va_recta(self):
        self.assertEqual(fan_directions(V(1, 0), 1, 20), [V(1, 0)])

    def test_tres_balas_central_y_dos_a_los_lados(self):
        directions = fan_directions(V(1, 0), 3, 20)
        self.assertEqual(directions[1], V(1, 0))
        self.assertAlmostEqual(directions[0].angle_to(directions[1]), -directions[2].angle_to(directions[1]))
        self.assertAlmostEqual(abs(directions[0].angle_to(directions[1])), 20)

    def test_las_direcciones_son_unitarias(self):
        for direction in fan_directions(V(0, -1), 3, 15):
            self.assertAlmostEqual(direction.length(), 1.0)

    def test_sigue_la_direccion_base(self):
        directions = fan_directions(V(0, -1), 3, 20)
        self.assertEqual(directions[1], V(0, -1))


class TestDisparoEspecial(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_sin_habilidad_dispara_dos_balas(self):
        create_player(self.world, INFO, V(100, 100))
        system_player_fire(self.world)
        self.assertEqual(len(bullet_velocities(self.world)), 2)

    def test_con_habilidad_dispara_cuatro_balas(self):
        create_player(self.world, INFO, V(100, 100), special_shot=True)
        system_player_fire(self.world)
        self.assertEqual(len(bullet_velocities(self.world)), 4)

    def test_tres_van_al_frente_y_una_atras(self):
        create_player(self.world, INFO, V(100, 100), special_shot=True)
        system_player_fire(self.world)
        velocities = bullet_velocities(self.world)
        forward = [v for v in velocities if v.x > 0]
        backward = [v for v in velocities if v.x < 0]
        self.assertEqual(len(forward), 3)
        self.assertEqual(len(backward), 1)
        self.assertEqual(backward[0], V(-100, 0))

    def test_las_balas_del_frente_se_abren_en_abanico(self):
        create_player(self.world, INFO, V(100, 100), special_shot=True)
        system_player_fire(self.world)
        forward = sorted((v for v in bullet_velocities(self.world) if v.x > 0), key=lambda v: v.y)
        self.assertLess(forward[0].y, 0)
        self.assertAlmostEqual(forward[1].y, 0)
        self.assertGreater(forward[2].y, 0)
        for v in forward:
            self.assertAlmostEqual(v.length(), 100)

    def test_la_bala_trasera_sigue_siendo_una_sola_y_recta(self):
        player = create_player(self.world, INFO, V(100, 100), special_shot=True)
        self.world.component_for_entity(player, CPlayerMovement).direction = V(0, -1)
        system_player_fire(self.world)
        back = [v for v in bullet_velocities(self.world) if v.y > 0]
        self.assertEqual(len(back), 1)
        self.assertAlmostEqual(back[0].x, 0)
        self.assertAlmostEqual(back[0].y, 100)

    def test_respeta_el_cooldown(self):
        create_player(self.world, INFO, V(100, 100), special_shot=True)
        system_player_fire(self.world)
        system_player_fire(self.world)
        self.assertEqual(len(bullet_velocities(self.world)), 4)

    def test_la_cantidad_de_balas_viene_de_la_config(self):
        info = dict(INFO, special_shot=dict(SPECIAL_INFO, forward_bullets=5))
        create_player(self.world, info, V(100, 100), special_shot=True)
        system_player_fire(self.world)
        self.assertEqual(len(bullet_velocities(self.world)), 6)

    def test_el_jugador_lleva_el_componente_solo_si_el_nivel_lo_da(self):
        with_ability = create_player(self.world, INFO, V(0, 0), special_shot=True)
        without = create_player(self.world, INFO, V(0, 0))
        self.assertIsNotNone(self.world.try_component(with_ability, CSpecialShot))
        self.assertIsNone(self.world.try_component(without, CSpecialShot))


class TestHabilidadConMuerteYReaparicion(unittest.TestCase):
    def setUp(self):
        reset_game_state()
        self.world = esper.World()
        self.player = create_player(self.world, INFO, V(100, 100), special_shot=True)
        kill_player(self.world, self.player, RESPAWN)

    def test_muerto_no_dispara_aunque_tenga_la_habilidad(self):
        system_player_fire(self.world)
        self.assertEqual(bullet_velocities(self.world), [])

    def test_al_reaparecer_conserva_la_habilidad(self):
        system_player_respawn(self.world, RESPAWN["delay"] + 0.01, RESPAWN, SPAWN)
        self.assertIsNotNone(self.world.try_component(self.player, CSpecialShot))
        system_player_fire(self.world)
        self.assertEqual(len(bullet_velocities(self.world)), 4)


class TestMensajeDeHabilidad(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)

    def test_el_mensaje_es_texto_de_interfaz_con_su_duracion(self):
        world = esper.World()
        message = create_special_shot_message(world, SPECIAL_INFO)
        self.assertEqual(world.component_for_entity(message, CText).text, "TRIPLE SHOT")
        self.assertTrue(world.has_component(message, CTagUI))
        self.assertTrue(world.has_component(message, CTagHideOnPause))
        self.assertEqual(world.component_for_entity(message, CLifetime).remaining, 2.0)

    def test_el_mensaje_desaparece_pasado_su_tiempo(self):
        world = esper.World()
        message = create_special_shot_message(world, SPECIAL_INFO)
        system_lifetime(world, 1.9)
        self.assertTrue(world.entity_exists(message))
        system_lifetime(world, 0.2)
        self.assertFalse(world.entity_exists(message))

    def test_config_real_tiene_la_habilidad_y_el_mensaje(self):
        info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.player_config)["special_shot"]
        self.assertEqual(info["forward_bullets"], 3)
        self.assertGreater(info["spread_degrees"], 0)
        self.assertGreater(info["message_duration"], 0)
        self.assertTrue(info["message"]["text"])


class TestHabilidadEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.constants = ServiceLocator.constants_service

    def level(self):
        path = ServiceLocator.configs_service.get(self.constants.levels_config)["levels"][0]
        return ServiceLocator.configs_service.get(path)

    def messages(self):
        return [e for e, _ in self.scene.ecs_world.get_component(CLifetime)
                if self.scene.ecs_world.has_component(e, CText)]

    def test_el_nivel_real_da_la_habilidad(self):
        self.assertTrue(self.level()["special"])

    def test_nivel_con_habilidad_dispara_cuatro_balas_y_muestra_el_mensaje(self):
        self.scene.start()
        self.scene.skip_blast_off()
        self.assertEqual(len(self.messages()), 1)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(len(bullet_velocities(self.scene.ecs_world)), 4)

    def test_nivel_sin_habilidad_dispara_dos_balas_y_no_muestra_mensaje(self):
        level = self.level()
        level["special"] = False
        self.addCleanup(level.__setitem__, "special", True)
        self.scene.start()
        self.scene.skip_blast_off()
        self.assertEqual(self.messages(), [])
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(len(bullet_velocities(self.scene.ecs_world)), 2)

    def test_nivel_sin_la_clave_special_no_da_la_habilidad(self):
        level = self.level()
        del level["special"]
        self.addCleanup(level.__setitem__, "special", True)
        self.scene.start()
        self.scene.skip_blast_off()
        self.assertEqual(self.messages(), [])
        self.assertIsNone(self.scene.ecs_world.try_component(self.scene._player_entity, CSpecialShot))

    def test_el_mensaje_se_borra_con_el_tiempo_y_se_dibuja(self):
        self.scene.start()
        self.scene.skip_blast_off()
        self.scene.do_draw(self.engine.screen)
        duration = ServiceLocator.configs_service.get(self.constants.player_config)["special_shot"]["message_duration"]
        for _ in range(int((duration + 0.5) * 60)):
            self.scene.simulate(1 / 60)
        self.assertEqual(self.messages(), [])

    def test_en_pausa_el_mensaje_no_corre(self):
        self.scene.start()
        self.scene.skip_blast_off()
        self.scene.toggle_pause()
        for _ in range(5 * 60):
            self.scene.simulate(1 / 60)
        self.assertEqual(len(self.messages()), 1)


if __name__ == "__main__":
    unittest.main()
