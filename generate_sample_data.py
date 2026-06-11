#!/usr/bin/env python3
import csv
import random
from datetime import datetime, timedelta

def generate_employees():
    departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations']
    first_names = ['John', 'Jane', 'Michael', 'Emily', 'David', 'Sarah', 'Chris', 'Jessica', 'Matthew', 'Amanda']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    rows = []
    for i in range(1, 1001):
        row = {
            'id': i,
            'first_name': random.choice(first_names),
            'last_name': random.choice(last_names),
            'email': f"{first_names[i % 10].lower()}.{last_names[i % 10].lower()}{i}@company.com",
            'department': random.choice(departments),
            'salary': random.randint(50000, 150000),
            'age': random.randint(22, 65),
            'hire_date': (datetime(2010, 1, 1) + timedelta(days=random.randint(0, 365*14))).strftime('%Y-%m-%d'),
            'is_active': random.choice(['True', 'False'])
        }
        rows.append(row)
    
    with open('employees.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated employees.csv with {len(rows)} rows")

def generate_products():
    categories = ['Electronics', 'Clothing', 'Home', 'Books', 'Food', 'Toys']
    brands = ['Apple', 'Samsung', 'Nike', 'Sony', 'LG', 'Amazon', 'Microsoft', 'Adidas']
    
    rows = []
    for i in range(1, 201):
        category = random.choice(categories)
        row = {
            'product_id': f'PRD{i:04d}',
            'name': f"{category.split()[0]} {random.choice(['Pro', 'Max', 'Lite', 'Ultra', 'Plus', 'Classic'])} {i}",
            'category': category,
            'brand': random.choice(brands),
            'price': round(random.uniform(9.99, 999.99), 2),
            'stock': random.randint(0, 500),
            'rating': round(random.uniform(1.0, 5.0), 1),
            'reviews': random.randint(0, 1000)
        }
        rows.append(row)
    
    with open('products.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated products.csv with {len(rows)} rows")

def generate_sales():
    products = []
    with open('products.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)
    
    employees = []
    with open('employees.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        employees = list(reader)
    
    rows = []
    start_date = datetime(2023, 1, 1)
    
    for i in range(1, 5001):
        product = random.choice(products)
        employee = random.choice(employees)
        quantity = random.randint(1, 10)
        unit_price = float(product['price'])
        discount = round(random.uniform(0, 0.3), 2)
        total = round(unit_price * quantity * (1 - discount), 2)
        
        row = {
            'sale_id': f'SALE{i:05d}',
            'product_id': product['product_id'],
            'product_name': product['name'],
            'category': product['category'],
            'employee_id': employee['id'],
            'employee_name': f"{employee['first_name']} {employee['last_name']}",
            'quantity': quantity,
            'unit_price': unit_price,
            'discount': discount,
            'total': total,
            'sale_date': (start_date + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
            'region': random.choice(['North', 'South', 'East', 'West'])
        }
        rows.append(row)
    
    with open('sales.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated sales.csv with {len(rows)} rows")

if __name__ == '__main__':
    generate_employees()
    generate_products()
    generate_sales()