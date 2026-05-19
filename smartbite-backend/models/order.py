from dataclasses import dataclass

@dataclass
class OrderItem:
    name: str
    price: float
    quantity: int

    @property
    def subtotal(self):
        return self.price * self.quantity