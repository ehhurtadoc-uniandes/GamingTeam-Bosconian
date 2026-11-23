import glob
import json
import os
import random
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_enemy import create_enemy
from src.create.prefab_hud import create_ability_hud
from src.create.prefab_minimap import create_minimap
from src.create.prefab_pickup import create_pickup, create_pickup_spawner
from src.create.prefab_player import create_player
from src.ecs.components.c_enemy import CEnemy, EnemyType
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
from src.ecs.components.tags.c_tag_shield_aura import CTagShieldAura
from src.ecs.systems.s_minimap import system_minimap
from src.ecs.systems.s_player_ability import (pickup_position, system_ability_hud, system_pickup_collection,
                                              system_pickup_spawner, system_player_ability,
                                              system_player_ability_activate)
from src.ecs.systems.s_player_death import is_vulnerable, kill_player, system_player_death
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_input import key_event
from tests.test_obstacles import OBSTACLES
from tests.test_player_death import RESPAWN, reset_game_state

V = pygame.Vector2
WORLD = V(1024, 1536)


def setUpModule():
    pygame.display.init()
    pygame.display.set_mode((1, 1))


def player_info():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.player_config)


def ability_info():
    return player_info()["ability"]


def make_player(charges=0, pos=V(100, 100)):
    world = esper.World()
    player = create_player(world, player_info(), pos)
    world.component_for_entity(player, CPlayerAbility).charges = charges
    return world, player


def pickups(world):
    return [e for e, _ in world.get_component(CPickup) if world.entity_exists(e)]


def auras(world):
    return [e for e, _ in world.get_component(CTagShieldAura) if world.entity_exists(e)]


def clear(world):
    world._clear_dead_entities()


class TestConfiguracion(unittest.TestCase):
    def test_la_habilidad_esta_en_la_configuracion(self):
        info = ability_info()
        for key in ("max_charges", "duration", "cooldown", "aura_image", "pickup", "hud"):
            self.assertIn(key, info)
        self.assertGreater(info["max_charges"], 0)
        self.assertGreaterEqual(info["cooldown"], info["duration"])

    def test_el_jugador_nace_con_la_habilidad_sin_cargas(self):
        world, player = make_player()
        c_ability = world.component_for_entity(player, CPlayerAbility)
        self.assertEqual(c_ability.charges, 0)
        self.assertEqual(c_ability.max_charges, ability_info()["max_charges"])

    def test_un_jugador_sin_ability_en_la_config_no_la_tiene(self):
        info = dict(player_info())
        del info["ability"]
        world = esper.World()
        player = create_player(world, info, V(10, 10))
        self.assertFalse(world.has_component(player, CPlayerAbility))

    def test_todos_los_niveles_definen_la_probabilidad_del_item(self):
        paths = glob.glob("assets/cfg/levels/level_*.json")
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with open(path, encoding="utf-8") as f:
                pickup = json.load(f)["pickup"]
            self.assertTrue(0 < pickup["chance"] <= 1, path)
            self.assertGreater(pickup["interval"], 0, path)

    def test_las_imagenes_existen(self):
        info = ability_info()
        self.assertTrue(os.path.exists(info["aura_image"]))
        self.assertTrue(os.path.exists(info["pickup"]["image"]))

    def test_x_y_el_boton_b_activan_la_habilidad(self):
        with open("assets/cfg/input.json", encoding="utf-8") as f:
            self.assertIn("x", json.load(f)[ServiceLocator.constants_service.ability_command])
        with open("assets/cfg/gamepad.json", encoding="utf-8") as f:
            self.assertIn(1, json.load(f)["buttons"][ServiceLocator.constants_service.ability_command])


