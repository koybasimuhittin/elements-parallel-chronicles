from mpi4py import MPI
import re

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0: # # Manager process
    # Read and parse the input file
    with open("input.txt", "r") as file:
        lines = file.readlines()

    # Parse the first line for simulation parameters
    first_line = lines[0].strip().split()
    N = int(first_line[0])  # Grid size
    W = int(first_line[1])  # Number of waves
    T = int(first_line[2])  # Units per faction per wave
    R = int(first_line[3])  # Rounds per wave

    print(f"Manager: Simulation parameters - Grid: {N}x{N}, Waves: {W}, Units/Faction/Wave: {T}, Rounds/Wave: {R}")

    # Parse wave data
    wave_data = {}
    wave_index = 0
    for line in lines[1:]:
        line = line.strip()
        if line.startswith("Wave"):
            wave_index += 1
            wave_data[wave_index] = {"E": [], "F": [], "W": [], "A": []}
        elif line.startswith(("E:", "F:", "W:", "A:")):
            faction, coordinates = line.split(":")
            # Parse coordinates
            coords = [
                tuple(map(int, coord.split()))
                for coord in re.findall(r"\d+ \d+", coordinates)
            ]
            # Validate coordinates
            for x, y in coords:
                if not (0 <= x < N and 0 <= y < N):
                    raise ValueError(f"Invalid coordinate ({x}, {y}) out of bounds.")
                if coords.count((x, y)) > 1:
                    raise ValueError(f"Duplicate coordinate ({x}, {y}) in faction {faction}.")
            wave_data[wave_index][faction] = coords

    print(f"Manager: Parsed wave data: {wave_data}")

    # Distribute wave data to workers
    for wave in range(1, W + 1):
        for worker_rank in range(1, size):
            if wave > len(wave_data):  # If no more waves, send empty data
                comm.send(None, dest=worker_rank, tag=0)
                continue

            # Send wave data to worker
            wave_info = {
                "wave": wave,
                "grid_size": N,
                "rounds": R,
                "factions": wave_data[wave],
            }
            comm.send(wave_info, dest=worker_rank, tag=0)
            print(f"Manager: Sent data for Wave {wave} to Worker {worker_rank}")

    # Signal workers to terminate
    for worker_rank in range(1, size):
        comm.send(None, dest=worker_rank, tag=1)  # Termination signal

elif rank > 0:  # Worker processes
    while True:
        # Receive data from the manager
        data = comm.recv(source=0, tag=MPI.ANY_TAG)

        if data is None:  # Termination signal
            print(f"Worker {rank}: Terminating.")
            break

        # Process wave data
        wave = data["wave"]
        grid_size = data["grid_size"]
        rounds = data["rounds"]
        factions = data["factions"]

        print(f"Worker {rank}: Processing Wave {wave} with data: {factions}")
