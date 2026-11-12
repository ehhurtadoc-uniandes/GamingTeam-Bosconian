from enum import Enum


class BaseOrientation(Enum):
    """Orientación de una base enemiga (LC-BAS-03, RF-09.3).

    Marca también por dónde es vulnerable el núcleo (#21): en una base
    horizontal se entra por los lados izquierdo/derecho del eje largo, en una
    vertical por arriba/abajo.
    """
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class CBase:
    """Relaciona una base con sus piezas (LC-BAS-04, RF-09.1).

    - orientation: orientación con que se desplegó la base.
    - turrets: entidades de las seis torretas. #21 las quita al destruirlas y
      destruye la base cuando la lista queda vacía.
    - core: entidad del núcleo.
    """

    def __init__(self, orientation: BaseOrientation, turrets: list[int], core: int) -> None:
        self.orientation = orientation
        self.turrets = turrets
        self.core = core
