from src.create.prefab_menu import create_text_lines
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene


def victory_stats(stats_info: dict) -> list[str]:
    """Líneas de la victoria con los datos de la partida: puntaje, vidas y continuaciones usadas."""
    game_state = ServiceLocator.game_state_service
    values = {"score": game_state.score, "lives_lost": game_state.lives_lost,
              "continues_used": game_state.continues_used}
    return [line.format(**values) for line in stats_info["text"]]


class VictoryScene(MenuScene):
    """Escena de victoria tras la última ronda (LC-ESC-05).

    Muestra el puntaje, cuántas vidas y continuaciones se usaron (LC-ESC-05.2) y vuelve al
    título al presionar aceptar o volver (LC-ESC-05.1). Durante accept_delay se ignoran las
    teclas, para que el jugador que venía disparando con Z no la salte sin verla.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine, ServiceLocator.constants_service.victory_config)
        self.wait_time = 0.0

    def do_create_menu(self) -> None:
        self.wait_time = self._config["accept_delay"]
        stats_info = self._config["stats"]
        create_text_lines(self.ecs_world, dict(stats_info, text=victory_stats(stats_info)))

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        self.wait_time -= delta_time

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if action.phase != CommandPhase.START or self.wait_time > 0:
            return
        if action.name in (constants.menu_accept_command, constants.menu_back_command):
            ServiceLocator.sounds_service.play_effect("MENU_ACCEPT")
            self.switch_scene(constants.title_scene)
