from mpi4py import MPI
import sys
from manager import Manager
from worker import Worker
import time

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

start_time = time.time()

if(len(sys.argv) < 2):
    input_file = "input.txt"
    output_file = "output.txt"

else:
    input_file = sys.argv[1]
    output_file = sys.argv[2]

manager = Manager(input_file, output_file, size - 1)
workers = [Worker(i + 1) for i in range(size - 1)]

if rank == 0:
    manager.run()

else:
    workers[rank - 1].run()

end_time = time.time()  

print("Rank", rank, "took", (end_time - start_time), "seconds to run.")


    
