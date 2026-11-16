class CPlayerWeapon:
    def __init__(self, weapon_info: dict) -> None:
        self.bullet_info: dict = weapon_info["bullet"]
        self.fire_cooldown: float = weapon_info["fire_cooldown"]
        self.time_left: float = 0.0
