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

    def get_block_coordinates(self, x, y):
        return (x - self.top_left[0], y - self.top_left[1])

    def get_grid_coordinate(self, x, y):
        return (x + self.top_left[0], y + self.top_left[1])

    def get_grid_element(self, x, y):
        return self.grid[x - self.top_left[0]][y - self.top_left[1]]

    def is_coordinate_inside(self, x, y):
        return self.top_left[0] <= x < self.bottom_right[0] and self.top_left[1] <= y < self.bottom_right[1]
    
    def get_grid_with_boundary_element(self, x, y):
        return self.grid_with_boundary[x - self.top_left[0] + 3][y - self.top_left[1] + 3]
    
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

    
    def reset_boundary(self):
        for i in range(self.size[1]):
            for j in range(self.size[0]):
                self.grid_with_boundary[i + 3][j + 3] = self.grid[i][j].unit_type if self.grid[i][j] != "." else "."

    
    def add_units(self, units):
        for unit in units:
            faction = unit[0]
            x, y = unit[1], unit[2]

            if self.get_grid_element(x, y) != ".":
                continue

            if faction == "E":
                self.grid[x - self.top_left[0]][y - self.top_left[1]] = EarthUnit(x, y)
            elif faction == "F":
                self.grid[x - self.top_left[0]][y - self.top_left[1]] = FireUnit(x, y)
            elif faction == "W":
                self.grid[x - self.top_left[0]][y - self.top_left[1]] = WaterUnit(x, y)
            elif faction == "A":
                self.grid[x - self.top_left[0]][y - self.top_left[1]] = AirUnit(x, y)


    def __str__(self):
        return f"Block {self.id} ({self.top_left}, {self.bottom_right}) - {self.units} - Adjacent Blocks : {self.adjacent_blocks}"
