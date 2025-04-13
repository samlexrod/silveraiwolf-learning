import strawberry
from typing import List
from app.models.supplier import Supplier
from app.models.product import Product

# Sample in-memory data
sample_suppliers = [
    Supplier(id=1, name="Acme Corp", products=[
        Product(id=1, name="Widget", description="Basic widget")
    ])
]

@strawberry.type
class Query:
    @strawberry.field
    def get_suppliers(self) -> List[Supplier]:
        return sample_suppliers
