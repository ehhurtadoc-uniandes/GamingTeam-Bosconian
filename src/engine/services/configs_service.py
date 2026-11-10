import json


class ConfigsService:
    def __init__(self) -> None:
        self._configs: dict[str, dict] = {}

    def get(self, path: str) -> dict:
        """Devuelve el contenido del JSON de path, leyéndolo solo la primera vez."""
        if path not in self._configs:
            with open(path, encoding="utf-8") as file:
                self._configs[path] = json.load(file)
        return self._configs[path]
