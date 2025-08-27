# Building a GraphQL API with Strawberry, FastAPI, and PostgreSQL

## Tutorial Overview

In this tutorial, you'll learn how to build a complete GraphQL API for a supply chain management system. By the end, you'll understand:

- **What GraphQL is** and why it's powerful for APIs
- **How Strawberry** makes GraphQL development elegant in Python
- **Building relationships** between data models
- **Implementing resolvers** that fetch and transform data
- **Using calculated fields** for business logic
- **Containerizing** your application for deployment
- **Testing** your GraphQL API effectively

## What You'll Build

We're building a **Supply Chain Management API** that tracks:
- **Products** (widgets, gadgets, tools, devices)
- **Suppliers** (companies that provide products)
- **Inventory** (stock levels and values)
- **Relationships** (which suppliers provide which products)

This real-world scenario demonstrates complex data relationships and business logic that you'll encounter in production applications.

## Learning Objectives

By completing this tutorial, you will:

1. **Understand GraphQL fundamentals** and how it differs from REST
2. **Master Strawberry GraphQL** for building Python APIs
3. **Design database schemas** with complex relationships
4. **Implement business logic** using calculated fields
5. **Deploy with Docker** for consistent environments
6. **Write effective tests** for GraphQL APIs
7. **Handle real-world scenarios** like data validation and error handling

## Why GraphQL?

### The Problem with Traditional REST APIs

Imagine you're building a mobile app for supply chain managers. With REST, you might need:

```bash
GET /products          # Get all products
GET /products/1/suppliers  # Get suppliers for product 1
GET /suppliers/1       # Get details for supplier 1
GET /inventory?product=1   # Get inventory for product 1
```

