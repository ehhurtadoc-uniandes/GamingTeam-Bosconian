from src.create.prefab_demo import create_demo_player, create_demo_target
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_demo import system_demo_fire, system_demo_hits
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene, is_user_input


class DemoScene(MenuScene):

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine, ServiceLocator.constants_service.demo_config)
        self.time_left = 0.0
        self._explosion_info: dict = {}

    def do_create_menu(self) -> None:
        constants = ServiceLocator.constants_service
        ServiceLocator.game_state_service.attract = True
        self.time_left = self._config["duration"]
        self._explosion_info = ServiceLocator.configs_service.get(constants.explosions_config)["explosion"]
        create_demo_player(self.ecs_world, self._config["player"], self._config["bullet"])
        for target_info in self._config["targets"]:
            create_demo_target(self.ecs_world, target_info)

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        system_demo_fire(self.ecs_world, delta_time)
        system_movement(self.ecs_world, delta_time)
        system_demo_hits(self.ecs_world, self._explosion_info)
        system_animation(self.ecs_world, delta_time)
        system_lifetime(self.ecs_world, delta_time)
        self.time_left -= delta_time
        if self.time_left <= 0:
            self.switch_scene(ServiceLocator.constants_service.instructions_scene)

    def do_process_events(self, event) -> None:
        if is_user_input(event):
            self.switch_scene(ServiceLocator.constants_service.title_scene)
