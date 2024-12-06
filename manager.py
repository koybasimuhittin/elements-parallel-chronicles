import re
import block

class Manager:

    BLOCK_SIZE = 3

    def __init__(self, input_file, output_file, worker_count):
        self.input_file = input_file
        self.output_file = output_file
        self.worker_count = worker_count
        with open(input_file, "r") as file:
            self.lines = file.readlines()

    def parse_general_info(self, lines):
        first_line = lines[0].strip().split()
        self.N = int(first_line[0])  # Grid size
        self.W = int(first_line[1])  # Number of waves
        self.T = int(first_line[2])  # Units per faction per wave
        self.R = int(first_line[3])  # Rounds per wave
    
    def parse_wave_data(self, lines):
        wave_data = {}
        wave_index = 0
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("Wave"):
                wave_index += 1
                wave_data[wave_index] = {"E": [], "F": [], "W": [], "A": []}
            elif line.startswith(("E:", "F:", "W:", "A:")):
                faction, coordinates = line.split(":")
                coords = [
                    tuple(map(int, coord.split()))
                    for coord in re.findall(r"\d+ \d+", coordinates)
                ]
                coords.sort()
                wave_data[wave_index][faction] = coords
        return wave_data

    def generate_blocks(self, wave, N):
        blocks = []
        block_id = 0
        for i in range(N // self.BLOCK_SIZE + N % self.BLOCK_SIZE):
            blocks.append([])
            for j in range(N // self.BLOCK_SIZE + N % self.BLOCK_SIZE):
                top_left = (i * self.BLOCK_SIZE, j * self.BLOCK_SIZE)
                bottom_right = (
                    min((i + 1) * self.BLOCK_SIZE, N) - 1,
                    min((j + 1) * self.BLOCK_SIZE, N) - 1,
                )
                adjacent_blocks = []
                factions = {
                    "E": [],
                    "F": [],
                    "W": [],
                    "A": [],
                }

                for faction in wave:
                    for coord in wave[faction]:
                        if top_left[0] <= coord[0] <= bottom_right[0] and top_left[1] <= coord[1] <= bottom_right[1]:
                            factions[faction].append(coord)
                
                block_instance = block.Block(factions, top_left, bottom_right, block_id, 0, adjacent_blocks)
                blocks[i].append(block_instance)
                block_id += 1
            
        return blocks
        
    def calculate_adjacent_blocks(self, blocks):
        for i in range(len(blocks)):
            for j in range(len(blocks[i])):
                adjacent_blocks = []
                for x in range(i-1, i+2):
                    for y in range(j-1, j+2):
                        if 0 <= x < len(blocks) and 0 <= y < len(blocks[i]) and (x, y) != (i, j):
                            adjacent_blocks.append({"id": blocks[x][y].block_id, "rank": blocks[x][y].worker_rank})
                blocks[i][j].adjacent_blocks = adjacent_blocks

    def assign_blocks_to_workers(self, blocks):
        for i in range(len(blocks)):
            for j in range(len(blocks[i])):
                blocks[i][j].worker_rank = (i + j) % self.worker_count + 1

    def print_blocks(self, blocks):
        for i in range(len(blocks)):
            for j in range(len(blocks[i])):
                print(blocks[i][j])
    
    def run(self):
        self.parse_general_info(self.lines)
        self.wave_data = self.parse_wave_data(self.lines)
        for i in range(1, self.W + 1):
            print(f"Wave {i}")
            self.blocks = self.generate_blocks(self.wave_data[i], self.N)
            self.assign_blocks_to_workers(self.blocks)
            self.calculate_adjacent_blocks(self.blocks)
            self.print_blocks(self.blocks)
        