class TestSpawnerDelItem(unittest.TestCase):
    def setUp(self):
        self.world, self.player = make_player()
        self.info = ability_info()["pickup"]
        self.rng = random.Random(3)

    def spawner(self, chance, interval=5.0):
        self.world.create_entity(CPickupSpawner(interval, chance))

    def run_spawner(self, seconds):
        system_pickup_spawner(self.world, seconds, self.info, WORLD, V(100, 100), self.rng)
        clear(self.world)

    def test_el_nivel_sin_pickup_no_crea_spawner(self):
        self.assertIsNone(create_pickup_spawner(self.world, {}))
        self.assertEqual(self.world.get_component(CPickupSpawner), [])

    def test_el_nivel_crea_el_spawner_con_su_probabilidad(self):
        entity = create_pickup_spawner(self.world, {"pickup": {"chance": 0.4, "interval": 12.0}})
        c_spawner = self.world.component_for_entity(entity, CPickupSpawner)
        self.assertEqual((c_spawner.chance, c_spawner.interval), (0.4, 12.0))

    def test_no_sale_antes_del_intervalo(self):
        self.spawner(1.0)
        self.run_spawner(4.9)
        self.assertEqual(pickups(self.world), [])

    def test_con_probabilidad_uno_sale_al_cumplirse_el_intervalo(self):
        self.spawner(1.0)
        self.run_spawner(5.0)
        self.assertEqual(len(pickups(self.world)), 1)

    def test_con_probabilidad_cero_nunca_sale(self):
        self.spawner(0.0)
        for _ in range(20):
            self.run_spawner(5.0)
        self.assertEqual(pickups(self.world), [])

    def test_solo_hay_un_item_a_la_vez(self):
        self.spawner(1.0)
        for _ in range(5):
            self.run_spawner(5.0)
        self.assertEqual(len(pickups(self.world)), 1)

    def test_la_probabilidad_decide_con_el_azar(self):
        self.spawner(0.5)
        fake = mock_rng([0.7, 0.2])
        system_pickup_spawner(self.world, 5.0, self.info, WORLD, V(100, 100), fake)
        self.assertEqual(pickups(self.world), [])
        system_pickup_spawner(self.world, 5.0, self.info, WORLD, V(100, 100), fake)
        self.assertEqual(len(pickups(self.world)), 1)

    def test_el_item_se_borra_solo_si_nadie_lo_recoge(self):
        from src.ecs.systems.s_lifetime import system_lifetime
        pickup = create_pickup(self.world, self.info, V(500, 500))
        system_lifetime(self.world, self.info["lifetime"] + 1)
        clear(self.world)
        self.assertFalse(self.world.entity_exists(pickup))

    def test_la_posicion_queda_lejos_del_jugador_y_de_las_bases(self):
        spawn = self.info["spawn"]
        base_pos = V(300, 300)
        self.world.create_entity(CTransform(base_pos - V(32, 32)), CSurface(V(64, 64), pygame.Color(0, 0, 0)),
                                 CTagBase())
        for seed in range(30):
            pos = pickup_position(self.world, spawn, WORLD, V(100, 100), random.Random(seed))
            self.assertGreaterEqual(wrapped(pos, V(100, 100)), spawn["min_player_distance"])
            self.assertGreaterEqual(max(abs(wrapped_vec(pos, base_pos).x) - 32,
                                        abs(wrapped_vec(pos, base_pos).y) - 32), spawn["base_margin"])

    def test_el_item_tiene_hitbox_en_su_capa(self):
        from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
        pickup = create_pickup(self.world, self.info, V(500, 500))
        self.assertEqual(self.world.component_for_entity(pickup, CHitBox).layer, CollisionLayer.PICKUP)


def wrapped_vec(a, b):
    from src.utils.wrap import wrapped_delta
    return wrapped_delta(a, b, WORLD)


def wrapped(a, b):
    return wrapped_vec(a, b).length()


class mock_rng:
    def __init__(self, values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)

    def uniform(self, a, b):
        return (a + b) / 2


