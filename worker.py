from block import Block
from mpi4py import MPI

comm = MPI.COMM_WORLD



class Worker:

    def __init__(self, rank):
        self.received_blocks = []
        self.rank = rank
        self.state=0


    def receive_blocks(self):
        """
        Receive blocks from the manager (rank 0).
        """

        block_data = comm.recv(source=0, tag=1)
        print(f"Worker {self.rank}: Received block with ID {block_data.block_id} "
              f"from Manager.")
        self.received_blocks.append(block_data)



    def run(self):
        """
        Main method to run the worker process.
        """
        print(f"Worker {self.rank}: Ready to receive blocks.")
        self.receive_blocks()
        print(f"Worker {self.rank}: Finished processing.")

    def run2(self):
        self.state = comm.recv(source=0, tag=10)

        if self.state ==0:
            while True:
                coord,rank= comm.recv(source=MPI.ANY_SOURCE,tag=3)



