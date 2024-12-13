import re
from block import Block
import utils
from mpi4py import MPI
from constants import MESSAGES
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

    def generate_blocks(self, wave, n, block_sizes):
        blocks = []
        block_ids = []
        id = 1

        top_left = (0, 0)
        for i in range(len(block_sizes)):
            block_top_left = top_left
            block_ids.append([])
            for j in range(len(block_sizes[i])):
                bottom_right = (block_top_left[0] + block_sizes[i][j][0], block_top_left[1] + block_sizes[i][j][1])
                blocks.append(Block({"E": [], "F": [], "W": [], "A": []}, block_top_left, bottom_right, id, [], block_sizes[i][j]))
                block_ids[i].append(id)
                id += 1
                block_top_left = (block_top_left[0] + block_sizes[i][j][0], block_top_left[1])
            top_left = (top_left[0], top_left[1] + block_sizes[i][0][1])

        for faction in wave:
            for coord in wave[faction]:
                id = utils.coordinates_to_block_id(coord[0], coord[1], n, self.worker_count)
                blocks[id - 1].units[faction].append(coord)
            
        return blocks, block_ids
        
    def calculate_adjacent_blocks(self, block_ids, blocks):
        for i in range(len(block_ids)):
            for j in range(len(block_ids[i])):
                adjacent_blocks = []
                for x in range(i-1, i+2):
                    for y in range(j-1, j+2):
                        if 0 <= x < len(block_ids) and 0 <= y < len(block_ids[i]) and (x, y) != (i, j):
                            adjacent_blocks.append(block_ids[x][y])
                blocks[block_ids[i][j] - 1].adjacent_blocks = adjacent_blocks


    def print_blocks(self, blocks):
        for i in range(len(blocks)):
                print(blocks[i])

    def send_blocks(self):
        for i in range(len(self.blocks)):
                comm.send(1, dest=self.blocks[i].id, tag=10)
                comm.send(self.blocks[i], dest=self.blocks[i].id, tag=1)

    def set_current_workers(self, x, y):
        sqr_of_worker = int(self.worker_count ** 0.5)
        current_workers = []
        for i in range(sqr_of_worker):
            for j in range(sqr_of_worker):
                if(i % 2 == x and j % 2 == y):
                    ## send start signal
                    current_workers.append(i * sqr_of_worker + j + 1)
                else:
                    ## send stop signal
                    pass

        return current_workers


    def run(self):
        utils.parse_general_info(self.lines)
        self.block_sizes = utils.calculate_block_sizes(utils.N, self.worker_count)
        self.wave_data = self.parse_wave_data(self.lines)
        for i in range(1, utils.W + 1):
            print(f"Wave {i}")
            self.blocks, self.block_ids = self.generate_blocks(self.wave_data[i], utils.N, self.block_sizes)
            self.calculate_adjacent_blocks(self.block_ids, self.blocks)
            print("Blocks:")
            self.print_blocks(self.blocks)

        self.send_blocks()

        blocksReceived = [False for _ in range(self.worker_count)]

        for i in range(1, self.worker_count + 1):
            if comm.recv(source=i, tag=MESSAGES['BLOCKS_RECEIVED']['tag']):
                blocksReceived[i - 1] = True

        print(blocksReceived)


    # def run2(self):
    #         for i in range(1,self.worker_count):
    #             print(i)
    #             print("23423235")
    #             for j in range(1, self.worker_count + 1):
    #                 if i==j:
    #                     comm.send(1, dest=j, tag=10)
    #                 else:
    #                     comm.send(0, dest=j, tag=10)
    #             comm.recv(source=i,tag=MPI.ANY_TAG)
    #             print("!!")
    #             for j in range(1, self.worker_count + 1):
    #                 comm.send(None,dest=j,tag=3)
    #         for j in range(1, self.worker_count + 1):
    #             comm.send(-1, dest=j, tag=10)





        
        
        

