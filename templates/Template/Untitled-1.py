class Customer:
    """
    Represents a customer with an ID and a name.
    """
    def __init__(self):
        self.ID = None
        self.Name = None

    def __str__(self):
        """
        Returns the name of the customer as a string.
        """
        return self.Name

def main():
    """
    The main entry point of the program.
    """
    array = [None, None, None]
    array[0] = 101
    array[1] = "C#"
    c = Customer()
    c.ID = 55
    c.Name = "Manish"
    array[2] = c

    for obj in array:
        print(obj)

    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
