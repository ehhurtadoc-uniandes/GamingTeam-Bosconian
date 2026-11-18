"""Pruebas de la pausa (#35). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground
from src.ecs.components.tags.c_tag_hidden import CTagHidden
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_pause import system_pause_visibility
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_starfield import system_star_blink
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayState

WHITE = pygame.Color(255, 255, 255)
BLINK = {"on": {"min": 1.0, "max": 1.0}, "off": {"min": 0.5, "max": 0.5}}
DT = 1 / 60


def make_square(world, pos=(10, 10), *tags):
    surf = CSurface(pygame.Vector2(4, 4), WHITE)
    return world.create_entity(CTransform(pygame.Vector2(pos)), surf, *tags)


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


class TestPauseVisibility(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.thing = make_square(self.world)
        self.star = make_square(self.world, (0, 0), CTagBackground())
        self.hud = make_square(self.world, (0, 0), CTagUI())
        self.minimap = make_square(self.world, (0, 0), CTagUI(), CTagHideOnPause())

    def hidden(self, entity):
        return self.world.has_component(entity, CTagHidden)

    def test_pausar_esconde_el_mundo_y_el_minimapa(self):
        system_pause_visibility(self.world, paused=True)
        self.assertTrue(self.hidden(self.thing))
        self.assertTrue(self.hidden(self.minimap))

    def test_pausar_deja_las_estrellas_y_el_hud(self):
        system_pause_visibility(self.world, paused=True)
        self.assertFalse(self.hidden(self.star))
        self.assertFalse(self.hidden(self.hud))

    def test_reanudar_vuelve_a_mostrar_todo(self):
        system_pause_visibility(self.world, paused=True)
        system_pause_visibility(self.world, paused=False)
        for entity in (self.thing, self.star, self.hud, self.minimap):
            self.assertFalse(self.hidden(entity))

    def test_reanudar_no_muestra_lo_que_ya_estaba_escondido(self):
        self.world.add_component(self.thing, CTagHidden())
        system_pause_visibility(self.world, paused=True)
        system_pause_visibility(self.world, paused=False)
        self.assertTrue(self.hidden(self.thing))
        self.assertFalse(self.hidden(self.minimap))

    def test_lo_escondido_no_se_dibuja(self):
        screen = pygame.Surface((32, 32))
        self.world.add_component(self.thing, CTagHidden())
        system_rendering(self.world, screen)
        self.assertEqual(screen.get_at((11, 11)), pygame.Color(0, 0, 0))
        self.world.remove_component(self.thing, CTagHidden)
        system_rendering(self.world, screen)
        self.assertEqual(screen.get_at((11, 11)), WHITE)


class TestStarBlink(unittest.TestCase):
    def test_parpadea_sin_moverse(self):
        world = esper.World()
        star = world.create_entity(CTransform(pygame.Vector2(5, 5)),
                                   CSurface(pygame.Vector2(1, 1), WHITE), CStar(0.5, 0.01))
        system_star_blink(world, 0.02, BLINK)
        self.assertFalse(world.component_for_entity(star, CStar).visible)
        self.assertEqual(world.component_for_entity(star, CSurface).surf.get_alpha(), 0)
        self.assertEqual(world.component_for_entity(star, CTransform).pos, pygame.Vector2(5, 5))


class TestPlayScenePause(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.world = self.scene.ecs_world
        self.player = self.world.get_component(CTagPlayer)[0][0]

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def player_pos(self):
        return pygame.Vector2(self.world.component_for_entity(self.player, CTransform).pos)

    def pause_texts(self):
        return [c.text for _, c in self.world.get_component(CText) if c.text == "JUEGO PAUSADO"]

    def test_p_pausa_y_vuelve_a_reanudar(self):
        self.press(pygame.K_p)
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.assertEqual(self.pause_texts(), ["JUEGO PAUSADO"])
        self.press(pygame.K_p)
        self.assertEqual(self.scene.state, PlayState.PLAYING)
        self.assertEqual(self.pause_texts(), [])

    def test_escape_tambien_pausa(self):
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.scene.state, PlayState.PAUSED)

    def test_en_pausa_jugador_y_enemigos_desaparecen_y_las_estrellas_no(self):
        self.press(pygame.K_1)
        self.press(pygame.K_p)
        enemy = self.world.get_component(CEnemy)[0][0]
        self.assertTrue(self.world.has_component(self.player, CTagHidden))
        self.assertTrue(self.world.has_component(enemy, CTagHidden))
        for star, _ in self.world.get_component(CStar):
            self.assertFalse(self.world.has_component(star, CTagHidden))
        self.scene.do_draw(self.engine.screen)

    def test_en_pausa_nada_se_mueve_pero_las_estrellas_brillan(self):
        self.scene.simulate(DT)
        self.press(pygame.K_p)
        before = self.player_pos()
        stars = {e: pygame.Vector2(c.pos) for e, (c, _) in self.world.get_components(CTransform, CStar)}
        blinks = {e: c.visible for e, c in self.world.get_component(CStar)}
        for _ in range(round(3 / DT)):
            self.scene.simulate(DT)
        self.assertEqual(self.player_pos(), before)
        for entity, pos in stars.items():
            self.assertEqual(self.world.component_for_entity(entity, CTransform).pos, pos)
        changed = [e for e, c in self.world.get_component(CStar) if c.visible != blinks[e]]
        self.assertTrue(changed)

    def test_en_pausa_no_aparecen_enemigos(self):
        self.press(pygame.K_p)
        self.press(pygame.K_1)
        for _ in range(round(6 / DT)):
            self.scene.simulate(DT)
        self.assertEqual(self.world.get_component(CEnemy), [])

    def test_al_reanudar_el_jugador_sigue_donde_estaba_y_se_mueve(self):
        self.press(pygame.K_p)
        before = self.player_pos()
        self.press(pygame.K_p)
        self.assertFalse(self.world.has_component(self.player, CTagHidden))
        self.assertEqual(self.player_pos(), before)
        self.scene.simulate(DT)
        self.scene.simulate(DT)
        self.assertNotEqual(self.player_pos(), before)

    def test_perder_el_foco_pausa_y_no_reanuda(self):
        focus_lost = pygame.event.Event(pygame.WINDOWFOCUSLOST)
        self.scene.process_events(focus_lost)
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.scene.process_events(focus_lost)
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.assertEqual(self.pause_texts(), ["JUEGO PAUSADO"])

    def test_flecha_presionada_en_pausa_cuenta_al_reanudar(self):
        self.press(pygame.K_p)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_RIGHT))
        self.press(pygame.K_p)
        direction = self.world.component_for_entity(self.player, CPlayerMovement).direction
        self.assertEqual(direction, pygame.Vector2(1, 0))


class TestPauseMenu(TestPlayScenePause):
    """Menú de la pausa: el mismo estilo de menú que el título (LC-ESC-04.3.5)."""

    def test_al_pausar_se_ve_el_menu(self):
        self.press(pygame.K_p)
        texts = {c.text for _, c in self.world.get_component(CText)}
        self.assertTrue({"CONTINUAR", "INSTRUCCIONES", "CREDITOS", "SALIR AL TITULO"} <= texts)
        self.scene.simulate(DT)
        self.scene.do_draw(self.engine.screen)

    def test_continuar_reanuda_sin_disparar(self):
        self.press(pygame.K_p)
        self.press(pygame.K_z)
        self.assertEqual(self.scene.state, PlayState.PLAYING)
        # Z también es PLAYER_FIRE: el mismo toque que reanuda no debe disparar.
        self.assertEqual(self.world.get_component(CTagPlayerBullet), [])
        self.assertEqual(self.menu_texts(), set())

    def test_escape_reanuda_una_sola_vez(self):
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.scene.state, PlayState.PLAYING)

    def test_instrucciones_en_pausa_y_volver_al_menu(self):
        self.press(pygame.K_p)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        self.assertEqual(self.scene.state, PlayState.PAUSED_INFO)
        self.assertIn("Z: DISPARAR", self.all_texts())
        self.assertNotIn("CONTINUAR", self.all_texts())
        # Escape es PAUSE y MENU_BACK: vuelve al menú una sola vez, no reanuda.
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.assertNotIn("Z: DISPARAR", self.all_texts())
        self.assertEqual(self.scene._pause_selected, 1)

    def test_creditos_en_pausa(self):
        self.press(pygame.K_p)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertIn("ESTEBAN LEAL", self.all_texts())
        self.press(pygame.K_z)
        self.assertEqual(self.scene.state, PlayState.PAUSED)

    def test_en_pausa_el_mundo_sigue_quieto_y_escondido_mientras_se_leen_instrucciones(self):
        self.press(pygame.K_p)
        before = self.player_pos()
        self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        for _ in range(30):
            self.scene.simulate(DT)
        self.assertEqual(self.player_pos(), before)
        self.assertTrue(self.world.has_component(self.player, CTagHidden))

    def test_salir_al_titulo(self):
        self.press(pygame.K_p)
        self.press(pygame.K_UP)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "title")

    def all_texts(self):
        return {c.text for _, c in self.world.get_component(CText)}

    def menu_texts(self):
        return self.all_texts() & {"CONTINUAR", "INSTRUCCIONES", "CREDITOS", "SALIR AL TITULO"}


if __name__ == "__main__":
    unittest.main()
