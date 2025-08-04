class BaseEnv:
    def __init__(self):
        pass
    
    def shoot(self, target: str):
        raise NotImplementedError("This method should be implemented in subclasses.")

    def use(self, items: list[int], item_name: str):
        """如果用的是肾上腺素，item_name 是偷的道具的名称"""
        raise NotImplementedError("This method should be implemented in subclasses.")