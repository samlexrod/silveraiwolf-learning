-- Sample data script for testing CDC replication
-- This script creates tables and performs operations that will trigger CDC events

-- Create a sample customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(20),
    zip_code VARCHAR(10),
    country VARCHAR(50) DEFAULT 'USA',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a sample orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a sample order_items table
CREATE TABLE IF NOT EXISTS order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for the updated_at column
CREATE TRIGGER update_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_order_items_updated_at
BEFORE UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Insert sample customers (INSERT operations)
INSERT INTO customers (first_name, last_name, email, phone, address, city, state, zip_code)
VALUES 
    ('John', 'Doe', 'john.doe@example.com', '555-123-4567', '123 Main St', 'New York', 'NY', '10001'),
    ('Jane', 'Smith', 'jane.smith@example.com', '555-987-6543', '456 Oak Ave', 'Los Angeles', 'CA', '90001'),
    ('Robert', 'Johnson', 'robert.johnson@example.com', '555-555-5555', '789 Pine Rd', 'Chicago', 'IL', '60601'),
    ('Emily', 'Williams', 'emily.williams@example.com', '555-222-3333', '321 Elm St', 'Houston', 'TX', '77001'),
    ('Michael', 'Brown', 'michael.brown@example.com', '555-444-5555', '654 Maple Dr', 'Phoenix', 'AZ', '85001');

-- Insert sample orders (INSERT operations)
INSERT INTO orders (customer_id, total_amount, status, shipping_address)
VALUES 
    (1, 150.00, 'completed', '123 Main St, New York, NY 10001'),
    (2, 275.50, 'pending', '456 Oak Ave, Los Angeles, CA 90001'),
    (3, 75.25, 'shipped', '789 Pine Rd, Chicago, IL 60601'),
    (4, 200.00, 'processing', '321 Elm St, Houston, TX 77001'),
    (5, 125.75, 'cancelled', '654 Maple Dr, Phoenix, AZ 85001');

-- Insert sample order items (INSERT operations)
INSERT INTO order_items (order_id, product_name, quantity, unit_price)
VALUES 
    (1, 'Laptop', 1, 150.00),
    (2, 'Smartphone', 1, 275.50),
    (3, 'Headphones', 1, 75.25),
    (4, 'Tablet', 1, 200.00),
    (5, 'Smartwatch', 1, 125.75);

-- Update operations (will trigger CDC events)
UPDATE customers 
SET phone = '555-111-2222', updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1;

UPDATE orders 
SET status = 'shipped', updated_at = CURRENT_TIMESTAMP
WHERE order_id = 2;

UPDATE order_items 
SET quantity = 2, updated_at = CURRENT_TIMESTAMP
WHERE item_id = 3;

-- Delete operations (will trigger CDC events)
DELETE FROM order_items WHERE item_id = 5;
DELETE FROM orders WHERE order_id = 5;
DELETE FROM customers WHERE customer_id = 5;

-- Insert more data after deletions (to test mixed operations)
INSERT INTO customers (first_name, last_name, email, phone, address, city, state, zip_code)
VALUES 
    ('Sarah', 'Davis', 'sarah.davis@example.com', '555-777-8888', '987 Cedar Ln', 'Miami', 'FL', '33101');

INSERT INTO orders (customer_id, total_amount, status, shipping_address)
VALUES 
    (6, 350.00, 'pending', '987 Cedar Ln, Miami, FL 33101');

INSERT INTO order_items (order_id, product_name, quantity, unit_price)
VALUES 
    (6, 'Gaming Console', 1, 350.00);

-- Update the newly inserted customer
UPDATE customers 
SET phone = '555-999-0000', updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 6;

-- Final update to an order
UPDATE orders 
SET status = 'completed', updated_at = CURRENT_TIMESTAMP
WHERE order_id = 6;

-- This script demonstrates:
-- 1. Table creation with appropriate data types and constraints
-- 2. Trigger creation for automatic timestamp updates
-- 3. INSERT operations (creates new records)
-- 4. UPDATE operations (modifies existing records)
-- 5. DELETE operations (removes records)
-- 6. Mixed operations to simulate real-world scenarios 