from block import Block
from mpi4py import MPI
import utils
from unit import Unit, EarthUnit, FireUnit, WaterUnit, AirUnit
import time

from constants import MESSAGES

comm = MPI.COMM_WORLD
worker_count = comm.Get_size() - 1
sqr_of_worker_count = worker_count ** 0.5


def print_grid(grid):
    string = ""
    for row in grid:
        row_str = ""
        for cell in row:
            row_str += str(cell) + ""
        string += "".join(row_str) + "\n"
    return string


# state 0: idle
# state 1: recieve blocks
# state 2: recieve boundaries
# state 3: send boundaries

class Worker:

    def __init__(self, rank):
        self.rank = rank
        self.state = 0
        self.block = None

    def receive_block(self):
        """
        Receive blocks from the manager (rank 0).
        """

        block_data = comm.recv(source=0, tag=1)
        print(f"Worker {self.rank}: Received block with ID {block_data.id} "
              f"from Manager.")
        self.block: Block = block_data

    def extract_block(self, position):
        if position == 0:
            # Top-left 2x2 block
            return [row[0:3] for row in self.block.grid[0:3]]
        elif position == 1:
            # Top 2 rows, all columns
            return [row[:] for row in self.block.grid[0:3]]
        elif position == 2:
            # Top 2 rows, last 2 columns
            return [row[-3:] for row in self.block.grid[0:3]]
        elif position == 3:
            # All rows, last 2 columns
            return [row[-3:] for row in self.block.grid]
        elif position == 4:
            # Bottom 2 rows, last 2 columns
            return [row[-3:] for row in self.block.grid[-3:]]
        elif position == 5:
            # Bottom 2 rows, all columns
            return [row[:] for row in self.block.grid[-3:]]
        elif position == 6:
            # Bottom 2 rows, first 2 columns
            return [row[0:3] for row in self.block.grid[-3:]]
        elif position == 7:
            # All rows, first 2 columns
            return [row[0:3] for row in self.block.grid]

    def run(self):
        """
        Main method to run the worker process.
        """
        while True:
            data = comm.recv(source=0, tag=10)
            self.state = data['state']
            if self.state == 1:
                self.receive_block()
                comm.send(MESSAGES['BLOCKS_RECEIVED']['message'], dest=MESSAGES['BLOCKS_RECEIVED']['dest'],
                          tag=MESSAGES['BLOCKS_RECEIVED']['tag'])
                self.state = 0

            elif self.state == 2:
                print(f"Worker {self.rank}: Receiving boundaries.")
                for neighbor in self.block.adjacent_blocks:
                    data = comm.recv(source=neighbor['block_id'], tag=10)
                    print(
                        f"Worker {self.rank}: Received boundary data from Worker {neighbor['block_id']}. Data: \n{print_grid(data)}")

                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'], dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            elif self.state == 3:
                print(f"Worker {self.rank}: Sending boundaries.")
                for neighbor in self.block.adjacent_blocks:
                    if utils.is_current_worker(neighbor['block_id'], data['current_worker_group']):
                        print(f"Worker {self.rank}: Sending block to Worker {neighbor['block_id']}.")
                        comm.send(self.extract_block(neighbor['position']), dest=neighbor['block_id'], tag=10)
                self.state = 0

            elif self.state == 4:  # attack phase one of the 4 groups attacks
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            self.attack( self.block.grid[i][j])

                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'], dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            elif self.state == 5:  # other 3 takes the damages
                self.take_damage()
                self.state = 0

            elif self.state == 6:  # resolution phase
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            unit: Unit = self.block.grid[i][j]
                            if unit.unit_type == 'E':
                                unit: EarthUnit
                                unit.fortify()

                            unit.health -= unit.damage_taken
                            unit.damage_taken = 0

                            if not unit.is_alive():  # unit is dead !!!! TODO: add inferno ability
                                self.block[i][j] = '.'

            elif self.state == 8:  # heal phase
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            unit = self.block.grid[i][j]
                            if not unit.attack_done:
                                unit.heal()
                            unit.attack_done = False




            else:
                pass

    def apply_damage(self, coordinates, unit: Unit | EarthUnit | FireUnit | WaterUnit | AirUnit):
        destination = utils.coordinates_to_block_id(coordinates[0], coordinates[1], utils.N, worker_count)
        comm.send([coordinates, unit.attack_power, unit.unit_type, self.rank], dest=destination, tag=70)
        is_attack_successful = comm.recv(source=destination, tag=70)
        return is_attack_successful

    def take_damage(self):
        while True:
            data = comm.recv(source=MPI.ANY_SOURCE, tag=70)
            if data is None:
                self.state = 0
                return
            coord, damage, unit_type, rank = data[0], data[1], data[2], data[3]
            enemy: Unit = self.block.get_grid_element(coord[0], coord[1])
            if not (enemy == "." or enemy.unit_type == unit_type):
                comm.send(False, dest=rank, tag=70)
            else:
                enemy.damage_taken += damage
                comm.send(True, dest=rank, tag=70)

    def attack(self, unit: Unit | EarthUnit | FireUnit | WaterUnit | AirUnit):
        """
        Determine targets in the attack pattern and deal damage.
        """

        def attack_to_coord(x, y):
            if 0 <= x < utils.N and 0 <= y < utils.N:
                if self.block.is_coordinate_inside(x, y):
                    enemy: Unit = self.block.get_grid_element(x, y)
                    if not (enemy == "." or enemy.unit_type == unit.unit_type):
                        enemy.damage_taken += unit.attack_power
                        unit.attack_done = True
                        return True
                else:
                    is_attack_successful = self.apply_damage((x, y), unit.attack_power)
                    if is_attack_successful:
                        unit.attack_done = True
                        return True

            return False

        for dx, dy in unit.directions:
            nx, ny = unit.x + dx, unit.y + dy
            is_attack_done = attack_to_coord(nx, ny)
            if not (is_attack_done) and unit.unit_type == 'A':
                nx, ny = nx + dx, ny + dy
                attack_to_coord(nx, ny)

    def request_data(self, coordinates):
        destination = utils.coordinates_to_block_id(coordinates[0], coordinates[1], utils.N, comm.Get_size() - 1)
        comm.send([coordinates, self.rank], dest=destination, tag=69)
        data = comm.recv(source=destination, tag=MPI.ANY_TAG)

    def send_data(self):
        a = comm.recv(source=MPI.ANY_SOURCE, tag=69)
        if a is None:
            self.state = -1
            pass
        coord, rank = a[0], a[1]
        data = self.block.get_grid_element(coord[0], coord[1])
        comm.send(data, dest=rank, tag=69)


"""
def run2(self):
    while True:
        self.state = comm.recv(source=0, tag=10)
        if self.state == -1:
            break

        if self.state == 0:
            while True:
                a = comm.recv(source=MPI.ANY_SOURCE, tag=3)
                if a is None:
                    break
                coord, rank = a[0], a[1]

                print(self.rank)
        elif self.state == 1:
            comm.send([(5, 6), self.rank], dest=4, tag=3)
            el = comm.recv(source=4, tag=4)
            if not el is None:
                print(el)
            else:
                print("asdas")
            comm.send("END", dest=0, tag=0)
            comm.recv(source=MPI.ANY_SOURCE, tag=3)
"""
