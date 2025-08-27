# Supply Chain GraphQL API

A GraphQL API for managing supply chain data using Strawberry, FastAPI, and PostgreSQL.

## Tech Stack

- **Strawberry**: Python library for building GraphQL APIs
- **FastAPI**: Modern web framework for building APIs with Python
- **PostgreSQL**: Primary relational database for data storage
- **SQLAlchemy**: ORM for database operations

## Project Structure

```
strawberry/
├── README.md                # This file
├── TUTORIAL.md              # Complete learning tutorial
├── Dockerfile              # Docker image configuration
├── Makefile                # Convenient commands
├── docker-compose.dev.yml   # Development Docker Compose
├── env.example             # Development environment template
├── env.prod.example        # Production environment template
├── init_db.py             # Database initialization script
├── pyproject.toml         # Project configuration and dependencies
├── uv.lock               # Dependency lock file
├── tests/                # Test suite
│   ├── __init__.py
│   ├── test_app.py       # Quick test runner
│   └── test_api.py       # Comprehensive API tests
└── app/                  # Application code
    ├── __init__.py
    ├── main.py           # FastAPI application
    ├── config.py         # Configuration
    ├── schema.py         # GraphQL schema
    ├── models/           # Data models
    │   ├── __init__.py
    │   ├── product.py
    │   ├── supplier.py
    │   └── inventory.py
    ├── resolvers/        # GraphQL resolvers
    │   ├── __init__.py
    │   ├── product.py
    │   ├── suppliers.py
    │   ├── inventory.py
    │   └── status.py
    └── db/               # Database connections
        ├── __init__.py
        ├── postgres.py
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quick Start

### Local Development

1. **Complete setup**
   ```bash
   make setup
   ```

2. **Start the application**
   ```bash
   make dev
   ```

3. **Access the API**
   - GraphQL Playground: http://localhost:8000/graphql
   - Health Check: http://localhost:8000/
   - API Documentation: http://localhost:8000/docs

### Docker Development

1. **Start containerized environment**
   ```bash
   make docker-compose-dev
   ```

2. **View logs**
   ```bash
   make docker-compose-dev-logs
   ```

3. **Stop environment**
   ```bash
   make docker-compose-dev-down
   ```

## Environment Setup

### Development Environment

```bash
# Copy environment template
cp env.example .env

# Default development values
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=supplychain
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

### Production Environment

```bash
# Copy production template
cp env.prod.example .env

# Customize with secure values
POSTGRES_USER=strawberry_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=supplychain_prod
DEBUG=false
```

## GraphQL Playground

Access the interactive GraphQL Playground at http://localhost:8000/graphql

### Sample Queries

