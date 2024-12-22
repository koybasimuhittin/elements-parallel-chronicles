from mpi4py import MPI
from utils import Utils
from block import Block
from unit import Unit, EarthUnit, FireUnit, WaterUnit, AirUnit
from constants import MESSAGES

comm = MPI.COMM_WORLD


def print_grid(grid, rank=None):
    """
    Helper function to convert a 2D grid into a string for debugging.
    """
    string = f"rank: {rank}\n"
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
        self.new_air_units = []

    def receive_block(self):
        """
        Receive block data from the Manager (rank 0).
        """
        block_data = comm.recv(source=0, tag=1)
        self.block: Block = block_data

    def receive_units(self):
        units_data = comm.recv(source=0, tag=2)
        self.block.add_units(units_data)

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
                self.state = 0

            elif self.state == 20:
                self.receive_units()
                self.state = 0
            
            elif self.state == 21:
                for x, y in self.new_water_units:
                    grid_x, grid_y = self.block.get_block_coordinates(x, y)
                    self.block.grid[grid_x][grid_y] = WaterUnit(x, y)

                self.new_water_units.clear()

                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            fire_unit = self.block.grid[i][j]
                            if fire_unit.unit_type == 'F':
                                fire_unit.reset_inferno()
            # 2) Worker becomes "receiver" of boundary data
            elif self.state == 2:
                self.block.reset_boundary()
                for neighbor in self.block.adjacent_blocks:
                    boundary_data = comm.recv(source=neighbor['block_id'], tag=10)
                    self.block.update_boundary(boundary_data['grid'], neighbor['position'])
                self.apply_inferno()
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

            # 7) Heal Phase
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

                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'],
                          dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            elif self.state == 9:
                self.take_water_unit()
                self.state = 0

            elif self.state == 10:  # calculate the new position of the air unit
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            air_unit = self.block.grid[i][j]
                            if air_unit.unit_type == 'A':
                                new_coordinates = self.air_movement(air_unit)
                                air_unit.change_position(new_coordinates)
                                #print(print_grid(self.block.grid_with_boundary, self.rank))
                                if self.block.is_coordinate_inside(new_coordinates[0], new_coordinates[1]):
                                    self.new_air_units.append(air_unit)
                                else:
                                    self.send_air_unit(air_unit)
                for i in range(len(self.block.grid)):
                    for j in range(len(self.block.grid[0])):
                        if self.block.grid[i][j] != '.':
                            air_unit = self.block.grid[i][j]
                            if air_unit.unit_type == 'A':
                                self.block.grid[i][j] = '.'  # remove the air unit
                
                comm.send(MESSAGES['ACTIVE_TIME_DONE']['message'],
                          dest=MESSAGES['ACTIVE_TIME_DONE']['dest'],
                          tag=MESSAGES['ACTIVE_TIME_DONE']['tag'])
                self.state = 0

            elif self.state == 11:
                self.take_air_unit()
                self.state = 0

            elif self.state == 12:
                for air_unit in self.new_air_units:
                    x,y = self.block.get_block_coordinates(air_unit.x,air_unit.y)
                    new_position=self.block.get_grid_element(air_unit.x,air_unit.y)
                    if new_position == '.':
                        self.block.grid[x][y]=air_unit
                    else:
                        self.block.grid[x][y].unite(air_unit)
                
                self.new_air_units.clear()
                self.state = 0

            # Anything else or termination
            elif self.state == 13:
                # Send block back to manager (for final collection)
                comm.send(self.block, dest=0, tag=10)

            elif self.state == -1:
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
        dest_block_id = Utils.coordinates_to_block_id(x, y)
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

    def send_air_unit(self, air_unit):
        dest_block_id = Utils.coordinates_to_block_id(air_unit.x, air_unit.y)
        comm.send(air_unit, dest=dest_block_id, tag=72)

    def take_air_unit(self):
        while True:
            air_unit = comm.recv(source=MPI.ANY_SOURCE, tag=72)
            if air_unit is None:
                self.state = 0
                return

            self.new_air_units.append(air_unit)

    def air_movement(self, unit: AirUnit):
        def calculate_number_of_enemies(x, y):
            cnt = 0
            for dx, dy in unit.directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < Utils.N and 0 <= ny < Utils.N:
                    enemy = self.block.get_grid_with_boundary_element(nx, ny)
                    if enemy == '.':
                        new_x, new_y = nx + dx, ny + dy
                        if 0 <= new_x < Utils.N and 0 <= new_y < Utils.N:
                            new_enemy = self.block.get_grid_with_boundary_element(new_x, new_y)
                            if new_enemy != '.' and new_enemy != 'A':
                                cnt += 1
                    elif enemy != 'A':
                        cnt += 1

            return cnt

        new_coordinates = (unit.x, unit.y)
        max_enemies = calculate_number_of_enemies(unit.x, unit.y)
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        self.block.set_grid_with_boundary_element(unit.x,unit.y,'.')
        for dx, dy in directions:
            nx, ny = unit.x + dx, unit.y + dy
            if 0 <= nx < Utils.N and 0 <= ny < Utils.N:
                if self.block.get_grid_with_boundary_element(nx, ny) != '.':
                    continue
                number_of_enemies = calculate_number_of_enemies(nx, ny)
                if number_of_enemies > max_enemies:
                    new_coordinates = (nx, ny)
                    max_enemies = number_of_enemies
        self.block.set_grid_with_boundary_element(unit.x, unit.y, 'A')
        return new_coordinates

    def apply_damage(self, coordinates, unit: Unit):
        dest_block_id = Utils.coordinates_to_block_id(coordinates[0], coordinates[1])
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
                if local_unit == ".":
                    comm.send(0, dest=attacker_rank, tag=70)
                else:
                    comm.send(1, dest=attacker_rank, tag=70)# there is a friend
            else:
                # Apply damage
                local_unit.damage_taken += damage
                comm.send(2, dest=attacker_rank, tag=70)

    def attack(self, unit: Unit):
        """
        Handle the logic of a single unit attacking its potential targets.
        For example, each unit might have 'directions' indicating adjacent cells.
        If it's an Air unit, it may have extended range, etc.
        """

        if(not unit.can_attack()):
            return

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
                        return 2
                    elif local_unit != ".":
                        return 1
                else:
                    # Otherwise, send damage to another block
                    number = self.apply_damage((x, y), unit)
                    if number == 2:
                        unit.attack_done = True
                        return 2
                    elif number == 1:
                        return 1 # The grid is full
            return 0

        # Attack each direction once; if Air unit, it may continue
        for dx, dy in unit.directions:
            nx, ny = unit.x + dx, unit.y + dy
            did_attack = attack_coord(nx, ny)
            if did_attack == 2 and unit.unit_type == 'F':
                unit.enemies_attacked.append((nx, ny))

            # Example: Air unit can "pierce" one more cell
            if did_attack == 0 and unit.unit_type == 'A':
                nx2, ny2 = nx + dx, ny + dy
                attack_coord(nx2, ny2)

    def apply_inferno(self):

        def is_inferno_available(unit: FireUnit):
            for [row, column] in unit.enemies_attacked:
                enemy = self.block.get_grid_with_boundary_element(row, column)
                if enemy == '.':
                    return True

            return False

        for i in range(len(self.block.grid)):
            for j in range(len(self.block.grid[0])):
                if self.block.grid[i][j] != '.':
                    unit = self.block.grid[i][j]
                    if unit.unit_type == 'F':
                        if is_inferno_available(unit):
                            unit.inferno()

                        unit.reset_enemies_attacked()

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
