from mpi4py import MPI
import sys
import manager
import worker

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

manager = manager.Manager("input.txt", "output.txt", size - 1)
workers = [worker.Worker(i + 1) for i in range(size - 1)]

if rank == 0:
    manager.run()


else:
    workers[rank - 1].run()


    
