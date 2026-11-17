class CSpecialShot:
    def __init__(self, special_info: dict) -> None:
        self.forward_bullets: int = special_info["forward_bullets"]
        self.spread_degrees: float = special_info["spread_degrees"]
