import re
from block import Block
from utils import Utils
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
        
        try:
            self.output = open(output_file, "w")
        except:
            self.output = open("output.txt", "x")

    
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
                wave_data[wave_index][faction] = coords
        return wave_data

    def generate_blocks(self, block_sizes):
        blocks = []
        block_ids = []
        block_id = 1

        top_left = (0, 0)
        for i in range(len(block_sizes)):
            block_top_left = top_left
            block_ids.append([])
            for j in range(len(block_sizes[i])):
                width, height = block_sizes[i][j]
                bottom_right = (
                    block_top_left[0] + height,
                    block_top_left[1] + width
                )
                blocks.append(
                    Block(
                        {"E": [], "F": [], "W": [], "A": []},
                        block_top_left,
                        bottom_right,
                        block_id,
                        [],
                        block_sizes[i][j]
                    )
                )
                block_ids[i].append(block_id)
                block_id += 1
                block_top_left = (block_top_left[0], block_top_left[1] + width)
            top_left = (top_left[0] + block_sizes[i][0][1], top_left[1])

        return blocks, block_ids
        
    def calculate_adjacent_blocks(self, block_ids, blocks):
        for i in range(len(block_ids)):
            for j in range(len(block_ids[i])):
                adjacent_blocks = []
                # from top-left to left clockwise [0, 1, 2]
                #                                 [7, x, 3]
                #                                 [6, 5, 4]
                dx = [-1,  0,  1,  1,  1,  0, -1, -1]
                dy = [-1, -1, -1,  0,  1,  1,  1,  0]  
                for k in range(8):
                    y = i + dy[k]
                    x = j + dx[k]
                    if 0 <= y < len(block_ids) and 0 <= x < len(block_ids[i]):
                        adjacent_blocks.append({
                            'block_id': block_ids[y][x],
                            'position': k,
                            'relative_position': (dx[k], dy[k])
                        })
                blocks[block_ids[i][j] - 1].adjacent_blocks = adjacent_blocks

    def send_blocks(self):
        for b in self.blocks:
            comm.send({'state': 1}, dest=b.id, tag=10)
            comm.send(b, dest=b.id, tag=1)

    def send_units(self, blocks):
        for i in range(len(blocks)):
            comm.send({'state': 20}, dest=i + 1, tag=10)
            comm.send(blocks[i]['units'], dest=i + 1, tag=2)

    def set_states(self, states, workers, worker_group):
        for rank in range(1, self.worker_count + 1):
            if workers[rank - 1]:
                comm.send({'state': states[0], 'current_worker_group': worker_group}, dest=rank, tag=10)
            else:
                comm.send({'state': states[1], 'current_worker_group': worker_group}, dest=rank, tag=10)

    def set_current_workers(self, x, y):
        sqr_of_worker = int(self.worker_count ** 0.5)
        if x == -1 and y == -1:
            return [True] * self.worker_count

        current_workers = [False] * self.worker_count
        for i in range(sqr_of_worker):
            for j in range(sqr_of_worker):
                if (i % 2 == x) and (j % 2 == y):
                    current_workers[i * sqr_of_worker + j] = True
        return current_workers
    
    def gather_grids_and_print(self):
        finalGrid = [['.' for _ in range(Utils.N)] for _ in range(Utils.N)]
        for rank in range(1, self.worker_count + 1):
            comm.send({'state': 13}, dest=rank, tag=10)
            block = comm.recv(source=rank, tag=10)
            for row_idx in range(block.top_left[0], block.bottom_right[0]):
                for col_idx in range(block.top_left[1], block.bottom_right[1]):
                    finalGrid[row_idx][col_idx] = str(
                        block.grid[row_idx - block.top_left[0]][col_idx - block.top_left[1]]
                    )
        for row in finalGrid:
            for cell in row:
                print(cell.ljust(2, ' '), end="", file=self.output)
            print(file=self.output)
        print(file=self.output)

    def run(self):
        Utils.parse_general_info(self.lines)

        config_data = {
            'N': Utils.N,
            'W': Utils.W,
            'T': Utils.T,
            'R': Utils.R,
        }
        comm.bcast(config_data, root=0)

        self.block_sizes = Utils.calculate_block_sizes(Utils.N, self.worker_count)

        self.wave_data = self.parse_wave_data(self.lines)

        self.blocks, self.block_ids = self.generate_blocks(self.block_sizes)
        self.calculate_adjacent_blocks(self.block_ids, self.blocks)
        self.send_blocks()

        for wave_idx in range(1, Utils.W + 1):
            wave = self.wave_data[wave_idx]

            blocks = [{} for _ in range(self.worker_count)]
            for rank in range(1, self.worker_count + 1):
                blocks[rank - 1]['units'] = []

            for faction in wave:
                for coord in wave[faction]:
                    if(coord[0] < 0 or coord[1] < 0 or coord[0] >= Utils.N or coord[1] >= Utils.N):
                        continue
                    found_id = Utils.coordinates_to_block_id(coord[0], coord[1])
                    blocks[found_id - 1]['units'].append((faction, coord[0], coord[1]))

            

            self.send_units(blocks)

            for _ in range(Utils.R):
                for x in range(2):      # x in {0,1}
                    for y in range(2):  # y in {0,1}
                        current_workers = self.set_current_workers(x, y)
                        # State to active: 2, inactive: 3
                        self.set_states([2, 3], current_workers, x * 2 + y)

                        # Wait for active workers to finish
                        for rank in range(1, self.worker_count + 1):
                            if current_workers[rank - 1]:
                                comm.recv(source=rank, tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])

                        for rank in range(1, self.worker_count + 1):
                            if not current_workers[rank - 1]:
                                comm.send(None, dest=rank, tag=60)

                for x in range(2):
                    for y in range(2):
                        current_workers = self.set_current_workers(x, y)
                        # State to active: 4, inactive: 5
                        self.set_states([10, 11], current_workers, x * 2 + y)
                        # Wait for active workers
                        for rank in range(1, self.worker_count + 1):
                            if current_workers[rank - 1]:
                                comm.recv(source=rank, tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                        # Send "continue" or "skip" (tag=70)
                        for rank in range(1, self.worker_count + 1):
                            if not current_workers[rank - 1]:
                                comm.send(None, dest=rank, tag=72)

                current_workers = [True] * self.worker_count
                self.set_states([12, 12], current_workers, -1)

                # --- Active time 2 (checkerboard step) ---
                for x in range(2):
                    for y in range(2):
                        current_workers = self.set_current_workers(x, y)
                        # State to active: 4, inactive: 5
                        self.set_states([4, 5], current_workers, x * 2 + y)

                        # Wait for active workers
                        for rank in range(1, self.worker_count + 1):
                            if current_workers[rank - 1]:
                                comm.recv(source=rank, tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])

                        # Send "continue" or "skip" (tag=70)
                        for rank in range(1, self.worker_count + 1):
                            if not current_workers[rank - 1]:
                                comm.send(None, dest=rank, tag=70)

                current_workers = [True] * self.worker_count
                self.set_states([6, 6], current_workers, -1)
                self.set_states([7, 7], current_workers, -1)

            for x in range(2):
                for y in range(2):
                    current_workers = self.set_current_workers(x, y)
                    # State to active: 4, inactive: 5
                    self.set_states([8, 9], current_workers, x * 2 + y)
                    # Wait for active workers
                    for rank in range(1, self.worker_count + 1):
                        if current_workers[rank - 1]:
                            comm.recv(source=rank, tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                    # Send "continue" or "skip" (tag=70)
                    for rank in range(1, self.worker_count + 1):
                        if not current_workers[rank - 1]:
                            comm.send(None, dest=rank, tag=71)

            current_workers = [True] * self.worker_count
            self.set_states([21, 21], current_workers, -1)

        self.gather_grids_and_print()
    

        for rank in range(1, self.worker_count + 1):
            comm.send({'state': -1}, dest=rank, tag=10)
