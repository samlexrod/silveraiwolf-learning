import strawberry
from typing import List
from app.models.inventory import Inventory
from app.models.product import Product

# Sample in-memory data
sample_inventory = [
    Inventory(product=Product(id=1, name="Widget", description="Basic widget"), quantity=100),
    Inventory(product=Product(id=2, name="Gadget", description="Advanced gadget"), quantity=200),
]

@strawberry.type
class Query:
    @strawberry.field
    def get_inventory(self) -> List[Inventory]:
        return sample_inventory
