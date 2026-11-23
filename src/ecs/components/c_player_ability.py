class CPlayerAbility:
    def __init__(self, ability_info: dict) -> None:
        self.max_charges: int = ability_info["max_charges"]
        self.charges: int = min(ability_info.get("start_charges", 0), self.max_charges)
        self.duration: float = ability_info["duration"]
        self.cooldown: float = ability_info["cooldown"]
        self.cooldown_remaining = 0.0
