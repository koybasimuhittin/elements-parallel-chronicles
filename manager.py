import re
from block import Block
from utils import Utils  # <-- Import the Utils class properly
from mpi4py import MPI
from constants import MESSAGES

comm = MPI.COMM_WORLD

class Manager:
    def __init__(self, input_file, output_file, worker_count):
        self.input_file = input_file
        self.output_file = output_file
        self.worker_count = worker_count  # Number of workers (manager excluded)
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
                wave_data[wave_index][faction] = coords
        return wave_data

    def generate_blocks(self, n, block_sizes):
        """
        Create blocks with top-left/bottom-right boundaries,
        populate them with wave units, and call fill_grid().
        """
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
                # Create a new Block
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
                # Move our top_left horizontally
                block_top_left = (block_top_left[0], block_top_left[1] + width)
            # After finishing row j, move top_left vertically
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
                # Assign adjacent blocks to the correct block
                blocks[block_ids[i][j] - 1].adjacent_blocks = adjacent_blocks

    def send_blocks(self):
        """
        Sends the fully prepared block objects to each worker.
        """
        for b in self.blocks:
            comm.send({'state': 1}, dest=b.id, tag=10)
            comm.send(b, dest=b.id, tag=1)

    def send_units(self, blocks):
        """
        Sends the units to the correct block.
        """
        for i in range(len(blocks)):
            comm.send({'state': 20}, dest=i + 1, tag=10)
            comm.send(blocks[i]['units'], dest=i + 1, tag=2)

    def set_states(self, states, workers, worker_group):
        """
        Sends two different states: one to active workers, one to inactive.
        """
        for rank in range(1, self.worker_count + 1):
            if workers[rank - 1]:
                comm.send({'state': states[0], 'current_worker_group': worker_group}, dest=rank, tag=10)
            else:
                comm.send({'state': states[1], 'current_worker_group': worker_group}, dest=rank, tag=10)

    def set_current_workers(self, x, y):
        """
        Depending on (x, y) in {0,1}, sets a checkerboard pattern of active workers.
        If (x, y) == (-1, -1), all workers are active.
        """
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
        # 7) Gather final grid state
        finalGrid = [['.' for _ in range(Utils.N)] for _ in range(Utils.N)]
        # Instruct each worker to send its final block
        for rank in range(1, self.worker_count + 1):
            comm.send({'state': 10}, dest=rank, tag=10)
            block = comm.recv(source=rank, tag=10)
            # Merge block content into finalGrid
            for row_idx in range(block.top_left[0], block.bottom_right[0]):
                for col_idx in range(block.top_left[1], block.bottom_right[1]):
                    finalGrid[row_idx][col_idx] = str(
                        block.grid[row_idx - block.top_left[0]][col_idx - block.top_left[1]]
                    )
        for row in finalGrid:
            print(row)
        print()

    def run(self):
        """
        Main run logic:
        1) Parse general info (N, W, T, R).
        2) Calculate block sizes.
        3) Parse wave data and generate blocks for each wave.
        4) Send blocks to workers.
        5) Receive "blocks received" confirmations.
        6) Run R rounds of simulation with a 2x2 checkerboard scheme.
        7) Collect final grids and print.
        """
        # 1) Parse the general info into Utils class-level variables
        Utils.parse_general_info(self.lines)
        
        # 2) Broadcast config to all ranks
        config_data = {
            'N': Utils.N,
            'W': Utils.W,
            'T': Utils.T,
            'R': Utils.R,
        }
        comm.bcast(config_data, root=0)


        # 2) Calculate block sizes
        self.block_sizes = Utils.calculate_block_sizes(Utils.N, self.worker_count)

        # 3) Parse wave data
        self.wave_data = self.parse_wave_data(self.lines)

        self.blocks, self.block_ids = self.generate_blocks(
                Utils.N, 
                self.block_sizes
            )
        self.calculate_adjacent_blocks(self.block_ids, self.blocks)
        self.send_blocks()

        for wave_idx in range(1, Utils.W + 1):
            print(f"Wave {wave_idx}")
            wave = self.wave_data[wave_idx]

            blocks = [{} for _ in range(self.worker_count)]
            for rank in range(1, self.worker_count + 1):
                blocks[rank - 1]['units'] = []

            for faction in wave:
                for coord in wave[faction]:
                    # Use Utils to find the block ID from (x, y)
                    if(coord[0] < 0 or coord[1] < 0 or coord[0] >= Utils.N or coord[1] >= Utils.N):
                        continue
                    found_id = Utils.coordinates_to_block_id(coord[0], coord[1])
                    blocks[found_id - 1]['units'].append((faction, coord[0], coord[1]))

            self.send_units(blocks)
            self.gather_grids_and_print()

            # 6) Run R rounds with a 2x2 checkerboard scheme
            for _ in range(Utils.R):
                # --- Active time 1 (checkerboard step) ---
                for x in range(2):      # x in {0,1}
                    for y in range(2):  # y in {0,1}
                        current_workers = self.set_current_workers(x, y)
                        # State to active: 2, inactive: 3
                        self.set_states([2, 3], current_workers, x * 2 + y)

                        # Wait for active workers to finish
                        for rank in range(1, self.worker_count + 1):
                            if current_workers[rank - 1]:
                                comm.recv(source=rank, tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])

                        # Send "continue" or "skip" (tag=69) for workers
                        for rank in range(1, self.worker_count + 1):
                            if not current_workers[rank - 1]:
                                comm.send(None, dest=rank, tag=69)

                print("Round is starting")

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

                print("Attack is done")
                current_workers = [True] * self.worker_count
                self.set_states([6, 6], current_workers, -1)

                self.gather_grids_and_print()

                self.set_states([7, 7], current_workers, -1)

                print("Healing is done")
                self.gather_grids_and_print()
                print("Round is done")
                print()

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
                
            

        for rank in range(1, self.worker_count + 1):
            comm.send({'state': -1}, dest=rank, tag=10)


    # Uncomment if you had some alternate run logic
    # def run2(self):
    #     for i in range(1, self.worker_count):
    #         print(i)
    #         for j in range(1, self.worker_count + 1):
    #             comm.send(1 if i == j else 0, dest=j, tag=10)
    #         comm.recv(source=i, tag=MPI.ANY_TAG)
    #         for j in range(1, self.worker_count + 1):
    #             comm.send(None, dest=j, tag=3)
    #     for j in range(1, self.worker_count + 1):
    #         comm.send(-1, dest=j, tag=10)