**Problems:**
- **Multiple requests** = slower mobile experience
- **Over-fetching** = wasted bandwidth (you get all fields, even ones you don't need)
- **Under-fetching** = need additional requests for related data

### The GraphQL Solution

With GraphQL, you make **one request** and get **exactly** what you need:

```graphql
query {
  getProducts {
    id
    name
    price                    # Only the fields you need
    suppliers {              # Related data in one request
      name
    }
    inventory {
      quantity
      totalValue            # Calculated fields
    }
  }
}
```

**Benefits:**
- **Single request** = faster performance
- **Exact data** = no over/under-fetching
- **Type safety** = fewer bugs
- **Self-documenting** = built-in schema exploration

## Why Strawberry?

Strawberry is a modern Python GraphQL library that feels natural to Python developers:

```python
@strawberry.type
class Product:
    id: int
    name: str
    price: float
    
    @strawberry.field
    def price_formatted(self) -> str:
        return f"${self.price:.2f}"
```

**Advantages:**
- **Type hints** = leverages Python's type system
- **Decorators** = clean, readable code
- **FastAPI integration** = modern async Python
- **Automatic schema generation** = less boilerplate

## Prerequisites

Before starting, you should have:
- **Basic Python knowledge** (functions, classes, async/await)
- **SQL understanding** (tables, relationships, foreign keys)
- **Docker basics** (containers, volumes)
- **Terminal/command line** comfort

**Required Software:**
- Python 3.11+
- Docker and Docker Compose
- A code editor (VS Code recommended)

## Tutorial Structure

This tutorial is organized into progressive steps:

1. **[Getting Started](#getting-started)** - Set up your development environment
2. **[Understanding the Architecture](#understanding-the-architecture)** - Learn how the pieces fit together
3. **[Database Design](#database-design)** - Design your data models and relationships
4. **[Building GraphQL Types](#building-graphql-types)** - Create your GraphQL schema
5. **[Implementing Resolvers](#implementing-resolvers)** - Fetch data from the database
6. **[Calculated Fields](#calculated-fields)** - Add business logic without database changes
7. **[Testing Your API](#testing-your-api)** - Write comprehensive tests
8. **[Containerization](#containerization)** - Package for deployment
9. **[Advanced Topics](#advanced-topics)** - Performance, security, and production concerns

---

## Getting Started

### Step 1: Set Up Your Development Environment

First, let's get your development environment ready:

```bash
# Navigate to the project directory
cd strawberry/

# Install dependencies
make setup
```

**What just happened?**
- `make setup` installed Python dependencies with `uv`
- Started PostgreSQL in a Docker container
- Created database tables and relationships
- Populated sample data for testing

### Step 2: Start the Development Server

```bash
make dev
```

Open http://localhost:8000/graphql in your browser. You should see **GraphQL Playground** - an interactive tool for exploring and testing your API.

### Step 3: Your First GraphQL Query

In GraphQL Playground, try this query:

```graphql
query {
  getProducts {
    id
    name
    description
  }
}
```

**Understanding the Response:**
```json
{
  "data": {
    "getProducts": [
      {
        "id": 1,
        "name": "Widget",
        "description": "Basic widget for everyday use"
      }
    ]
  }
}
```

**Key Concepts:**
- **Query**: You specify exactly what data you want
- **Fields**: Only requested fields are returned
- **Structure**: Response mirrors your query structure

---

## Understanding the Architecture

Let's understand how our GraphQL API is structured:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GraphQL       │    │   Strawberry    │    │   PostgreSQL    │
│   Playground    │───▶│   Resolvers     │───▶│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
     Frontend              Backend Logic         Data Storage
```

### The Flow

1. **Client** sends GraphQL query
2. **Strawberry** parses query and calls appropriate resolvers
3. **Resolvers** fetch data from PostgreSQL using SQLAlchemy
4. **Strawberry** formats response according to schema
5. **Client** receives exactly the requested data

### Key Components

**FastAPI** (`app/main.py`):
```python
app = FastAPI(title="Supply Chain GraphQL API")
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```
- Serves as the web framework
- Handles HTTP requests and routing
- Integrates with Strawberry GraphQL

**Strawberry Schema** (`app/schema.py`):
```python
@strawberry.type
class Query:
    get_products: List[Product] = strawberry.field(resolver=get_products)
    get_suppliers: List[Supplier] = strawberry.field(resolver=get_suppliers)
```
- Defines what queries are available
- Links to resolver functions
- Provides type safety

**SQLAlchemy Models** (`app/models/`):
```python
class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
```
- Maps to database tables
- Handles relationships between entities
- Provides async database operations

---

## Database Design

### Understanding Relationships

Our supply chain has three main entities with specific relationships:

```sql
┌─────────────┐     ┌─────────────────────┐     ┌─────────────┐
│  suppliers  │────▶│  supplier_products  │◀────│  products   │
│             │     │                     │     │             │
│ id          │     │ supplier_id         │     │ id          │
│ name        │     │ product_id          │     │ name        │
└─────────────┘     └─────────────────────┘     │ description │
                                                │ price       │
                                                └─────────────┘
                                                      │
                                                      ▼
                                                ┌─────────────┐
                                                │  inventory  │
                                                │             │
                                                │ id          │
                                                │ product_id  │
                                                │ quantity    │
                                                └─────────────┘
```

### Relationship Types

**Many-to-Many (Suppliers ↔ Products)**:
- One supplier can provide multiple products
- One product can be provided by multiple suppliers
- Uses `supplier_products` association table

**One-to-One (Products → Inventory)**:
- Each product has one inventory record
- Each inventory record belongs to one product
- Uses foreign key `inventory.product_id`

### Why These Relationships?

**Real-world scenarios:**
- **Apple** supplies both **iPhones** and **iPads** (one supplier, many products)
- **iPhone screens** come from both **Samsung** and **LG** (one product, many suppliers)
- Each **iPhone model** has its own **inventory count** (one-to-one)

### Database Initialization

Look at `init_db.py` to see how we create sample data:

```python
# Create products
product1 = ProductModel(name="Widget", description="Basic widget", price=19.99)
product2 = ProductModel(name="Gadget", description="Advanced gadget", price=89.99)

# Create suppliers  
supplier1 = SupplierModel(name="Acme Corp")
supplier2 = SupplierModel(name="Tech Solutions Inc")

# Create many-to-many relationships
await session.execute(
    supplier_products.insert().values([
        {"supplier_id": supplier1.id, "product_id": product1.id},
        {"supplier_id": supplier1.id, "product_id": product2.id},
        {"supplier_id": supplier2.id, "product_id": product2.id},
    ])
)

# Create inventory (one-to-one)
inventory1 = InventoryModel(product_id=product1.id, quantity=100)
```

---

## Building GraphQL Types

### Strawberry Types vs Database Models

We need **two representations** of our data:

1. **Database Models** (SQLAlchemy) - for database operations
2. **GraphQL Types** (Strawberry) - for API responses

**Why separate them?**
- **Database models** handle persistence, relationships, constraints
- **GraphQL types** handle API shape, calculated fields, presentation logic
- **Separation** allows independent evolution of database and API

### Creating GraphQL Types

**Product Type** (`app/models/product.py`):
```python
@strawberry.type
class Product:
    id: int
    name: str
    description: str
    price: float
    
    @strawberry.field
    def price_formatted(self) -> str:
        """Format price as currency"""
        return f"${self.price:.2f}"
    
    @strawberry.field
    def is_premium(self) -> bool:
        """Determine if product is premium (> $50)"""
        return self.price > 50.0
```

**Key Concepts:**

**Basic Fields**: `id`, `name`, `description`, `price`
- Map directly to database columns
- Strawberry handles type conversion automatically

**Calculated Fields**: `price_formatted`, `is_premium`  
- Computed on-the-fly from existing data
- No database changes required
- Perfect for business logic

### Advanced Types with Relationships

**Supplier Type** (`app/models/supplier.py`):
```python
@strawberry.type
class Supplier:
    id: int
    name: str
    products: List[Product]  # One-to-many relationship
```

**Inventory Type** (`app/models/inventory.py`):
```python
@strawberry.type
class Inventory:
    product: Product  # One-to-one relationship
    quantity: int
    
    @strawberry.field
    def total_value(self) -> float:
        """Calculate total inventory value"""
        return self.quantity * self.product.price
    
    @strawberry.field
    def stock_status(self) -> str:
        """Determine stock status"""
        if self.quantity == 0:
            return "OUT_OF_STOCK"
        elif self.quantity <= 10:
            return "LOW_STOCK"
        else:
            return "IN_STOCK"
```

### Type Safety Benefits

With Strawberry's type hints, you get:
- **IDE autocomplete** for field names
- **Compile-time checking** for type mismatches  
- **Automatic schema generation** from Python types
- **Runtime validation** of query responses

---

## Implementing Resolvers

Resolvers are functions that fetch data for GraphQL fields. Think of them as the "controllers" in MVC architecture.

### Basic Resolver Pattern

**Product Resolver** (`app/resolvers/product.py`):
```python
@strawberry.field
async def get_products() -> List[Product]:
    async with get_pg_session() as session:
        # Query database using SQLAlchemy
        stmt = select(ProductModel).order_by(ProductModel.id)
        result = await session.execute(stmt)
        products = result.scalars().all()
        
        # Convert database models to GraphQL types
        return [
            Product(
                id=p.id,
                name=p.name,
                description=p.description,
                price=p.price
            ) for p in products
        ]
```

**What's happening here?**
1. **Open database session** with `get_pg_session()`
2. **Build SQLAlchemy query** with `select(ProductModel)`
3. **Execute query** and get results
4. **Transform data** from database models to GraphQL types
5. **Return list** of GraphQL Product objects

### Handling Relationships

**Supplier Resolver with Products** (`app/resolvers/suppliers.py`):
```python
@strawberry.field
async def get_suppliers() -> List[Supplier]:
    async with get_pg_session() as session:
        # Use eager loading to prevent N+1 queries
        stmt = (
            select(SupplierModel)
            .options(selectinload(SupplierModel.products))
            .order_by(SupplierModel.id)
        )
        result = await session.execute(stmt)
        suppliers = result.scalars().all()
        
        # Build response with related products
        supplier_list = []
        for supplier in suppliers:
            # Convert related products
            supplier_products = [
                Product(id=p.id, name=p.name, description=p.description, price=p.price)
                for p in supplier.products
            ]
            # Create supplier with products
            supplier_list.append(
                Supplier(id=supplier.id, name=supplier.name, products=supplier_products)
            )
        
        return supplier_list
```

**Performance Optimization:**
- `selectinload(SupplierModel.products)` loads all related products in one query
- **Prevents N+1 problem** (1 query for suppliers + N queries for each supplier's products)
- **Single database roundtrip** = better performance

### Complex Resolver with Multiple Relationships

**Inventory Resolver** (`app/resolvers/inventory.py`):
```python
@strawberry.field
async def get_inventory() -> List[Inventory]:
    async with get_pg_session() as session:
        stmt = (
            select(InventoryModel)
            .options(selectinload(InventoryModel.product))
            .order_by(InventoryModel.product_id)
        )
        result = await session.execute(stmt)
        inventory_items = result.scalars().all()
        
        return [
            Inventory(
                product=Product(
                    id=item.product.id,
                    name=item.product.name,
                    description=item.product.description,
                    price=item.product.price
                ),
                quantity=item.quantity
            ) for item in inventory_items
        ]
```

### Resolver Best Practices

**1. Always use async/await:**
```python
async def get_products() -> List[Product]:  # ✅ Async
    async with get_pg_session() as session:  # ✅ Async context manager
        result = await session.execute(stmt)  # ✅ Await database call
```

**2. Use eager loading for relationships:**
```python
# ❌ N+1 queries (slow)
stmt = select(SupplierModel)

# ✅ Single query (fast)  
stmt = select(SupplierModel).options(selectinload(SupplierModel.products))
```

**3. Transform data consistently:**
```python
# Convert database model to GraphQL type
return [
    Product(id=p.id, name=p.name, description=p.description, price=p.price)
    for p in database_products
]
```

---

## Calculated Fields

Calculated fields are one of GraphQL's most powerful features. They let you add business logic and data transformations **without changing your database**.

### Why Calculated Fields?

**Business Scenario**: Your product manager wants to:
- Show formatted prices (`$19.99` instead of `19.99`)
- Identify premium products (price > $50)
- Calculate inventory values
- Determine stock status

**Traditional approach**: Add columns to database, migrate data, update all queries

**GraphQL approach**: Add calculated fields that compute values on demand

### Product Calculated Fields

```python
@strawberry.type
class Product:
    id: int
    name: str
    description: str
    price: float
    
    @strawberry.field
    def price_formatted(self) -> str:
        """Format price with currency symbol"""
        return f"${self.price:.2f}"
    
    @strawberry.field
    def is_premium(self) -> bool:
        """Determine if product is premium"""
        return self.price > 50.0
    
    @strawberry.field
    def price_category(self) -> str:
        """Categorize product by price"""
        if self.price < 25:
            return "BUDGET"
        elif self.price < 75:
            return "STANDARD"  
        else:
            return "PREMIUM"
```

**Usage in queries:**
```graphql
query {
  getProducts {
    name
    price              # 19.99
    priceFormatted     # "$19.99"
    isPremium          # false
    priceCategory      # "BUDGET"
  }
}
```

### Inventory Calculated Fields

```python
@strawberry.type  
class Inventory:
    product: Product
    quantity: int
    
    @strawberry.field
    def total_value(self) -> float:
        """Calculate total inventory value"""
        return self.quantity * self.product.price
    
    @strawberry.field
    def total_value_formatted(self) -> str:
        """Format total value as currency"""
        value = self.quantity * self.product.price
        return f"${value:.2f}"
    
    @strawberry.field
    def stock_status(self) -> str:
        """Determine stock status"""
        if self.quantity == 0:
            return "OUT_OF_STOCK"
        elif self.quantity <= 10:
            return "LOW_STOCK"
        else:
            return "IN_STOCK"
    
    @strawberry.field
    def stock_status_description(self) -> str:
        """Human-readable stock description"""
        if self.quantity == 0:
            return "Out of stock - reorder immediately"
        elif self.quantity <= 10:
            return f"Low stock - {self.quantity} units remaining"
        else:
            return f"{self.quantity} units in stock"
    
    @strawberry.field
    def needs_restock(self) -> bool:
        """Determine if product needs restocking"""
        return self.quantity <= 10
```

### Advanced Calculated Fields

**Business Intelligence Query:**
```graphql
query InventoryAnalysis {
  getInventory {
    product {
      name
      isPremium
    }
    quantity
    totalValue
    stockStatus
    needsRestock
  }
}
```

**Response with business insights:**
```json
{
  "data": {
    "getInventory": [
      {
        "product": {
          "name": "Device",
          "isPremium": true
        },
        "quantity": 25,
        "totalValue": 4999.75,
        "stockStatus": "IN_STOCK", 
        "needsRestock": false
      }
    ]
  }
}
```

### When to Use Calculated Fields

**✅ Great for:**
- **Formatting**: Currency, dates, phone numbers
- **Business logic**: Status calculations, categorization
- **Simple math**: Totals, percentages, ratios
- **String manipulation**: Full names, formatted addresses
- **Boolean flags**: Eligibility checks, status flags

**❌ Avoid for:**
- **Heavy computations**: Use background jobs instead
- **External API calls**: Use separate resolvers with caching
- **Database aggregations**: Use database queries for better performance

---

## Testing Your API

### Interactive Testing with GraphQL Playground

GraphQL Playground is your primary testing tool during development:

1. **Start your server**: `make dev`
2. **Open Playground**: http://localhost:8000/graphql
3. **Explore the schema**: Use the "Docs" tab to see all available types and fields

### Essential Test Queries

**Test 1: Basic Product Query**
```graphql
query TestProducts {
  getProducts {
    id
    name
    description
    price
    priceFormatted
    isPremium
  }
}
```

**Test 2: Supplier Relationships**  
```graphql
query TestSupplierRelationships {
  getSuppliers {
    id
    name
    products {
      id
      name
      price
    }
  }
}
```

**Test 3: Complex Business Logic**
```graphql
query TestBusinessLogic {
  getInventory {
    product {
      name
      isPremium
      priceCategory
    }
    quantity
    totalValue
    totalValueFormatted
    stockStatus
    stockStatusDescription
    needsRestock
  }
}
```

**Test 4: Selective Field Requests**
```graphql
query TestSelectiveFields {
  getProducts {
    name        # Only request what you need
    isPremium   # Test calculated fields
  }
}
```

### Automated Testing

**Run the test suite:**
```bash
make test           # Quick tests
make test-pytest    # Full pytest suite  
```

**Example test** (`tests/test_api.py`):
```python
def test_get_products():
    """Test products query returns expected data"""
    query = """
    query {
        getProducts {
            id
            name
            price
            isPremium
        }
    }
    """
    
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200
    
    data = response.json()["data"]["getProducts"]
    assert len(data) > 0
    
    # Test calculated fields
    widget = next(p for p in data if p["name"] == "Widget")
    assert widget["isPremium"] == False  # $19.99 < $50
    
    device = next(p for p in data if p["name"] == "Device") 
    assert device["isPremium"] == True   # $199.99 > $50
```

### Testing Strategies

**1. Schema Testing**: Verify your GraphQL schema is valid
**2. Resolver Testing**: Test individual resolver functions  
**3. Integration Testing**: Test full query execution
**4. Business Logic Testing**: Verify calculated fields work correctly
**5. Error Handling Testing**: Test invalid queries and edge cases

---

## Containerization

### Why Containerize?

**Development Benefits:**
- **Consistent environment** across team members
- **No local PostgreSQL installation** required
- **Easy setup** for new developers
- **Matches production environment**

**Production Benefits:**  
- **Reliable deployments** across different servers
- **Scalable architecture** with container orchestration
- **Environment isolation** prevents conflicts
- **Easy rollbacks** to previous versions

### Docker Development Setup

**Start containerized development:**
```bash
make docker-compose-dev
```

**What happens:**
1. **PostgreSQL container** starts with persistent data volume
2. **Database initialization** runs once to create tables and sample data
3. **Application container** starts after database is ready
4. **Health checks** ensure everything is running correctly

**View logs:**
```bash
make docker-compose-dev-logs
```

**Clean up:**
```bash
make docker-compose-dev-clean  # Removes containers and data
```

### Docker Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   DB Init       │    │   PostgreSQL    │
│   Container     │    │   Container     │    │   Container     │
│                 │    │                 │    │                 │
│ FastAPI         │    │ Runs once       │    │ Persistent      │
│ Strawberry      │◀───│ Creates tables  │───▶│ Data Volume     │
│ GraphQL API     │    │ Populates data  │    │ Port 5432       │
│ Port 8000       │    │ Exits           │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Container Configuration

**Dockerfile highlights:**
```dockerfile
# Multi-stage build for efficiency
FROM python:3.11-slim AS base

# Install uv for fast dependency management  
RUN pip install uv

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Non-root user for security
RUN useradd app && chown -R app:app /app
USER app

# Health check for container orchestration
HEALTHCHECK CMD curl -f http://localhost:8000/ || exit 1
```

**Docker Compose configuration** (`docker-compose.dev.yml`):
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pass}
      POSTGRES_DB: ${POSTGRES_DB:-supplychain}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d supplychain"]

  db-init:
    build: .
    command: ["uv", "run", "python", "init_db.py"]
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"  # Run once and exit

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      db-init:
        condition: service_completed_successfully
```

---

## Advanced Topics

### Performance Optimization

**N+1 Query Problem:**
```python
# ❌ This creates N+1 queries
suppliers = session.execute(select(SupplierModel)).scalars().all()
for supplier in suppliers:
    products = supplier.products  # Separate query for each supplier

# ✅ This creates 1 query  
suppliers = session.execute(
    select(SupplierModel)
    .options(selectinload(SupplierModel.products))
).scalars().all()
```

**DataLoader Pattern** (for complex scenarios):
```python
# Use DataLoader for batching and caching
@strawberry.field
async def products(self, info) -> List[Product]:
    loader = info.context["product_loader"]  
    return await loader.load(self.id)
```

### Error Handling

**Custom exceptions:**
```python
@strawberry.type
class ProductNotFoundError:
    message: str = "Product not found"

@strawberry.field
async def get_product(id: int) -> Union[Product, ProductNotFoundError]:
    product = await find_product_by_id(id)
    if not product:
        return ProductNotFoundError()
    return product
```

### Authentication and Authorization

**Add authentication middleware:**
```python
@strawberry.field
async def get_private_data(info) -> str:
    user = info.context["user"]
    if not user.is_authenticated:
        raise Exception("Authentication required")
    return "Secret data"
```

### Production Deployment

**Environment variables for production:**
```bash
# Security
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=api.yourcompany.com

# Database (use managed PostgreSQL in production)
DATABASE_URL=postgresql://user:pass@prod-db.amazonaws.com/supplychain

# Performance  
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Monitoring
SENTRY_DSN=https://your-sentry-dsn.com
```

**Production checklist:**
- [ ] Use managed database (AWS RDS, Google Cloud SQL)
- [ ] Set up SSL/TLS certificates
- [ ] Configure proper logging and monitoring
- [ ] Set up health checks and metrics
- [ ] Use environment-specific configuration
- [ ] Set up CI/CD pipeline
- [ ] Configure auto-scaling

---

## Conclusion

Congratulations! You've built a complete GraphQL API with:

✅ **Modern Python stack** (FastAPI, Strawberry, SQLAlchemy)  
✅ **Complex data relationships** (one-to-one, many-to-many)
✅ **Business logic** through calculated fields
✅ **Container deployment** with Docker
✅ **Comprehensive testing** strategies
✅ **Production considerations** for scaling

### What You've Learned

**GraphQL Concepts:**
- Query structure and field selection
- Type system and schema design
- Resolvers and data fetching
- Calculated fields for business logic

**Python Development:**
- Modern async Python with FastAPI
- SQLAlchemy ORM with relationships
- Type hints for better code quality
- Container-based development

**Production Skills:**
- Docker containerization
- Database design and relationships
- API testing strategies
- Performance optimization techniques

### Next Steps

**Extend this tutorial:**
- Add **mutations** for creating/updating data
- Implement **authentication** and user management
- Add **subscriptions** for real-time updates
- Create a **React frontend** to consume your API

**Production deployment:**
- Set up **AWS/Google Cloud** deployment
- Add **monitoring** with Prometheus/Grafana
- Implement **caching** with Redis
- Set up **CI/CD** pipeline

**Advanced features:**
- **File uploads** for product images
- **Batch operations** for bulk updates  
- **Rate limiting** and security
- **API versioning** strategies

### Resources

- [Strawberry Documentation](https://strawberry.rocks/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async Tutorial](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)

---

*This tutorial was designed to give you hands-on experience with modern GraphQL development in Python. The concepts you've learned here apply to any GraphQL implementation, making you a more versatile API developer.*