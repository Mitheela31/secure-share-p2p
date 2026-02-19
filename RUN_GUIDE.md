# 🚀 Running Frontend & Backend Separately

This guide explains how to run the Django backend and React frontend as separate services.

---

## 📁 Project Structure

```
project/
├── backend/          # Django REST API (Port 8000)
├── frontend/         # React + Vite (Port 5173)
└── documentation/
```

---

## 🔧 BACKEND (Django) - Port 8000

### Prerequisites
- Python 3.10+ installed
- pip (Python package manager)

### Step 1: Open Terminal & Navigate to Backend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\backend"
```

### Step 2: Create Virtual Environment (Recommended - One Time)
```powershell
py -m venv venv
```

### Step 3: Activate Virtual Environment
```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
.\venv\Scripts\activate.bat
```

### Step 4: Install Dependencies
```powershell
py -m pip install -r requirements.txt
```

### Step 5: Run Migrations (First Time / After Model Changes)
```powershell
py manage.py migrate
```

### Step 6: Start Backend Server
```powershell
py manage.py runserver 8000
```

### ✅ Backend Running At:
- **API**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/
- **API Docs (Swagger)**: http://localhost:8000/api/docs/
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc/

---

## 🎨 FRONTEND (React + Vite) - Port 5173

### Prerequisites
- Node.js 18+ installed
- npm or bun package manager

### Step 1: Open NEW Terminal & Navigate to Frontend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\frontend"
```

### Step 2: Install Dependencies (First Time)
```powershell
# Using npm
npm install

# OR using bun (faster)
bun install
```

### Step 3: Start Frontend Development Server
```powershell
# Using npm
npm run dev

# OR using bun
bun run dev
```

### ✅ Frontend Running At:
- **App**: http://localhost:5173/

---

## 🔄 Running Both Together (Two Terminals)

### Terminal 1 - Backend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\backend"
py manage.py runserver 8000
```

### Terminal 2 - Frontend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\frontend"
npm run dev
```

---

## 🌐 API Communication

The frontend is configured to communicate with backend at `http://localhost:8000`.

### CORS Configuration (Already Set in Backend)
The backend allows requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (React default)

### API Base URL in Frontend
Check/update in `frontend/src/lib/api.ts`:
```typescript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

---

## 📋 Available API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register/` | POST | User registration |
| `/api/v1/auth/login/` | POST | User login (returns JWT) |
| `/api/v1/auth/logout/` | POST | User logout |
| `/api/v1/auth/profile/` | GET/PUT | User profile |
| `/api/v1/users/` | GET | List all users |
| `/api/v1/users/<id>/` | GET | Get user details |
| `/api/v1/files/` | GET/POST | List/Upload files |
| `/api/v1/transfers/` | GET/POST | List/Create transfers |

---

## 🛠️ Common Commands

### Backend Commands
```powershell
# Run server
py manage.py runserver 8000

# Create superuser (admin access)
py manage.py createsuperuser

# Make migrations after model changes
py manage.py makemigrations

# Apply migrations
py manage.py migrate

# Run with different port
py manage.py runserver 8080
```

### Frontend Commands
```powershell
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Lint code
npm run lint
```

---

## 🔥 Quick Start Script

### Option 1: Run Backend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\backend" ; py manage.py runserver 8000
```

### Option 2: Run Frontend
```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\frontend" ; npm run dev
```

---

## ⚠️ Troubleshooting

### Backend Issues

**1. "py is not recognized"**
```powershell
# Use python instead
python manage.py runserver 8000
```

**2. "Module not found"**
```powershell
py -m pip install -r requirements.txt
```

**3. "Port already in use"**
```powershell
# Use different port
py manage.py runserver 8001
```

### Frontend Issues

**1. "npm is not recognized"**
- Install Node.js from https://nodejs.org/

**2. "Module not found"**
```powershell
npm install
```

**3. "Port 5173 in use"**
```powershell
# Vite will auto-select next available port
# Or manually specify:
npm run dev -- --port 3000
```

---

## 📱 Development Workflow

1. **Start Backend First** (Terminal 1)
   - Handles API requests, database, authentication

2. **Start Frontend Second** (Terminal 2)
   - Connects to backend API
   - Hot-reload for UI changes

3. **Keep Both Running**
   - Backend: Handles all data operations
   - Frontend: User interface

---

## 🔐 Creating Admin User

```powershell
cd "c:\Users\M MOHAMED IMRAN\OneDrive\Desktop\project\backend"
py manage.py createsuperuser
```

Then access admin panel at: http://localhost:8000/admin/

---

## 📊 Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐
│    FRONTEND     │  HTTP   │    BACKEND      │
│  React + Vite   │◄───────►│  Django REST    │
│  Port: 5173     │  JSON   │  Port: 8000     │
└─────────────────┘         └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │    DATABASE     │
                            │    SQLite       │
                            │   db.sqlite3    │
                            └─────────────────┘
```

---

## ✅ Verification Checklist

- [ ] Backend running at http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/api/docs/
- [ ] Frontend running at http://localhost:5173
- [ ] Frontend can call backend APIs (no CORS errors)
- [ ] Login/Register working

---

**Happy Coding! 🎉**
