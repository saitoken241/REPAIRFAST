# RepairFast

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![MySQL](https://img.shields.io/badge/mysql-%2300f.svg?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Uvicorn](https://img.shields.io/badge/uvicorn-FF9900?style=for-the-badge&logo=fastapi&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

**RepairFast** is a digital platform for **preventive risk management and incident communication in industrial environments**. It connects employees, analysts, and managers through a structured workflow for reporting, triaging, and resolving operational incidents — ensuring full traceability and promoting a strong safety culture.

---

## 📌 About the Project

In industrial environments, poor communication between teams and the lack of structured incident records can directly compromise operational safety. RepairFast centralizes the entire incident management lifecycle into a single platform, with role-based interfaces tailored for each type of user.

### Problems addressed:

- Fragmented communication between operational teams  
- Lack of traceability in incident records  
- Absence of structured historical data for analysis  
- Difficulty in continuously monitoring risks  

---

## 📁 Project Structure

```

repairfast/
│
├── backend/
│   └── app/
│       ├── main.py               # API entry point and main routes
│       ├── database.py           # MySQL connection via SQLAlchemy
│       ├── models/
│       │   └── user_model.py     # ORM model for the users table
│       ├── schemas/              # (in development) Pydantic validation
│       └── routers/              # (in development) Route modularization
│
├── frontend/
│   └── public/
│       ├── index.html            # Institutional landing page
│       ├── login.html            # User authentication
│       ├── home_employee.html    # Employee dashboard
│       ├── home_analyst.html     # Analyst dashboard
│       └── home_manager.html     # Manager dashboard
│   └── src/
│       ├── css/
│       │   ├── global.css        # Global styles and CSS variables
│       │   └── components.css    # Reusable UI components
│       └── js/
│           ├── api.js            # API integration and data mocks
│           └── utils.js          # Utilities (dates, greetings, DOM helpers)
│
└── requirements.txt

````

---

## 👥 User Roles

The system has three distinct roles, each with its own dashboard and feature set.

### 👷 Employee
Focused on creating and tracking individual incident reports.

- Summary panel with report counts (total, open, in progress, resolved)  
- Personal report list with status filters  
- New report creation flow  
- Access to the Knowledge Base and Risk Map  

---

### 🧪 Analyst
Designed for technical triage and incident analysis.

- Consolidated report table with pagination  
- Critical incidents panel with visual highlights  
- Advanced filters by sector, priority, and status  
- Inline row actions (assign, change status, comment)  
- Analytical dashboard and Risk Map  

---

### 📊 Manager
Strategic interface with full operational visibility.

- Operational KPIs with trend indicators  
- Scope toggle: global view or by sector  
- Sector ranking with SLA metrics  
- Distribution charts by category and priority  
- Power BI integration for executive dashboards  
- Recent reports with full traceability  

---

## 🎨 Frontend

The interface was built using **HTML5, CSS3, and vanilla JavaScript**, with no external frameworks. The design follows a dark theme with orange accents (`#E85C1A`), prioritizing readability and information density.

### Highlights:

- Design system with global CSS variables and reusable components  
- Custom cursor with interaction animations  
- Responsive sidebar with mobile hamburger menu  
- Animated cards with smooth transitions  
- Fully responsive layout (desktop, tablet, and mobile)  
- Skeleton loading states and empty/error feedback  
- Typography: Bebas Neue, DM Sans, and DM Mono (Google Fonts)  

---

## ⚙️ Backend — REST API

Built with **FastAPI + SQLAlchemy + MySQL**, following Separation of Concerns principles and designed for scalability.

### Available Endpoints

| Method | Endpoint           | Description          |
|--------|--------------------|----------------------|
| GET    | `/`                | Welcome message      |
| POST   | `/users/`          | Create a new user    |
| GET    | `/users/`          | List all users       |
| GET    | `/users/{user_id}` | Get user by ID       |
| PUT    | `/users/{user_id}` | Update user          |
| DELETE | `/users/{user_id}` | Delete user          |

---

## 📚 API Documentation

| Interface  | URL                            |
|------------|--------------------------------|
| Swagger UI | http://127.0.0.1:8000/docs     |
| ReDoc      | http://127.0.0.1:8000/redoc    |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+  
- MySQL 8.0+ or MariaDB  
- Git  

---

### 1. Clone the repository

```bash
git clone https://github.com/your-user/repairfast.git
cd repairfast
````

---

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure the database

Create a `.env` file in the root directory:

```env
DATABASE_URL=sqlite:///./test.db

```

---

### 5. Run the migrations 
```bash
alembic upgrade head
```

if the database exists, run:
```bash
alembic stamp head   
alembic upgrade head
```
---

### 6. Test the database:
```bash
sqlite3 test.db
.tables
```
---
### 7. Run the API server

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

### 8. Run the frontend

```bash
# Using Python
python -m http.server 3000 --directory frontend/public

# Using Node.js
npx serve frontend/public
```

---

## 🛠️ Technologies

| Technology        | Purpose               |
| ----------------- | --------------------- |
| Python            | Backend language      |
| FastAPI           | REST API framework    |
| SQLAlchemy        | ORM                   |
| MySQL             | Relational database   |
| PyMySQL           | Database driver       |
| Uvicorn           | ASGI server           |
| Pydantic          | Data validation       |
| python-dotenv     | Environment variables |
| HTML5 / CSS3 / JS | Frontend              |
| Google Fonts      | Typography            |

---

## 🗺️ Roadmap

* [x] Pydantic schemas for validation
* [x] Route modularization (`routers/users.py`)
* [ ] JWT authentication
* [x] Password hashing with bcrypt
* [ ] Full incident management endpoints
* [ ] Frontend integration with real API
* [ ] Automated tests with pytest
* [ ] Docker + Docker Compose
* [ ] Cloud deployment (AWS or Railway)
* [ ] Power BI integration
* [ ] Mobile app for field reporting
* [ ] Interactive risk map
* [ ] Real-time notifications

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 👨‍💻 Author

**ken**
Backend Developer | Cybersecurity Enthusiast