class TestRecogerElItem(unittest.TestCase):
    def setUp(self):
        self.world, self.player = make_player()
        self.info = ability_info()["pickup"]

    def player_center(self):
        c_t = self.world.component_for_entity(self.player, CTransform)
        return c_t.pos + V(self.world.component_for_entity(self.player, CSurface).area.size) / 2

    def charges(self):
        return self.world.component_for_entity(self.player, CPlayerAbility).charges

    def test_tocar_el_item_da_una_carga_y_lo_borra(self):
        pickup = create_pickup(self.world, self.info, self.player_center())
        system_pickup_collection(self.world, WORLD)
        clear(self.world)
        self.assertEqual(self.charges(), 1)
        self.assertFalse(self.world.entity_exists(pickup))

    def test_un_item_lejos_no_se_recoge(self):
        pickup = create_pickup(self.world, self.info, self.player_center() + V(100, 0))
        system_pickup_collection(self.world, WORLD)
        self.assertEqual(self.charges(), 0)
        self.assertTrue(self.world.entity_exists(pickup))

    def test_con_las_cargas_llenas_el_item_se_queda(self):
        self.world.component_for_entity(self.player, CPlayerAbility).charges = ability_info()["max_charges"]
        pickup = create_pickup(self.world, self.info, self.player_center())
        system_pickup_collection(self.world, WORLD)
        clear(self.world)
        self.assertEqual(self.charges(), ability_info()["max_charges"])
        self.assertTrue(self.world.entity_exists(pickup))

    def test_el_jugador_muerto_no_lo_recoge(self):
        self.world.add_component(self.player, CPlayerDead(1.0, False))
        pickup = create_pickup(self.world, self.info, self.player_center())
        system_pickup_collection(self.world, WORLD)
        self.assertEqual(self.charges(), 0)
        self.assertTrue(self.world.entity_exists(pickup))

    def test_se_recoge_al_cruzar_el_borde_del_mundo(self):
        world, player = make_player(pos=V(1020, 100))
        create_pickup(world, self.info, V(2, 112))
        system_pickup_collection(world, WORLD)
        self.assertEqual(world.component_for_entity(player, CPlayerAbility).charges, 1)


class TestActivarElEscudo(unittest.TestCase):
    def setUp(self):
        self.info = ability_info()

    def test_sin_cargas_no_se_activa(self):
        world, player = make_player(charges=0)
        self.assertFalse(system_player_ability_activate(world, self.info))
        self.assertFalse(world.has_component(player, CShield))

    def test_con_carga_se_activa_y_la_gasta(self):
        world, player = make_player(charges=2)
        self.assertTrue(system_player_ability_activate(world, self.info))
        self.assertTrue(world.has_component(player, CShield))
        self.assertEqual(world.component_for_entity(player, CPlayerAbility).charges, 1)
        self.assertEqual(len(auras(world)), 1)

    def test_mientras_dura_no_se_gasta_otra_carga(self):
        world, player = make_player(charges=2)
        system_player_ability_activate(world, self.info)
        self.assertFalse(system_player_ability_activate(world, self.info))
        self.assertEqual(world.component_for_entity(player, CPlayerAbility).charges, 1)

    def test_el_escudo_dura_lo_que_dice_la_configuracion(self):
        world, player = make_player(charges=1)
        system_player_ability_activate(world, self.info)
        system_player_ability(world, self.info["duration"] - 0.1, self.info)
        self.assertTrue(world.has_component(player, CShield))
        system_player_ability(world, 0.2, self.info)
        clear(world)
        self.assertFalse(world.has_component(player, CShield))
        self.assertEqual(auras(world), [])

    def test_hay_cooldown_entre_usos(self):
        world, player = make_player(charges=2)
        system_player_ability_activate(world, self.info)
        system_player_ability(world, self.info["duration"] + 0.1, self.info)
        clear(world)
        self.assertFalse(system_player_ability_activate(world, self.info))
        system_player_ability(world, self.info["cooldown"], self.info)
        self.assertTrue(system_player_ability_activate(world, self.info))
        self.assertEqual(world.component_for_entity(player, CPlayerAbility).charges, 0)

    def test_el_numero_de_usos_es_limitado(self):
        world, player = make_player(charges=ability_info()["max_charges"])
        uses = 0
        for _ in range(ability_info()["max_charges"] + 3):
            if system_player_ability_activate(world, self.info):
                uses += 1
            system_player_ability(world, self.info["cooldown"] + 1, self.info)
            clear(world)
        self.assertEqual(uses, ability_info()["max_charges"])

    def test_el_jugador_muerto_no_la_activa(self):
        world, player = make_player(charges=1)
        world.add_component(player, CPlayerDead(1.0, False))
        self.assertFalse(system_player_ability_activate(world, self.info))

    def test_el_aura_sigue_al_jugador(self):
        world, player = make_player(charges=1)
        system_player_ability_activate(world, self.info)
        world.component_for_entity(player, CTransform).pos.update(300, 400)
        system_player_ability(world, 0.016, self.info)
        aura = auras(world)[0]
        aura_center = (world.component_for_entity(aura, CTransform).pos
                       + V(world.component_for_entity(aura, CSurface).area.size) / 2)
        player_center = (world.component_for_entity(player, CTransform).pos
                         + V(world.component_for_entity(player, CSurface).area.size) / 2)
        self.assertEqual(aura_center, player_center)

    def test_el_aura_parpadea_al_acabarse(self):
        world, player = make_player(charges=1)
        system_player_ability_activate(world, self.info)
        system_player_ability(world, self.info["duration"] - self.info["warning_time"] - 0.01, self.info)
        aura = auras(world)[0]
        self.assertFalse(world.has_component(aura, CTagHidden))
        states = set()
        for _ in range(40):
            system_player_ability(world, 0.02, self.info)
            if world.entity_exists(aura):
                states.add(world.has_component(aura, CTagHidden))
        self.assertEqual(states, {True, False})


