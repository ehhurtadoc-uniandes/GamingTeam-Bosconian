class CMenuItem:
    """Una opción del menú: su posición (index), qué hace (action) y su texto en el JSON (template).

    template puede tener campos como {level}; la escena los llena al cambiar el valor.
    """

    def __init__(self, index: int, action: str, template: str) -> None:
        self.index = index
        self.action = action
        self.template = template
