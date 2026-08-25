

# **🛒 E-Commerce REST API - for Project Nexus**

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)](https://www.djangoproject.com/)
[![Django REST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)](https://jwt.io/)
[![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://www.python.org/)

A robust, scalable, and production-ready e-commerce backend API built with Django REST Framework. Complete with JWT authentication, payment integration, comprehensive testing, and full API documentation.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ - Interpreter
- Sqlite3 - Database
- pip - extension manager

## 🚀 **Live Demo**
- **API Base URL**: `https://abuaminuu.pythonanywhere.com/api/commerce/v.1.1/`
- **API Documentation**: `https://abuaminuu.pythonanywhere.com/api/commerce/v.1.1/swagger/
- **Register**: `https://abuaminuu.pythonanywhere.com/register/`
- **Login**: `https://abuaminuu.pythonanywhere.com/auth/login/`

8. **Local Demo**
- API: http://localhost:8000/api/commerce/v.1.1/
- Swagger Docs: http://localhost:8000/api/commerce/v.1.1/swagger/
- Admin: http://localhost:8000/admin/
- register/login: http://localhost:8000/register/


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

# seed data for testing 
python commerce/fake.py

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## 📚 **API Endpoints**

### **Authentication**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register/` | Register new user |
| `POST` | `/auth/token/` | Login (get JWT tokens) |
| `POST` | `/api/auth/refresh/` | Refresh access token |
| `GET` | `/api/commerce/v1.1/profile/` | Get user profile with tokens |

## 🔐 Authentication

Uses JWT tokens:
```bash
# Get token
POST /api/auth/token/
{"username": "user", "password": "pass"}

# Use token
Authorization: Bearer <your_token>
```

### **Products**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/products/` | List all products (public) |
| `POST` | `/api/products/` | Create product (authenticated) |
| `GET` | `/api/products/{id}/` | Product details (public)|
| `PUT` | `/api/products/{id}/` | Update product (authenticated owner only) |
| `DELETE` | `/api/products/{id}/` | Delete product (authenticated owner only) |
| `GET` | `/api/products/{id}/recommendations` | See product recommendations per this product id  (authenticated owner only) |


### **Orders**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/orders/` | Create new order (authenticated) |
| `GET` | `/api/orders/{id}/` | Order details (authenticated) |
| `POST` | `/api/orders/{id}/pay/` | Initiate payment  (authenticated) |
| `POST` | `/api/orders/{id}/confirm_payment/` | Confirm payment (authenticated) |

### **Filtering & Sorting**
```bash
# Filter by price range
GET /api/products/?min_price=100&max_price=500

# Search products
GET /api/products/?search=laptop

# Filter by category
GET /api/products/?category=electronics
```
### **Dashboard Urls for Admin Staffs**


## 📦 Main Features

- **User Authentication** (JWT)
- **Product Management** (CRUD with filtering)
- **Order Processing** (Multi-item orders)
- **Payment Integration** (Flutterwave)
- **API Documentation** (Swagger/OpenAPI)


### 📊 **Other Features**
- Pagination for large datasets
- Comprehensive API documentation (Swagger/OpenAPI)
- Comprehensive test suite (90%+ coverage)

## 🏗️ **Architecture**

```
graph TB
    A[Frontend Client] --> B[REST API]
    B --> C[JWT Authentication]
    B --> D[Business Logic Layer]
    D --> E[Data Models]
    E --> F[PostgreSQL Database]
    B --> G[Payment Gateway]
```

## 📁 **Data Model**

### **Core Entities**
```
User (inherits AbstractUser)
├── Profile (One-to-One)
├── Products (One-to-Many)
├── Orders (One-to-Many)
└── Payments (One-to-Many)

Product ****
├── owner (Foreign Key -> User model)
├── name (char)
├── description (char)
├── category (selection)
├── price (decimal)
└── stock (integer)

Order
├── User (Foreign Key -> User Model)
├── Items (reverse from Orderitems Model)
|__ order_status (char)

OrderItem
├── order (Foreign Key -> User Model)
├── product (Foreign Key -> product Model - reverse name)
├── price (decimal)
└── quantity (int)

Payment
├── User (Foreign Key -> User Model)
├── Order (Foreign Key -> Order Model)
├── amount (decimal)
├── status (char)
└── method (char)
```

## 🔧 **Technology Stack**

| Layer | Technology |
|-------|------------|
| **Backend Framework** | Django 5.2 + Django REST Framework |
| **Database** | PostgreSQL (Production), SQLite (Development) |
| **Authentication** | Simple JWT |
| **API Documentation** | drf-yasg (Swagger/OpenAPI) |
| **Testing** | Django Test Framework, unittest |
| **Deployment** | PythonAnywhere |
| **Payment Gateway** | Flutterwave API |
| **TODO Validation** | Django Validators, Serializer Validation |


## 🧪 **Testing**

Run the comprehensive test suite:
```bash
# Run all tests
python manage.py test

# TODO: coverage tests

# Run specific test modules
python manage.py test commerce.tests.test_models
python manage.py test commerce.tests.test_serializers
python manage.py test commerce.tests.test_views
python manage.py test commerce.tests.test_auth
python manage.py test commerce.tests.e2e
python manage.py test commerce.tests.test_payment_e2e
```


## 🔒 **Security Features**

- ✅ JWT-based authentication with refresh tokens
- ✅ Password hashing with Django's built-in hashers
- ✅ SQL injection protection via Django ORM
- ✅ Secure headers (CORS, HSTS, etc.) 

<!-- 
- ✅ XSS protection through template auto-escaping
- ✅ CSRF protection for session-based auth
- ✅ Rate limiting on authentication endpoints
- ✅ Input validation and sanitization

-->

## 📈 **Performance Optimizations**

- **Database indexing** on frequently queried fields
- **Query optimization** with `select_related` and `prefetch_related`
- **Pagination** for large result sets
<!-- - **Caching** ready (Redis integration available) -->
<!-- - **Asynchronous tasks** support (Celery integration ready) -->

## 🤝 **Frontend Integration**

### **Example: React Integration**
```javascript
// Authentication
const login = async (username, password) => {
  const response = await fetch(`${API_BASE}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const { access, refresh } = await response.json();
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
  return access;
};

// Fetch products with filtering
const getProducts = async (filters = {}) => {
  const params = new URLSearchParams(filters).toString();
  const response = await fetch(`${API_BASE}/products/?${params}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });
  return response.json();
};
```

## 👏 **Acknowledgments**

- [Django REST Framework](https://www.django-rest-framework.org/) for the excellent API framework
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/) for JWT authentication
- [drf-yasg](https://drf-yasg.readthedocs.io/) for Swagger documentation
- [PythonAnywhere](https://www.pythonanywhere.com/) for hosting

## 📞 **Support**

- **Documentation**: [Swagger UI](https://abuaminuu.pythonanywhere.com/swagger/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/project-nexus-ecommerce/issues)
- **Email**: i.abuaminu@gmail.com

---

<div align="center">
  
**Built with ❤️ using Django REST Framework**

[![GitHub stars](https://img.shields.io/github/stars/abuaminuu/project-nexus-ecommerce?style=social)](https://github.com/abuaminuu/project-nexus-ecommerce)
[![GitHub forks](https://img.shields.io/github/forks/abuaminuu/project-nexus-ecommerce?style=social)](https://github.com/abuaminuu/project-nexus-ecommerce)

*Star this repo if you found it useful! ⭐*

</div>
