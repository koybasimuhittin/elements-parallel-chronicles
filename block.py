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
        self.grid_with_boundary = [['.' for _ in range(self.size[0] + 6)] for _ in range(self.size[1] + 6)]

    def fill_grid(self):
        for faction in self.units:
            for unit in self.units[faction]:
                coords = self.get_block_coordinates(unit[0], unit[1])
                if faction == "E":
                    self.grid[coords[0]][coords[1]] = EarthUnit(unit[0], unit[1])
                    self.grid_with_boundary[coords[0] + 3][coords[1] + 3] = "E"
                elif faction == "F":
                    self.grid[coords[0]][coords[1]] = FireUnit(unit[0], unit[1])
                    self.grid_with_boundary[coords[0] + 3][coords[1] + 3] = "F"
                elif faction == "W":
                    self.grid[coords[0]][coords[1]] = WaterUnit(unit[0], unit[1])
                    self.grid_with_boundary[coords[0] + 3][coords[1] + 3] = "W"
                elif faction == "A":
                    self.grid[coords[0]][coords[1]] = AirUnit(unit[0], unit[1])
                    self.grid_with_boundary[coords[0] + 3][coords[1] + 3] = "A"

    def get_block_coordinates(self, x, y):
        return (x - self.top_left[0], y - self.top_left[1])

    def get_grid_coordinate(self, x, y):
        return (x + self.top_left[0], y + self.top_left[1])

    def get_grid_element(self, x, y):
        return self.grid[x - self.top_left[0]][y - self.top_left[1]]

    def is_coordinate_inside(self, x, y):
        return self.top_left[0] <= x < self.bottom_right[0] and self.top_left[1] <= y < self.bottom_right[1]
    
    def update_boundary(self, boundary, position):
        # add 3x3 boundary to the top left corner
        if position == 0:
            for i in range(3):
                for j in range(3):
                    self.grid_with_boundary[+ i][j] = boundary[i][j]
        
        # add size[0]x3 boundary to the top side
        elif position == 1:
            for i in range(3):
                for j in range(self.size[0]):
                    self.grid_with_boundary[i][j + 3] = boundary[i][j]
        
        # add 3x3 boundary to the top right corner
        elif position == 2:
            for i in range(3):
                for j in range(3):
                    self.grid_with_boundary[i][self.size[0] + j + 3] = boundary[i][j]
        
        # add 3xsize[1] boundary to the right side
        elif position == 3:
            for i in range(self.size[1]):
                for j in range(3):
                    self.grid_with_boundary[i + 3][self.size[0] + j + 3] = boundary[i][j]
        
        # add 3x3 boundary to the bottom right corner
        elif position == 4:
            for i in range(3):
                for j in range(3):
                    self.grid_with_boundary[self.size[1] + i + 3][self.size[0] + j + 3] = boundary[i][j]

        # add size[0]x3 boundary to the bottom side
        elif position == 5:
            for i in range(3):
                for j in range(self.size[0]):
                    self.grid_with_boundary[self.size[1] + i + 3][j + 3] = boundary[i][j]

        # add 3x3 boundary to the bottom left corner
        elif position == 6:
            for i in range(3):
                for j in range(3):
                    self.grid_with_boundary[self.size[1] + i + 3][j] = boundary[i][j]

        # add 3xsize[1] boundary to the left side
        elif position == 7:
            for i in range(self.size[1]):
                for j in range(3):
                    self.grid_with_boundary[i + 3][j] = boundary[i][j]   


        


    def __str__(self):
        return f"Block {self.id} ({self.top_left}, {self.bottom_right}) - {self.units} - Adjacent Blocks : {self.adjacent_blocks}"
