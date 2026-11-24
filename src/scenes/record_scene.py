from src.create.prefab_menu import create_text_lines
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene


class RecordScene(MenuScene):

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine, ServiceLocator.constants_service.record_config)
        self.wait_time = 0.0

    def do_create_menu(self) -> None:
        self.wait_time = self._config["accept_delay"]
        game_state = ServiceLocator.game_state_service
        stats_info = self._config["stats"]
        values = {"score": game_state.score, "hi_score": game_state.hi_score}
        lines = [line.format(**values) for line in stats_info["text"]]
        create_text_lines(self.ecs_world, dict(stats_info, text=lines))

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        self.wait_time -= delta_time

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if action.phase != CommandPhase.START or self.wait_time > 0:
            return
        if action.name in (constants.menu_accept_command, constants.menu_back_command):
            ServiceLocator.sounds_service.play_effect("MENU_ACCEPT")
            self.switch_scene(ServiceLocator.game_state_service.after_record)
