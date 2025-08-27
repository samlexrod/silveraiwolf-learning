import strawberry
from typing import List
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.inventory import Inventory
from app.resolvers.product import Query as ProductQuery
from app.resolvers.suppliers import Query as SupplierQuery
from app.resolvers.inventory import Query as InventoryQuery

@strawberry.type
class Query(ProductQuery, SupplierQuery, InventoryQuery):
    """Combined GraphQL Query type that includes all resolvers."""
    pass

# Create the schema
schema = strawberry.Schema(query=Query)
