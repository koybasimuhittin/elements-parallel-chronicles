class Unit:
    """
    Base class for a unit on the battlefield.
    """

    def __init__(self, unit_type, x, y, max_health, attack_power, healing_rate):
        self.unit_type = unit_type  # Unit type: E, F, W, A .
        self.x = x  # X-coordinate
        self.y = y  # Y-coordinate
        self.max_health = max_health  # Maximum health points
        self.health = max_health  # Current health points
        self.attack_power = attack_power  # Attack damage
        self.healing_rate = healing_rate  # Healing rate when not attacking
        self.damage_taken = 0
        self.attack_done = False

    def is_alive(self):
        """
        Check if the unit is still alive.
        """
        return self.health > 0
    
    def can_attack(self):
        return self.health >= self.max_health // 2

    def __str__(self):
        return self.unit_type + str(self.health)

    def heal(self):
        return


class EarthUnit(Unit):
    """
    Earth unit class with specific attributes and abilities.
    """

    def __init__(self, x, y):
        super().__init__(unit_type="E", x=x, y=y, max_health=18, attack_power=2, healing_rate=3)
        self.directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def fortify(self):
        """
        Reduce incoming damage by 50% (rounded down).
        """
        self.damage_taken = max(0, self.damage_taken // 2)

    def heal(self):
        self.health = min(18, self.health + self.healing_rate)


class FireUnit(Unit):
    """
    Fire unit class with specific attributes and abilities.
    """

    def __init__(self, x, y):
        super().__init__(unit_type="F", x=x, y=y, max_health=12, attack_power=4, healing_rate=1)
        self.base_attack_power = 4
        self.attack_power = self.base_attack_power
        self.enemies_attacked = []
        self.directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    def inferno(self):
        if self.attack_power < 6:
            self.attack_power += 1
            print(f"Inferno activated! Attack power increased to {self.attack_power}.")

    def reset_inferno(self):
        self.attack_power = self.base_attack_power
        self.enemies_attacked=[]

    def reset_enemies_attacked(self):
        self.enemies_attacked = []

    def heal(self):
        self.health = min(12, self.health + self.healing_rate)


class WaterUnit(Unit):
    """
    Water unit class with specific attributes and abilities.
    """

    def __init__(self, x, y):
        super().__init__(unit_type="W", x=x, y=y, max_health=14, attack_power=3, healing_rate=2)
        self.directions = [(-1, -1), (1, 1), (-1, 1), (1, -1)]

    # def flood(self, battlefield):
    #     neutral_cells = []
    #     directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    #     for dx, dy in directions:
    #         nx, ny = self.x + dx, self.y + dy
    #         if 0 <= nx < battlefield.size and 0 <= ny < battlefield.size:
    #             if battlefield.grid[ny][nx] == ".":
    #                 neutral_cells.append((ny, nx))

    #     neutral_cells.sort(key=lambda cell: (cell[0], cell[1]))

    #     if neutral_cells:
    #         ny, nx = neutral_cells[0]
    #         battlefield.grid[ny][nx] = "W"
    #         new_water_unit = WaterUnit(nx, ny)
    #         print(f"Water unit at ({self.x}, {self.y}) converts adjacent cell ({nx}, {ny}) to Water unit.")
    #         return new_water_unit
    #     else:
    #         print(f"Water unit at ({self.x}, {self.y}) found no adjacent neutral cells to convert.")
    #     return None

    def heal(self):
        self.health = min(14, self.health + self.healing_rate)





class AirUnit(Unit):
    """
    Air unit class with specific attributes and abilities.
    """

    def __init__(self, x, y):
        super().__init__(unit_type="A", x=x, y=y, max_health=10, attack_power=2, healing_rate=2)
        self.directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    def change_position(self,new_coordinates):
        self.x , self.y = new_coordinates
    def unite(self, air_unit):
        self.health = min(10, self.health + air_unit.health)
        self.attack_power += air_unit.attack_power

    def heal(self):
        self.health = min(10, self.health + self.healing_rate)
