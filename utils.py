global N, W, T, R

def calculate_block_sizes(n, worker_count):
    sqr_of_worker = int(worker_count ** 0.5)
    initial_block_size = n // sqr_of_worker
    remaning_size = n % sqr_of_worker
    block_sizes = []
    for i in range(sqr_of_worker):
        block_sizes.append([])
        for j in range(sqr_of_worker):
            block_sizes[i].append((initial_block_size + (j < remaning_size), initial_block_size + (i < remaning_size)))
    
    return block_sizes

def coordinates_to_block_id(x, y, n, worker_count):
    sqr_of_worker = int(worker_count ** 0.5)
    block_size = n // sqr_of_worker
    remaning_size = n % sqr_of_worker

    if(x > remaning_size * (block_size + 1)):
        x -= remaning_size
        if(y > remaning_size * (block_size + 1)):
            y -= remaning_size
            return (x // (block_size)) + y // (block_size) * sqr_of_worker + 1    
        else:
            return (x // (block_size)) + y // (block_size + 1) * sqr_of_worker + 1
    else:
        if(y > remaning_size * (block_size + 1)):
            y -= remaning_size
            return (x // (block_size + 1)) + y // (block_size) * sqr_of_worker + 1
        else:
            return (x // (block_size + 1)) + y // (block_size + 1) * sqr_of_worker + 1 
    

def parse_general_info(lines):
    first_line = lines[0].strip().split()
    global N, W, T, R
    N = int(first_line[0])  # Grid size
    W = int(first_line[1])  # Number of waves
    T = int(first_line[2])  # Units per faction per wave
    R = int(first_line[3])  # Rounds per wave
