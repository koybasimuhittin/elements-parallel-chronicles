import re
import block
import utils
from mpi4py import MPI
comm = MPI.COMM_WORLD

class Manager:
    def __init__(self, input_file, output_file, worker_count):
        self.input_file = input_file
        self.output_file = output_file
        self.worker_count = worker_count
        with open(input_file, "r") as file:
            self.lines = file.readlines()
    
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
        for i in range(N // utils.BLOCK_SIZE + N % utils.BLOCK_SIZE):
            blocks.append([])
            for j in range(N // utils.BLOCK_SIZE + N % utils.BLOCK_SIZE):
                top_left = (i * utils.BLOCK_SIZE, j * utils.BLOCK_SIZE)
                bottom_right = (
                    min((i + 1) * utils.BLOCK_SIZE, N) - 1,
                    min((j + 1) * utils.BLOCK_SIZE, N) - 1,
                )
                adjacent_blocks = []
                units = {
                    "E": [],
                    "F": [],
                    "W": [],
                    "A": [],
                }
                
                block_instance = block.Block(units, top_left, bottom_right, block_id, 0, adjacent_blocks)
                blocks[i].append(block_instance)
                block_id += 1

        for faction in wave:
            for coord in wave[faction]:
                id = utils.coordinate_to_block_id(coord, N)
                x, y = utils.block_id_to_block_index(id, N)
                blocks[x][y].units[faction].append(coord)
            
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
                blocks[i][j].worker_rank = blocks[i][j].block_id % self.worker_count + 1

    def print_blocks(self, blocks):
        for i in range(len(blocks)):
            for j in range(len(blocks[i])):
                print(blocks[i][j])

    def send_blocks(self):
        for i in range(len(self.blocks)):
            for j in range(len(self.blocks[i])):
                comm.send(self.blocks[i][j], dest=self.blocks[i][j].worker_rank, tag=1)

    def run(self):
        utils.parse_general_info(self.lines)
        self.wave_data = self.parse_wave_data(self.lines)
        for i in range(1, utils.W + 1):
            print(f"Wave {i}")
            self.blocks = self.generate_blocks(self.wave_data[i], utils.N)
            self.assign_blocks_to_workers(self.blocks)
            self.calculate_adjacent_blocks(self.blocks)
            print("Blocks:")
            self.print_blocks(self.blocks)
            
        self.send_blocks()

        
        
        

