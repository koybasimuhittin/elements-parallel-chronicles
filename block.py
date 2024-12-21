from unit import EarthUnit, FireUnit, WaterUnit, AirUnit


class Block:
    def __init__(self, units, top_left, bottom_right, id, adjacent_blocks, size):
        self.units = units
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.id = id
        self.adjacent_blocks = adjacent_blocks
        self.size = size
        self.grid = [['.' for _ in range(self.size[0])] for _ in range(self.size[1])]

    def fill_grid(self):
        for faction in self.units:
            for unit in self.units[faction]:
                coords = self.get_block_coordinates(unit[0], unit[1])
                if faction == "E":
                    self.grid[coords[0]][coords[1]] = EarthUnit(unit[0], unit[1])
                elif faction == "F":
                    self.grid[coords[0]][coords[1]] = FireUnit(unit[0], unit[1])
                elif faction == "W":
                    self.grid[coords[0]][coords[1]] = WaterUnit(unit[0], unit[1])
                elif faction == "A":
                    self.grid[coords[0]][coords[1]] = AirUnit(unit[0], unit[1])

    def get_block_coordinates(self, x, y):
        return (x - self.top_left[0], y - self.top_left[1])

    def get_grid_coordinate(self, x, y):
        return (x + self.top_left[0], y + self.top_left[1])

    def get_grid_element(self, x, y):
        return self.grid[x - self.top_left[0]][y - self.top_left[1]]

    def is_coordinate_inside(self, x, y):
        return self.top_left[0] <= x < self.bottom_right[0] and self.top_left[1] <= y < self.bottom_right[1]

    def __str__(self):
        return f"Block {self.id} ({self.top_left}, {self.bottom_right}) - {self.units} - Adjacent Blocks : {self.adjacent_blocks}"