class TestElEscudoProtege(unittest.TestCase):
    def setUp(self):
        reset_game_state()
        self.addCleanup(reset_game_state)
        self.info = ability_info()
        self.world, self.player = make_player(charges=1, pos=V(100, 100))

    def put_enemy_on_player(self):
        enemies_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.enemies_config)
        c_t = self.world.component_for_entity(self.player, CTransform)
        return create_enemy(self.world, enemies_info, c_t.pos.copy(), EnemyType.E)

    def test_sin_escudo_es_vulnerable_y_con_escudo_no(self):
        self.assertTrue(is_vulnerable(self.world, self.player))
        system_player_ability_activate(self.world, self.info)
        self.assertFalse(is_vulnerable(self.world, self.player))

    def test_al_acabar_el_escudo_vuelve_a_ser_vulnerable(self):
        system_player_ability_activate(self.world, self.info)
        system_player_ability(self.world, self.info["duration"] + 0.1, self.info)
        clear(self.world)
        self.assertTrue(is_vulnerable(self.world, self.player))

    def test_un_enemigo_encima_no_mata_con_escudo(self):
        system_player_ability_activate(self.world, self.info)
        enemy = self.put_enemy_on_player()
        lives = ServiceLocator.game_state_service.lives
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertFalse(self.world.has_component(self.player, CPlayerDead))
        self.assertEqual(ServiceLocator.game_state_service.lives, lives)
        self.assertTrue(self.world.entity_exists(enemy))

    def test_sin_escudo_el_mismo_enemigo_si_mata(self):
        self.put_enemy_on_player()
        system_player_death(self.world, RESPAWN, OBSTACLES)
        self.assertTrue(self.world.has_component(self.player, CPlayerDead))

    def test_el_escudo_no_destruye_enemigos(self):
        system_player_ability_activate(self.world, self.info)
        self.put_enemy_on_player()
        system_player_ability(self.world, 1.0, self.info)
        system_player_death(self.world, RESPAWN, OBSTACLES)
        clear(self.world)
        self.assertEqual(len(self.world.get_component(CEnemy)), 1)