**Get all products:**
```graphql
query {
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

**Get suppliers with their products:**
```graphql
query {
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

**Get inventory with business logic:**
```graphql
query {
  getInventory {
    product {
      name
      isPremium
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

## API Endpoints

- **GraphQL Playground**: `http://localhost:8000/graphql`
- **GraphQL API**: `POST http://localhost:8000/graphql`
- **Health Check**: `GET http://localhost:8000/`
- **API Documentation**: `http://localhost:8000/docs`

## GraphQL Schema

### Types
- **Product**: Products with calculated fields (price formatting, premium status)
- **Supplier**: Suppliers with their associated products
- **Inventory**: Inventory levels with business logic (stock status, total values)

### Queries
- `getProducts`: Retrieve all products
- `getSuppliers`: Retrieve all suppliers with their products
- `getInventory`: Retrieve inventory levels for all products

### Calculated Fields

The API includes business logic through calculated fields:

**Product fields:**
- `priceFormatted`: Currency-formatted price (`$19.99`)
- `isPremium`: Boolean flag for products over $50
- `priceCategory`: Categorization (BUDGET, STANDARD, PREMIUM)

**Inventory fields:**
- `totalValue`: Quantity × product price
- `totalValueFormatted`: Currency-formatted total value
- `stockStatus`: Status enum (IN_STOCK, LOW_STOCK, OUT_OF_STOCK)
- `stockStatusDescription`: Human-readable status description
- `needsRestock`: Boolean flag for low inventory

## Testing

### Interactive Testing

Use GraphQL Playground for interactive testing:
1. Start the server: `make dev`
2. Open: http://localhost:8000/graphql
3. Use the "Docs" tab to explore the schema
4. Test queries in the main interface

### Automated Testing

```bash
# Run quick tests
make test

# Run full pytest suite
make test-pytest

# Run tests with database
make full-test
```

### Test Structure

- `tests/test_app.py`: Basic application tests
- `tests/test_api.py`: Comprehensive GraphQL API tests

## Database Management

### Initialize Database

```bash
# Start PostgreSQL
make start-postgres

# Initialize with sample data
make init-db
```

### Sample Data

The database includes realistic supply chain data:
- **Products**: Widget ($19.99), Gadget ($89.99), Tool ($45.50), Device ($199.99)
- **Suppliers**: Acme Corp, Tech Solutions Inc, Global Supplies Ltd
- **Inventory**: Various stock levels for testing business logic
- **Relationships**: Many-to-many supplier-product associations

### Database Commands

```bash
make start-postgres    # Start PostgreSQL container
make stop-postgres     # Stop PostgreSQL container
make init-db          # Initialize database with sample data
make logs             # Show PostgreSQL logs
make clean            # Clean up containers and cache
```

## Containerization

### Development Containers

The Docker setup includes:
- **PostgreSQL container**: Database with persistent volume
- **DB initialization container**: Runs once to populate sample data
- **Application container**: FastAPI + Strawberry GraphQL API

### Container Features

- **Automatic database population**: Sample data created on startup
- **Health checks**: Ensures services are ready before starting dependencies
- **Persistent data**: PostgreSQL data survives container restarts
- **Hot reload**: Application reloads on code changes (development mode)

### Docker Commands

```bash
# Development environment
make docker-compose-dev        # Start all services
make docker-compose-dev-down   # Stop all services
make docker-compose-dev-logs   # View service logs
make docker-compose-dev-clean  # Remove containers and volumes

# Individual containers
make docker-build             # Build application image
make docker-run              # Run application container
make docker-test             # Test container functionality
```

### Container Architecture

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

## Available Commands

### Development Commands
```bash
make help           # Show all available commands
make setup          # Complete project setup
make setup-dev      # Setup with development dependencies
make install        # Install Python dependencies
make install-dev    # Install development dependencies
make dev            # Start development server
```

### Testing Commands
```bash
make test           # Run test suite
make test-pytest    # Run tests with pytest
make full-test      # Run complete test suite with database
```

### Database Commands
```bash
make init-db        # Initialize database with sample data
make start-postgres # Start PostgreSQL
make stop-postgres  # Stop PostgreSQL
make logs           # Show PostgreSQL logs
make clean          # Clean up containers and cache
```

### Docker Commands
```bash
make docker-build                # Build the Docker image
make docker-run                 # Run application in Docker
make docker-compose-dev         # Start development environment
make docker-compose-dev-down    # Stop development environment
make docker-compose-dev-logs    # View development logs
make docker-compose-dev-clean   # Clean up environment and volumes
make docker-test               # Test the Docker container
```

### Dependency Management
```bash
make add-dep PKG=package-name     # Add a new dependency
make add-dev-dep PKG=package-name # Add a development dependency
```

## Architecture

### Request Flow

```
Client Request → FastAPI → Strawberry GraphQL → Resolvers → SQLAlchemy → PostgreSQL
                     ↓
GraphQL Response ← JSON Formatting ← Type Conversion ← Database Results
```

### Key Components

- **FastAPI**: HTTP server and routing
- **Strawberry**: GraphQL schema and query processing
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Data persistence
- **Docker**: Containerization and deployment

## Performance Features

- **Async/await**: Non-blocking database operations
- **Eager loading**: Prevents N+1 query problems
- **Connection pooling**: Efficient database connections
- **Type safety**: Compile-time error checking
- **Health checks**: Monitoring and reliability

## Development Workflow

1. **Start development environment**: `make setup && make dev`
2. **Test API**: Use GraphQL Playground at http://localhost:8000/graphql
3. **Run tests**: `make test` for quick feedback
4. **Make changes**: Code hot-reloads automatically
5. **Test in containers**: `make docker-compose-dev` for production-like testing

## Troubleshooting

### Common Issues

**Database connection errors:**
- Ensure PostgreSQL is running: `make start-postgres`
- Check environment variables in `.env`
- Verify database is initialized: `make init-db`

**Container issues:**
- Check container status: `docker ps`
- View logs: `make docker-compose-dev-logs`
- Clean and restart: `make docker-compose-dev-clean && make docker-compose-dev`

**Import errors:**
- Ensure dependencies are installed: `make install`
- Check Python version: `python --version` (should be 3.11+)

### Useful Debug Commands

```bash
# Check database tables
docker compose exec postgres psql -U user -d supplychain -c "\dt"

# View container logs
docker logs strawberry-graphql-app
docker logs strawberry-postgres-dev

# Test database connection
make start-postgres
sleep 3
make init-db
```

## Learning Resources

For a complete tutorial on building this API from scratch, see [TUTORIAL.md](./TUTORIAL.md).

## Next Steps

- **Add mutations**: Implement create/update/delete operations
- **Add authentication**: Secure your API endpoints  
- **Add subscriptions**: Real-time updates
- **Deploy to cloud**: AWS, Google Cloud, or Azure deployment
- **Add caching**: Redis for improved performance
- **Add monitoring**: Logging, metrics, and alerting