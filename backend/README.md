# Secure File Transfer Backend

Production-ready Django REST API for secure peer-to-peer file transfer application.

## Tech Stack

- **Python 3.x**
- **Django 4.2+**
- **Django REST Framework**
- **SQLite** (persistent database)
- **JWT Authentication** (Simple JWT)
- **CORS Support** (django-cors-headers)

## Project Structure

```
backend/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # SQLite database (created after migrate)
├── config/                  # Project configuration
│   ├── settings.py          # Django settings
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI config
│   └── asgi.py              # ASGI config
├── users/                   # User & authentication app
│   ├── models.py            # User model
│   ├── serializers.py       # API serializers
│   ├── views.py             # Auth views
│   ├── views_users.py       # User listing views
│   ├── urls.py              # Auth URLs
│   ├── urls_users.py        # User URLs
│   └── admin.py             # Admin config
├── files/                   # File metadata app
│   ├── models.py            # File & FileChunk models
│   ├── serializers.py       # API serializers
│   ├── views.py             # File views
│   ├── urls.py              # File URLs
│   └── admin.py             # Admin config
└── transfers/               # Transfer management app
    ├── models.py            # Transfer & TransferLog models
    ├── serializers.py       # API serializers
    ├── views.py             # Transfer views
    ├── urls.py              # Transfer URLs
    └── admin.py             # Admin config
```

## Quick Start

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py makemigrations users files transfers
python manage.py migrate
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 5. Seed Sample Data

```bash
python manage.py seed_data
```

This creates sample users, files, and transfers for testing.

### 6. Run Development Server

```bash
python manage.py runserver 127.0.0.1:8000
```

Server runs at: `http://localhost:8000`

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Register new user |
| POST | `/api/v1/auth/login/` | Login (returns JWT) |
| POST | `/api/v1/auth/logout/` | Logout |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| GET | `/api/v1/auth/profile/` | Get current user profile |
| PUT | `/api/v1/auth/profile/` | Update profile |
| POST | `/api/v1/auth/password/change/` | Change password |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/` | List all users |
| GET | `/api/v1/users/online/` | List online users |
| GET | `/api/v1/users/<id>/` | Get user details |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/files/` | List user's files |
| POST | `/api/v1/files/` | Create file metadata |
| GET | `/api/v1/files/<id>/` | Get file details |
| DELETE | `/api/v1/files/<id>/` | Delete file |
| GET | `/api/v1/files/<id>/chunks/` | List file chunks |
| GET | `/api/v1/files/<id>/progress/` | Get transfer progress |

### Transfers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/transfers/` | List all transfers |
| POST | `/api/v1/transfers/` | Create transfer |
| GET | `/api/v1/transfers/<id>/` | Get transfer details |
| PATCH | `/api/v1/transfers/<id>/` | Update transfer |
| POST | `/api/v1/transfers/<id>/action/` | Perform action |
| GET | `/api/v1/transfers/sent/` | List sent transfers |
| GET | `/api/v1/transfers/received/` | List received transfers |
| GET | `/api/v1/transfers/pending/` | List pending transfers |
| GET | `/api/v1/transfers/active/` | List active transfers |
| GET | `/api/v1/transfers/stats/` | Get statistics |

## API Documentation

Interactive documentation available at:

- **Swagger UI:** http://localhost:8000/api/docs/
- **ReDoc:** http://localhost:8000/api/redoc/
- **OpenAPI Schema:** http://localhost:8000/api/schema/

## Test Credentials

After running `seed_data`:

| Username | Password | Status |
|----------|----------|--------|
| alice | password123 | Online |
| bob | password123 | Online |
| charlie | password123 | Offline |
| diana | password123 | Online |
| evan | password123 | Offline |

## Admin Panel

Access Django admin at: http://localhost:8000/admin/

Login with superuser credentials created earlier.

## Frontend Integration

See [documentation/api_docs.md](../documentation/api_docs.md) for detailed frontend integration guide.

### Quick Example

```typescript
import authService from '@/lib/authService';

// Login
const { access, refresh, user } = await authService.login({
  username: 'alice',
  password: 'password123'
});

// Use in API calls
import userService from '@/lib/userService';
const users = await userService.getUsers();
```

## Environment Variables

For production, set these environment variables:

```bash
DJANGO_SECRET_KEY=your-secure-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com
```

## Database

SQLite database is stored at `backend/db.sqlite3`.

For production, consider migrating to PostgreSQL:

```python
# config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'secure_transfer',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## License

MIT License