class TestHudYMinimapa(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        pygame.init()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.info = ability_info()
        self.world, self.player = make_player(charges=2)
        create_ability_hud(self.world, self.info["hud"])

    def hud_text(self):
        from src.ecs.components.c_ability_text import CAbilityText
        return self.world.get_components(CText, CAbilityText)[0][1][0].text

    def test_el_hud_muestra_las_cargas(self):
        system_ability_hud(self.world, self.info["hud"])
        self.assertEqual(self.hud_text(), "x2")

    def test_el_hud_muestra_que_esta_activo(self):
        system_player_ability_activate(self.world, self.info)
        system_ability_hud(self.world, self.info["hud"])
        self.assertEqual(self.hud_text(), self.info["hud"]["active_text"])

    def test_el_item_se_ve_en_el_minimapa(self):
        minimap_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.minimap_config)
        minimap = create_minimap(self.world, minimap_info)
        create_pickup(self.world, self.info["pickup"], V(512, 768))
        system_minimap(self.world, 0.0, WORLD)
        surf = self.world.component_for_entity(minimap, CSurface).surf
        size = surf.get_size()
        x, y = int(512 * size[0] / WORLD.x), int(768 * size[1] / WORLD.y)
        color = minimap_info["pickup_color"]
        self.assertEqual(tuple(surf.get_at((x, y)))[:3], (color["r"], color["g"], color["b"]))

    def test_sin_item_el_minimapa_no_muestra_nada_de_pickup(self):
        minimap_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.minimap_config)
        minimap = create_minimap(self.world, minimap_info)
        system_minimap(self.world, 0.0, WORLD)
        surf = self.world.component_for_entity(minimap, CSurface).surf
        color = minimap_info["pickup_color"]
        found = any(tuple(surf.get_at((x, y)))[:3] == (color["r"], color["g"], color["b"])
                    for x in range(surf.get_width()) for y in range(surf.get_height()))
        self.assertFalse(found)


class TestEnLaEscenaDeJuego(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        reset_game_state()
        self.addCleanup(reset_game_state)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()

    def ability(self):
        return self.scene.ecs_world.component_for_entity(self.scene._player_entity, CPlayerAbility)

    def test_x_sin_cargas_no_hace_nada(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_x))
        self.assertFalse(self.scene.ecs_world.has_component(self.scene._player_entity, CShield))

    def test_x_con_carga_activa_el_escudo(self):
        self.ability().charges = 1
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_x))
        self.assertTrue(self.scene.ecs_world.has_component(self.scene._player_entity, CShield))
        self.assertEqual(self.ability().charges, 0)

    def test_x_no_activa_el_escudo_en_pausa(self):
        self.ability().charges = 1
        self.scene.toggle_pause()
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_x))
        self.assertFalse(self.scene.ecs_world.has_component(self.scene._player_entity, CShield))

    def test_el_nivel_crea_el_spawner_de_items(self):
        self.assertEqual(len(self.scene.ecs_world.get_component(CPickupSpawner)), 1)

    def test_el_item_sale_en_la_partida_y_se_recoge(self):
        spawner = self.scene.ecs_world.get_component(CPickupSpawner)[0][1]
        spawner.chance = 1.0
        spawner.timer = 0.0
        self.scene.simulate(1 / 60)
        items = pickups(self.scene.ecs_world)
        self.assertEqual(len(items), 1)
        c_t = self.scene.ecs_world.component_for_entity(self.scene._player_entity, CTransform)
        self.scene.ecs_world.component_for_entity(items[0], CTransform).pos.update(c_t.pos + V(6, 6))
        self.scene.simulate(1 / 60)
        self.assertEqual(self.ability().charges, 1)

    def test_el_escudo_sobrevive_a_los_pasos_de_la_partida(self):
        self.ability().charges = 1
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_x))
        for _ in range(30):
            self.scene.simulate(1 / 60)
        self.assertEqual(len(auras(self.scene.ecs_world)), 1)

    def test_las_instrucciones_hablan_del_escudo(self):
        with open("assets/cfg/instructions.json", encoding="utf-8") as f:
            self.assertIn("X: ESCUDO", f.read())


if __name__ == "__main__":
    unittest.main()
