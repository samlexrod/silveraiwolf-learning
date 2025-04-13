import strawberry
from typing import List
from app.models.product import Product

# Sample in-memory data
sample_products = [
    Product(id=1, name="Widget", description="Basic widget"),
    Product(id=2, name="Gadget", description="Advanced gadget"),
]

@strawberry.type
class Query:
    @strawberry.field
    def get_products(self) -> List[Product]:
        return sample_products
