from mpi4py import MPI
import block  # Assuming `block` module is defined and contains the `Block` class.


class Worker:

    def __init__(self):
        self.received_blocks = []

    def receive_blocks(self):
        """
        Receive blocks from the manager (rank 0).
        """
        while True:
            # Use MPI.Status to probe messages and handle dynamic communication.
            status = MPI.Status()
            block_data = self.comm.recv(source=0, tag=1, status=status)

            if block_data == "END":  # Signal to terminate receiving
                print(f"Worker {self.rank}: Received termination signal. Exiting.")
                break

            print(f"Worker {self.rank}: Received block with ID {block_data.block_id} "
                  f"from Manager.")
            self.received_blocks.append(block_data)



    def run(self):
        """
        Main method to run the worker process.
        """
        print(f"Worker {self.rank}: Ready to receive blocks.")
        self.receive_blocks()
        self.process_blocks()
        print(f"Worker {self.rank}: Finished processing.")

