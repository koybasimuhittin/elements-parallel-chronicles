from mpi4py import MPI

class Utils:
    # Class-level defaults (will be updated after parsing)
    N = 0
    W = 0
    T = 0
    R = 0

    # MPI world
    comm = MPI.COMM_WORLD
    worker_count = comm.Get_size() - 1
    sqr_of_worker_count = int(worker_count ** 0.5)

    @classmethod
    def parse_general_info(cls, lines):
        """
        Reads the first line to set N, W, T, R on the class.
        """
        first_line = lines[0].strip().split()
        cls.N = int(first_line[0])  # Grid size
        cls.W = int(first_line[1])  # Number of waves
        cls.T = int(first_line[2])  # Units per faction per wave
        cls.R = int(first_line[3])  # Rounds per wave

    @classmethod
    def calculate_block_sizes(cls, n, worker_count):
        """
        Calculates block sizes using the class's sqr_of_worker_count.
        You can also omit n and worker_count if you prefer using cls.N/cls.worker_count.
        """
        # If you want to rely on class attributes, you can do:
        # n = n or cls.N
        # worker_count = worker_count or cls.worker_count
        # but here it takes them as parameters explicitly.
        initial_block_size = n // cls.sqr_of_worker_count
        remaining_size = n % cls.sqr_of_worker_count
        block_sizes = []

        for i in range(cls.sqr_of_worker_count):
            row_sizes = []
            for j in range(cls.sqr_of_worker_count):
                width  = initial_block_size + (j < remaining_size)
                height = initial_block_size + (i < remaining_size)
                row_sizes.append((width, height))
            block_sizes.append(row_sizes)

        return block_sizes

    @classmethod
    def coordinates_to_block_id(cls, y, x):

        """
        Computes block ID given (x, y) coordinates, using the class's sqr_of_worker_count.
        """
        n = cls.N
        block_size = n // cls.sqr_of_worker_count
        remaining_size = n % cls.sqr_of_worker_count

        # Adjust x, y and compute block ID
        if x > remaining_size * (block_size + 1):
            x -= remaining_size
            if y > remaining_size * (block_size + 1):
                y -= remaining_size
                return (x // block_size) + (y // block_size) * cls.sqr_of_worker_count + 1    
            else:
                return (x // block_size) + (y // (block_size + 1)) * cls.sqr_of_worker_count + 1
        else:
            if y > remaining_size * (block_size + 1):
                y -= remaining_size
                return (x // (block_size + 1)) + (y // block_size) * cls.sqr_of_worker_count + 1
            else:
                return (x // (block_size + 1)) + (y // (block_size + 1)) * cls.sqr_of_worker_count + 1

    @classmethod
    def is_current_worker(cls, worker_id, current_worker_group):
        """
        Determines if the given worker_id belongs to the 'active' group for the current round.
        """
        if current_worker_group == -1:
            return True
        # Convert worker_id to 0-based
        worker_id -= 1
        x = worker_id // cls.sqr_of_worker_count
        y = worker_id % cls.sqr_of_worker_count
        return (x % 2 == current_worker_group // 2) and (y % 2 == current_worker_group % 2)