BLOCK_SIZE = 5

def coordinate_to_block_id(coord, N):
    return coord[0] // BLOCK_SIZE * (N // BLOCK_SIZE + N % BLOCK_SIZE) + coord[1] // BLOCK_SIZE

def block_id_to_block_index(block_id, N):
    return block_id // (N // BLOCK_SIZE + N % BLOCK_SIZE), block_id % (N // BLOCK_SIZE + N % BLOCK_SIZE)

def parse_general_info(lines):
    first_line = lines[0].strip().split()
    global N, W, T, R
    N = int(first_line[0])  # Grid size
    W = int(first_line[1])  # Number of waves
    T = int(first_line[2])  # Units per faction per wave
    R = int(first_line[3])  # Rounds per wave