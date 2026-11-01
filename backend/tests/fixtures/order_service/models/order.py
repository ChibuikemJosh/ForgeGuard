class Order:
    def __init__(self, id: str, owner_id: str, total: int):
        self.id = id
        self.owner_id = owner_id
        self.total = total
