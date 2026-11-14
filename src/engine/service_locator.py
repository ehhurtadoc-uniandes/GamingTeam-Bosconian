from src.engine.services.configs_service import ConfigsService
from src.engine.services.constants_service import ConstantsService
from src.engine.services.fonts_service import FontsService
from src.engine.services.game_state_service import GameStateService
from src.engine.services.images_service import ImagesService
from src.engine.services.sounds_service import SoundsService
from src.engine.services.texts_service import TextsService


class ServiceLocator:
    images_service = ImagesService()
    sounds_service = SoundsService()
    fonts_service = FontsService()
    texts_service = TextsService()
    configs_service = ConfigsService()
    constants_service = ConstantsService()
    game_state_service = GameStateService()
