#  RepairFast API

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![MySQL](https://img.shields.io/badge/mysql-%2300f.svg?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Uvicorn](https://img.shields.io/badge/uvicorn-FF9900?style=for-the-badge&logo=fastapi&logoColor=white)

The **RepairFast API** is the backend of a digital platform designed for **preventive risk management and incident communication in industrial environments**.

The goal of the platform is to **improve communication between operational teams**, record incidents with traceability, and enable continuous monitoring of risks in order to **reduce accidents and improve operational safety**.

This API was built using **FastAPI + SQLAlchemy + MySQL**, focusing on:

- ⚡ High performance
- 🧹 Clean code
- 🏗️ Scalable architecture
- 📚 Automatic API documentation
- 🔎 Data traceability

---

#  About the RepairFast Project

**RepairFast** is a digital solution designed for **industrial environments**, where proper communication of risks and accurate incident records are essential to prevent accidents.

In many industrial scenarios, problems such as:

- poor communication between teams
- fragmented incident reports
- lack of structured historical data
- difficulty tracking operational events

can negatively impact **operational safety**.

RepairFast aims to solve these problems by providing:

- structured incident reporting
- full historical event tracking
- continuous risk monitoring
- improved communication between teams

This API represents the **core backend component of the RepairFast platform**.

---

#  API Features

- ✅ Full **CRUD** for user management
- ✅ Structure prepared for **incident management systems**
- ✅ Automatic API documentation using **Swagger UI** and **ReDoc**
- ✅ Error handling with `HTTPException`
- ✅ Secure **MySQL database connection via SQLAlchemy**
- ✅ Modular architecture ready for scaling
- ✅ Data validation following backend best practices

---

#  System Architecture

The API follows **Separation of Concerns** principles to improve maintainability and scalability.

```

repair-fast/
│
├── main.py
│   ├── Application entry point
│   └── Main API routes
│
├── database.py
│   ├── MySQL connection configuration
│   └── SQLAlchemy engine
│
├── models/
│   └── user_model.py
│       └── ORM model for the users table
│
├── schemas/        # (under development)
│   └── Pydantic data validation
│
├── routers/        # (under development)
│   └── Route modularization
│
└── requirements.txt

````

The architecture was designed to support future expansion such as:

- authentication systems
- analytics dashboards
- microservices architecture
- integrations with external systems

---

#  Running the Project

## Prerequisites

- Python **3.9+**
- MySQL **8.0+** or MariaDB
- Git

---

## 1️⃣ Clone the repository

```bash
git clone https://github.com/your-user/repair-fast.git
cd repair-fast
````

---

## 2️⃣ Create a virtual environment

```bash
python -m venv venv
```

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3️⃣ Install dependencies

```bash
pip install fastapi uvicorn sqlalchemy pymysql
```

---

## 4️⃣ Configure the database

Create a MySQL database:

```
meubanco
```

Default credentials in the project:

```
User: root
Password: root
```

If necessary, modify the `DATABASE_URL` in:

```
database.py
```

---

## 5️⃣ Start the API server

```bash
uvicorn main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

#  Automatic Documentation

One of the advantages of **FastAPI** is automatic interactive documentation.

### Swagger UI

```
http://127.0.0.1:8000/docs
```

### ReDoc

```
http://127.0.0.1:8000/redoc
```

---

#  API Endpoints

| Method | Endpoint           | Description         |
| ------ | ------------------ | ------------------- |
| GET    | `/`                | Welcome message     |
| POST   | `/users/`          | Create a new user   |
| GET    | `/users/`          | List all users      |
| GET    | `/users/{user_id}` | Retrieve user by ID |
| PUT    | `/users/{user_id}` | Update user         |
| DELETE | `/users/{user_id}` | Delete user         |

---

#  Future Platform Integrations

RepairFast was designed as part of a larger ecosystem that may include:

* 📊 Analytical dashboards (**Power BI**)
* 📱 Mobile application for incident reporting
* 🗺️ Interactive risk maps
* 🧾 Dynamic incident forms
* 📚 Safety knowledge base
* 📈 Operational performance monitoring

---

#  Roadmap

* [ ] Pydantic schemas for request validation
* [ ] Modular routing (`routers/users.py`)
* [ ] Authentication with **JWT**
* [ ] Password hashing with **bcrypt**
* [ ] Automated testing with **pytest**
* [ ] Docker + Docker Compose
* [ ] Cloud deployment on **AWS**
* [ ] Log storage and monitoring integration

---

#  Technologies Used

| Technology      | Purpose                   |
| --------------- | ------------------------- |
| Python          | Main programming language |
| FastAPI         | Backend web framework     |
| SQLAlchemy      | ORM                       |
| MySQL           | Relational database       |
| Uvicorn         | ASGI server               |
| Swagger / ReDoc | API documentation         |

---

#  Project Goal

This project was developed as an applied study focused on **operational safety and risk management in industrial environments**.

The objective is to demonstrate how digital solutions can:

* improve incident communication
* increase data traceability
* reduce operational failures
* support safety culture in organizations

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 👨‍💻 Author

**ken**

Backend Developer | Cybersecurity Enthusiast

📧 []()
🔗 LinkedIn: 




