from mpi4py import MPI
from utils import Utils  # <-- Import the entire Utils class
from block import Block
from unit import Unit, EarthUnit, FireUnit, WaterUnit, AirUnit
import time
from constants import MESSAGES

comm = MPI.COMM_WORLD


def print_grid(grid):
    """
    Helper function to convert a 2D grid into a string for debugging.
    """
    string = ""
    for row in grid:
        row_str = ""
        for cell in row:
            row_str += str(cell)
        string += row_str + "\n"
    return string


class Worker:

    def __init__(self, rank):
        self.rank = rank
        self.state = 0
        self.block = None
        self.new_water_units = set()

    def receive_block(self):
        """
        Receive block data from the Manager (rank 0).
        """
        block_data = comm.recv(source=0, tag=1)
        self.block: Block = block_data

    def extract_block(self, position):
        """
        Extracts specific 'boundary' sub-grids to send to neighbors.
        Each position corresponds to a direction around the block:
          0 -> top-left corner, 1 -> top edge, 2 -> top-right corner, etc.
        """
        # Example extraction size is 3x3, but can be adjusted as needed
        if position == 0:
            return [row[0:3] for row in self.block.grid[0:3]]
        elif position == 1:
            return [row[:] for row in self.block.grid[0:3]]
        elif position == 2:
            return [row[-3:] for row in self.block.grid[0:3]]
        elif position == 3:
            return [row[-3:] for row in self.block.grid]
        elif position == 4:
            return [row[-3:] for row in self.block.grid[-3:]]
        elif position == 5:
            return [row[:] for row in self.block.grid[-3:]]
        elif position == 6:
            return [row[0:3] for row in self.block.grid[-3:]]
        elif position == 7:
            return [row[0:3] for row in self.block.grid]
        # Default empty if position is somehow out of range
        return []

    def run(self):
        """
        Main loop for the worker process.
        """

        config_data = comm.bcast(None, root=0)
        # Update Utils class variables
        Utils.N = config_data['N']
        Utils.W = config_data['W']
        Utils.T = config_data['T']
        Utils.R = config_data['R']

        while True:
            # Receive control/state info from Manager (rank=0)
            data = comm.recv(source=0, tag=10)
            self.state = data['state']

            # 1) Receive blocks from manager
            if self.state == 1:
                self.receive_block()
                comm.send(MESSAGES['BLOCKS_RECEIVED']['message'],
                          dest=MESSAGES['BLOCKS_RECEIVED']['dest'],
                          tag=MESSAGES['BLOCKS_RECEIVED']['tag'])
                self.state = 0

            # 2) Worker becomes "receiver" of boundary data
            elif self.state == 2:
                for neighbor in self.block.adjacent_blocks:
                    boundary_data = comm.recv(source=neighbor['block_id'], tag=10)
                    self.block.update_boundary(boundary_data['grid'], neighbor['position'])

                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'],
                          dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            # 3) Worker becomes "sender" of boundary data
            elif self.state == 3:
                current_group = data['current_worker_group']
                for neighbor in self.block.adjacent_blocks:
                    # Only send to neighbors that are also in the active checkerboard group
                    if Utils.is_current_worker(neighbor['block_id'], current_group):
                        comm.send({'grid': self.extract_block(neighbor['position']), 'position': neighbor['position']},
                                  dest=neighbor['block_id'], tag=10)
                self.state = 0

            # 4) Attack Phase
            elif self.state == 4:
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            self.attack(self.block.grid[i][j])
                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'],
                          dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            # 5) Take Damage Phase
            elif self.state == 5:
                self.take_damage()
                self.state = 0

            # 6) Resolution Phase
            elif self.state == 6:
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            unit: Unit = self.block.grid[i][j]
                            # Example: Earth units may fortify
                            if unit.unit_type == 'E':
                                unit: EarthUnit
                                unit.fortify()

                            # Apply accumulated damage
                            unit.health -= unit.damage_taken
                            unit.damage_taken = 0

                            # Kill unit if health <= 0
                            if not unit.is_alive():
                                self.block.grid[i][j] = '.'
                self.state = 0

            # 8) Heal Phase
            elif self.state == 7:
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            unit = self.block.grid[i][j]
                            # If the unit hasn't attacked yet, it can heal
                            if not unit.attack_done:
                                unit.heal()
                            # Reset its attack state
                            unit.attack_done = False
                self.state = 0
            elif self.state == 8:  # water floods
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            water_unit = self.block.grid[i][j]
                            if water_unit.unit_type == 'W':
                                self.create_water_unit(water_unit)
            elif self.state == 9:
                self.take_water_unit()
                self.state = 0

            # Anything else or termination
            elif self.state == 10:
                # Send block back to manager (for final collection)
                comm.send(self.block, dest=0, tag=10)
            elif self.state ==11: # start wave
                for x,y in self.new_water_units:
                    grid_x,grid_y = self.block.get_block_coordinates(x,y)
                    self.block.grid[grid_x][grid_y] = WaterUnit(x, y)
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            fire_unit = self.block.grid[i][j]
                            if fire_unit.unit_type == 'F':
                                fire_unit.reset_inferno()



            elif self.state == -1:
                print(f"Worker {self.rank}: Terminating.")
                break

    def create_water_unit(self, water_unit: WaterUnit):
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dx, dy in directions:
            nx, ny = water_unit.x + dx, water_unit.y + dy
            if 0 <= nx < Utils.N and 0 <= ny < Utils.N:
                if self.block.is_coordinate_inside(nx, ny):
                    if self.block.get_grid_element(nx, ny) == '.':
                        self.new_water_units.add((nx, ny))
                        break
                else:
                    is_creation_successful = self.send_water_unit(nx, ny)
                    if is_creation_successful:
                        break

    def send_water_unit(self, x, y):
        dest_block_id = Utils.coordinates_to_block_id(
            x, y, Utils.N, Utils.worker_count
        )
        comm.send([x, y, self.rank], dest=dest_block_id, tag=71)
        success = comm.recv(source=dest_block_id, tag=71)
        return success

    def take_water_unit(self):
        while True:
            data = comm.recv(source=MPI.ANY_SOURCE, tag=71)
            if data is None:
                self.state = 0
                return

            x, y, sender_rank = data
            local_unit = self.block.get_grid_element(x, y)
            # If the cell is empty, it's a valid target
            if local_unit == ".":
                self.new_water_units.add((x, y))
                comm.send(True, dest=sender_rank, tag=71)
            else:
                comm.send(False, dest=sender_rank, tag=71)

    def apply_damage(self, coordinates, unit: Unit):
        dest_block_id = Utils.coordinates_to_block_id(
            coordinates[0], coordinates[1], Utils.N, Utils.worker_count
        )
        comm.send([coordinates, unit.attack_power, unit.unit_type, unit.x, unit.y, self.rank],
                  dest=dest_block_id, tag=70)
        # Wait for confirmation (True = damage applied, False = blocked)
        success = comm.recv(source=dest_block_id, tag=70)
        return success

    def take_damage(self):
        while True:
            data = comm.recv(source=MPI.ANY_SOURCE, tag=70)
            if data is None:
                # No more attack messages
                self.state = 0
                return

            coord, damage, enemy_type, attacker_x, attacker_y, attacker_rank = data
            local_unit = self.block.get_grid_element(coord[0], coord[1])
            # If the cell is empty or matches the enemy's faction, it's a valid target
            if local_unit == "." or local_unit.unit_type == enemy_type:
                # Attack is blocked (friendly or invalid target)
                comm.send(False, dest=attacker_rank, tag=70)
            else:
                # Apply damage
                local_unit.damage_taken += damage
                comm.send(True, dest=attacker_rank, tag=70)

    def attack(self, unit: Unit):
        """
        Handle the logic of a single unit attacking its potential targets.
        For example, each unit might have 'directions' indicating adjacent cells.
        If it's an Air unit, it may have extended range, etc.
        """

        def attack_coord(x, y):
            # If within the global grid
            if 0 <= x < Utils.N and 0 <= y < Utils.N:
                # If target cell is in the same block:
                if self.block.is_coordinate_inside(x, y):
                    local_unit = self.block.get_grid_element(x, y)
                    # If target cell is not empty AND is a different faction
                    if not (local_unit == "." or local_unit.unit_type == unit.unit_type):
                        local_unit.damage_taken += unit.attack_power
                        unit.attack_done = True
                        return True
                else:
                    # Otherwise, send damage to another block
                    if self.apply_damage((x, y), unit):
                        unit.attack_done = True
                        return True
            return False

        # Attack each direction once; if Air unit, it may continue
        for dx, dy in unit.directions:
            nx, ny = unit.x + dx, unit.y + dy
            did_attack = attack_coord(nx, ny)
            if unit.unit_type == 'F':
                unit.enemies_attacked.append((nx, ny))

            # Example: Air unit can "pierce" one more cell
            if not did_attack and unit.unit_type == 'A':
                nx2, ny2 = nx + dx, ny + dy
                attack_coord(nx2, ny2)

    # def request_data(self, coordinates):
    #     """
    #     Example of requesting data from another worker's block.
    #     """
    #     dest_block_id = Utils.coordinates_to_block_id(
    #         coordinates[0], coordinates[1], Utils.N, Utils.worker_count
    #     )
    #     comm.send([coordinates, self.rank], dest=dest_block_id, tag=69)
    #     data = comm.recv(source=dest_block_id, tag=MPI.ANY_TAG)
    #     print(f"Worker {self.rank}: Requested data at {coordinates}, received: {data}")

    # def send_data(self):
    #     """
    #     Example of providing data to a requesting worker (tag=69).
    #     """
    #     request = comm.recv(source=MPI.ANY_SOURCE, tag=69)
    #     if request is None:
    #         self.state = -1
    #         return
    #     coord, requester_rank = request
    #     data = self.block.get_grid_element(coord[0], coord[1])
    #     comm.send(data, dest=requester_rank, tag=69)
