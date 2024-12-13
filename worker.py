from block import Block
from mpi4py import MPI
import utils
comm = MPI.COMM_WORLD

# state 1: recieve blocks
# state 2: active
# state 3: only send data

class Worker:

    def __init__(self, rank):
        self.blocks = []
        self.rank = rank
        self.state = -1


    def receive_blocks(self):
        """
        Receive blocks from the manager (rank 0).
        """

        block_data = comm.recv(source=0, tag=1)
        print(f"Worker {self.rank}: Received block with ID {block_data.id} "
              f"from Manager.")
        self.blocks.append(block_data)


    def run(self):
        """
        Main method to run the worker process.
        """
        while True:
            if(self.state == 1):
                print(f"Worker {self.rank}: Ready to receive blocks.")
                self.receive_blocks()                             
                print(f"Worker {self.rank}: Finished processing.")
            elif(self.state == 2):
                print(f"Worker {self.rank}: Active.")
                pass
            elif(self.state == 3):
                print(f"Worker {self.rank}: Only send data.")
                pass

    def run2(self):
        while True:
            self.state = comm.recv(source=0, tag=10)
            if self.state == -1:
                break

            if self.state == 0:
                while True:
                    a= comm.recv(source=MPI.ANY_SOURCE,tag=3)
                    if a is None:
                        break
                    coord, rank =a[0],a[1]


                    print(self.rank)
            elif self.state == 1:
                comm.send([(5,6),self.rank],dest=4,tag=3)
                el=comm.recv(source=4,tag=4)
                if not el is None:
                    print(el)
                else:
                    print("asdas")
                comm.send("END", dest=0, tag=0)
                comm.recv(source=MPI.ANY_SOURCE,tag=3)


