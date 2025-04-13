products_data = [
    Product(id=1, name="Widget", description="Basic Widget"),
    Product(id=2, name="Gadget", description="Advanced Gadget"),
]

suppliers_data = [
    Supplier(id=1, name="Acme Corp", products=products_data),
]

inventory_data = [
    Inventory(product=products_data[0], quantity=100),
    Inventory(product=products_data[1], quantity=200),
]

@strawberry.type
class Query:
    @strawberry.field
    def get_products(self) -> List[Product]:
        return products_data

    @strawberry.field
    def get_suppliers(self) -> List[Supplier]:
        return suppliers_data

    @strawberry.field
    def get_inventory(self) -> List[Inventory]:
        return inventory_data
