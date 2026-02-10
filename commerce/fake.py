import os
import sys
import random
from faker import Faker
from faker.providers import BaseProvider
import faker_commerce

# Get the current directory and parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add both current and parent directories to the path
sys.path.append(parent_dir)
sys.path.append(current_dir)

# Get the current directory and parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level from snippets folder

# Add the project root to sys.path
sys.path.insert(0, project_root)

# 1. SET THE SETTINGS MODULE (Crucial)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_project_nexus.settings')

# 2. INITIALIZE DJANGO
import django
django.setup()

# Now import Django models AFTER setup
from commerce.models import User, Product, Order, OrderItem, Payment

fake = Faker("en_NG")
# add commerce provider to faker
fake.add_provider(faker_commerce.Provider)

def seed_fake_users(records):

    
    
    for i in range(records):
        try:
            username = fake.user_name()
            email = fake.email()

            # check if user exists
            if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                continue
            user = User.objects.create_user(
                username=fake.user_name(),
                email=fake.email(),
                password="password",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=random.choice(['customer', 'admin'])
            )
            user.save()
        except Exception as e:
            print(f"err creating user {e}")
            continue
            
    print(f"{records} realistic entries generated.")


def seed_fake_products(num_records):
    """Create fake product"""

    CATEGORIES = [
        "electronics",
        "fashion",
        "home_kitchen",
        "computing",
        "mobile_phones",
        "beauty_care",
        "sports_outdoors",
        "health_wellness",
        "automotive",
        "books_media",
        "toys_games",
        "groceries",
        "office_supplies",
        "pet_supplies",
        "furniture",
        "baby_products",
        "others"
    ]

    for i in range(num_records):
        try:
            # get users instances for owner field
            users = User.objects.all()
            # Create a product with realistic data
            product = Product(
                owner = random.choice(users),  # Assuming user IDs from 1 to 100
                name=fake.ecommerce_name(),
                description=fake.text(max_nb_chars=50),
                category=random.choice(CATEGORIES),
                price=round(random.uniform(10.0, 1000.0), 2),
                stock=random.randint(2, 50),
            )
            
            # ** Save it individually
            product.save()
            # print(snippet.code)
            # Show progress
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1} products...{product.name}")
                
        except Exception as e:
            print(f"Error creating snippet {i+1}: {e}")
            continue
    
    # # Show final count
    # count = Snippet.objects.count()
    # print(f"\n✅ Done! Created {count} snippets in database.")

def seed_fake_orders(num_records):
    """Create fake orders"""
    for i in range(num_records):
        try:
            users = User.objects.all()
            user = random.choice(users)
            order = Order.objects.create(
                user=user,
                order_status=random.choice(["pending", "shipped", "delivered", "cancelled"])
            )
            # add items to order
            products = Product.objects.all()
            for _ in range(random.randint(1, 5)):
                product = random.choice(products)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=product.price,
                    quantity=random.randint(1, 3),
                )
            
            # Show progress
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1} orders...{order.id}")
                
        except Exception as e:
            print(f"Error creating order {i+1}: {e}")
            continue

def seed_fake_payments(num_records):
    """Create fake payments"""
    for i in range(num_records):
        try:
            users = User.objects.all()
            user = random.choice(users)
            # get order instances for order field
            order = Order.objects.all()
            order = random.choice(order)
            Payment.objects.create(
                user=user,
                order=order,
                amount=round(random.uniform(20.0, 2000.0), 2),
                method=random.choice(["card", "paypal", "bank_transfer"]),
                status=random.choice(["pending", "cancel", "confirmed"])
            )
            
            # Show progress
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1} payments...")
                
        except Exception as e:
            print(f"Error creating payment {i+1}: {e}")
            continue

def gen_sample_data(n):
    for _ in range(n):
        print(fake.ecommerce_category(), fake.ecommerce_price())
        # print(fake.first_name(), fake.ecommerce_name(), fake.ecommerce_category(), fake.ecommerce_price())

    id = [1,3,2]
    # print(random.choice(id))


if __name__ == "__main__":
    # run main
    # gen_sample_data(15)
    seed_fake_users(50)
    # seed_fake_products(500)
    # seed_fake_orders(100)
    # seed_fake_payments(100)
    pass
