import math

from src.create.prefab_menu import create_menu
from src.create.prefab_text import create_interface_text
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_text import CText
from src.ecs.systems.s_menu import get_menu, move_selection, selected_action, system_menu_highlight
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene


def seconds_left(time_left: float) -> int:
    """Segundos que se muestran en la cuenta regresiva: 4.2 s se ve como 5, y nunca menos de 0."""
    return max(0, math.ceil(time_left))


class DefeatScene(MenuScene):
    """Escena de derrota (LC-ESC-06): "CONTINUAR?" con cuenta regresiva y las opciones SI y NO.

    SI continúa en el mismo nivel con todas las vidas y el puntaje en cero (LC-ESC-06.2).
    NO, volver o que se acabe continue_time (5 s, LC-ESC-06.1) llevan a la escena de título.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine, ServiceLocator.constants_service.defeat_config)
        self.time_left = 0.0
        self._countdown_text: int | None = None

    def do_create_menu(self) -> None:
        self.time_left = self._config["continue_time"]
        info = self._config["countdown"]
        self._countdown_text = create_interface_text(self.ecs_world, self._countdown(), info)
        create_menu(self.ecs_world, self._config["menu"])

    def _countdown(self) -> str:
        return self._config["countdown"]["text"].format(seconds=seconds_left(self.time_left))

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        system_menu_highlight(self.ecs_world)
        self.time_left -= delta_time
        self.ecs_world.component_for_entity(self._countdown_text, CText).text = self._countdown()
        if self.time_left <= 0:
            self.switch_scene(ServiceLocator.constants_service.title_scene)

    def do_action(self, action: CInputCommand) -> None:
        if action.phase != CommandPhase.START:
            return
        constants = ServiceLocator.constants_service
        menu = get_menu(self.ecs_world)
        if action.name in constants.menu_move_commands:
            menu.selected = move_selection(menu.selected, constants.menu_move_commands[action.name], menu.count)
        elif action.name == constants.menu_accept_command:
            self.accept(selected_action(self.ecs_world))
        elif action.name == constants.menu_back_command:
            self.accept("QUIT")

    def accept(self, action: str) -> None:
        if action == "CONTINUE":
            ServiceLocator.game_state_service.continue_game()
            self.switch_scene(ServiceLocator.constants_service.play_scene)
        elif action == "QUIT":
            self.switch_scene(ServiceLocator.constants_service.title_scene)
