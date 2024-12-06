from mpi4py import MPI
import sys
from manager import Manager
from worker import Worker

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

manager = Manager("input.txt", "output.txt", size - 1)
workers = [Worker(i + 1) for i in range(size - 1)]

if rank == 0:
    manager.run()


else:
    workers[rank - 1].run()


    
