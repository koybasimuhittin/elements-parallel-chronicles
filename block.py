class Block:
    def __init__(self, factions, top_left, bottom_right, block_id, worker_rank, adjacent_blocks):
        self.factions = factions
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.block_id = block_id
        self.worker_rank = worker_rank
        self.adjacent_blocks = adjacent_blocks


    def __str__(self):
        return f"Block {self.block_id} ({self.top_left}, {self.bottom_right}) - {self.factions} - Adjacent Blocks : {self.adjacent_blocks}"
    
