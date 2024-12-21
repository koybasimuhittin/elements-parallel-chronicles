from mpi4py import MPI

N = 0
W = 0
T = 0
R = 0

comm = MPI.COMM_WORLD

worker_count = comm.Get_size() - 1
sqr_of_worker_count = (int)(worker_count ** 0.5)

def calculate_block_sizes(n, worker_count):
    initial_block_size = n // sqr_of_worker_count
    remaning_size = n % sqr_of_worker_count
    block_sizes = []
    for i in range(sqr_of_worker_count):
        block_sizes.append([])
        for j in range(sqr_of_worker_count):
            block_sizes[i].append((initial_block_size + (j < remaning_size), initial_block_size + (i < remaning_size)))
    
    return block_sizes

def coordinates_to_block_id(x, y, n, worker_count):
    block_size = n // sqr_of_worker_count
    remaning_size = n % sqr_of_worker_count

    if(x > remaning_size * (block_size + 1)):
        x -= remaning_size
        if(y > remaning_size * (block_size + 1)):
            y -= remaning_size
            return (x // (block_size)) + y // (block_size) * sqr_of_worker_count + 1    
        else:
            return (x // (block_size)) + y // (block_size + 1) * sqr_of_worker_count + 1
    else:
        if(y > remaning_size * (block_size + 1)):
            y -= remaning_size
            return (x // (block_size + 1)) + y // (block_size) * sqr_of_worker_count + 1
        else:
            return (x // (block_size + 1)) + y // (block_size + 1) * sqr_of_worker_count + 1 
        
def is_current_worker(worker_id, current_worker_group):
    if current_worker_group == -1:
        return True
    worker_id -= 1
    x = worker_id // sqr_of_worker_count
    y = worker_id % sqr_of_worker_count
    return x % 2 == current_worker_group // 2 and y % 2 == current_worker_group % 2
    

def parse_general_info(lines):
    first_line = lines[0].strip().split()
    global N, W, T, R
    N = int(first_line[0])  # Grid size
    W = int(first_line[1])  # Number of waves
    T = int(first_line[2])  # Units per faction per wave
    R = int(first_line[3])  # Rounds per wave
