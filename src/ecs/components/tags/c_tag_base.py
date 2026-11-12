class CTagBase:
    """Marca la entidad principal (el cuerpo) de una base enemiga."""


class CTagBaseTurret:
    """Marca una torreta de base. base es la entidad de la base a la que pertenece."""

    def __init__(self, base: int) -> None:
        self.base = base


class CTagBaseCore:
    """Marca el núcleo de una base. base es la entidad de la base a la que pertenece."""

    def __init__(self, base: int) -> None:
        self.base = base
