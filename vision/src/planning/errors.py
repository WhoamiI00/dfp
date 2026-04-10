"""Planning-related errors."""


class NoPathError(Exception):
    pass


class ApproachPointBlockedError(Exception):
    def __init__(self, shelf_id: str):
        super().__init__(f"Approach point blocked by inflated obstacle: shelf_id={shelf_id}")
        self.shelf_id = shelf_id
