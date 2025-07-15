class HotelManagement:
    def __init__(self):
        self.orders = []  # Orders placed
        self.received = []  # Orders received by kitchen
        self.delivered = []  # Orders delivered to customer

    def place_order(self, order):
        print(f"Placing order: {order}")
        self.orders.append(order)

    def receive_order(self):
        if len(self.orders) == 0:
            print("No orders to receive.")
            return

        order = self.orders.pop()
        print(f"Receiving order: {order}")
        # FIX: Added the missing line to append order to received list
        self.received.append(order)

    def deliver_order(self):
        if len(self.received) == 0:
            print("No orders to deliver.")
            return

        order = self.received.pop()
        print(f"Delivering order: {order}")
        self.delivered.append(order)

    def status(self):
        print(f"Orders: {self.orders}")
        print(f"Received: {self.received}")
        print(f"Delivered: {self.delivered}")


# --- Example usage ---
if __name__ == "__main__":
    hm = HotelManagement()

    hm.place_order("Pasta")
    hm.receive_order()
    hm.deliver_order()

    hm.status()