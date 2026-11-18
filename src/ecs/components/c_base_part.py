class CBasePart:
    """Une una torreta o un núcleo con la base a la que pertenece (#21).

    base es la entidad del cuerpo, la que lleva CBase. Así el choque de una bala
    con una pieza llega a su base sin buscar en todas las CBase.
    """

    def __init__(self, base: int) -> None:
        self.base = base
