
```markdown
# 🛒 E-Commerce Backend API

A robust Django REST Framework backend for e-commerce applications.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16
- pip

### Installation
```bash
# Clone repo
git clone <https://github.com/abuaminuu/project-nexus-ecommerce.git>
cd project-nexus-ecommerce

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## 📚 API Documentation

Interactive API docs available at: `http://localhost:8000/swagger/`

## 🔐 Authentication

Uses JWT tokens:
```bash
# Get token
POST /api/auth/token/
{"username": "user", "password": "pass"}

# Use token
Authorization: Bearer <your_token>
```

## 📦 Main Features

- **User Authentication** (JWT)
- **Product Management** (CRUD with filtering/sorting)
- **Order Processing** (Multi-item orders)
- **Payment Integration** (Flutterwave)
- **API Documentation** (Swagger/OpenAPI)

## 🗄️ Database Schema

```
User → Products (Owner)
User → Orders → OrderItems → Product
```

## 🧪 Testing

```bash
# Run all tests
# python manage.py test

# Run specific tests
python manage.py test commerce.tests.test_models
```

## 🐳 Docker (Optional) TODO

```bash
docker-compose up --build
```

## 📁 Project Structure

```
ecommerce/
├── commerce/          # Main app
├── products/          # Product models/views
├── orders/            # Order management
├── payments/          # Payment integration
└── tests/            # Test suites
```

## TODO How to run the application
## 📄 License

MIT
```

**Key Sections:**
1. Quick start
2. API docs location  
3. Authentication method
4. Main features
5. Testing commands
6. Project structure

**Keep it brief** - developers just need to get it running fast. Add more details only if needed.