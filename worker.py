from block import Block
from mpi4py import MPI
import utils

from constants import MESSAGES

comm = MPI.COMM_WORLD


# state 0: idle
# state 1: recieve blocks
# state 2: active
# state 3: only send data

class Worker:

    def __init__(self, rank):
        self.rank = rank
        self.state = 0
        self.block = None

    def receive_block(self):
        """
        Receive blocks from the manager (rank 0).
        """

        block_data = comm.recv(source=0, tag=1)
        print(f"Worker {self.rank}: Received block with ID {block_data.id} "
              f"from Manager.")
        self.block = block_data

    def run(self):
        """
        Main method to run the worker process.
        """
        while True:
            self.state = comm.irecv(source=0, tag=10).wait()
            print(f"Worker {self.rank}: Received state {self.state}.")
            if (self.state == 1):
                print(f"Worker {self.rank}: Ready to receive blocks.")
                self.receive_block()
                print(f"Worker {self.rank}: Finished processing.")
                comm.send(MESSAGES['BLOCKS_RECEIVED']['message'], dest=MESSAGES['BLOCKS_RECEIVED']['dest'],
                          tag=MESSAGES['BLOCKS_RECEIVED']['tag'])
                self.state = 0
            elif (self.state == 2):
                print(f"Worker {self.rank}: Active.")



                self.state = 0
            elif (self.state == 3):
                print(f"Worker {self.rank}: Only send data.")
                self.state = 0
            else:
                pass


def request_data(self, coordinates):
    destination = utils.coordinates_to_block_id(coordinates[0], coordinates[1], utils.N, comm.Get_size() - 1)
    comm.send([coordinates, self.rank], dest=destination, tag=69)
    data = comm.recv(source=destination, tag=MPI.ANY_TAG)


def send_data(self):
    a = comm.recv(source=MPI.ANY_SOURCE, tag=69)
    if a is None:
        self.state = -1
        pass
    coord, rank = a[0], a[1]
    data = self.block.get_grid_element(coord[0],coord[1])
    comm.send(data, dest=rank, tag=69)



def run2(self):
    while True:
        self.state = comm.recv(source=0, tag=10)
        if self.state == -1:
            break

        if self.state == 0:
            while True:
                a = comm.recv(source=MPI.ANY_SOURCE, tag=3)
                if a is None:
                    break
                coord, rank = a[0], a[1]

                print(self.rank)
        elif self.state == 1:
            comm.send([(5, 6), self.rank], dest=4, tag=3)
            el = comm.recv(source=4, tag=4)
            if not el is None:
                print(el)
            else:
                print("asdas")
            comm.send("END", dest=0, tag=0)
            comm.recv(source=MPI.ANY_SOURCE, tag=3)
