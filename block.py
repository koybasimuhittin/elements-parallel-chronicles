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
                self.grid[unit[0]][unit[1]] = faction

    def get_grid_element(self, x, y):
        return self.grid[x - self.top_left[0]][y - self.top_left[1]]
                
    def __str__(self):
        return f"Block {self.id} ({self.top_left}, {self.bottom_right}) - {self.units} - Adjacent Blocks : {self.adjacent_blocks}"
    
