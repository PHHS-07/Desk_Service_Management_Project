# Desk Service Management System

A comprehensive project and service management platform built with Django. This system allows administrators to manage clients and projects, while providing dedicated dashboards for managers and clients to track requests, projects, and payments.

## Features

- **Admin Dashboard**: Manage projects, clients, and system logs.
- **Manager Dashboard**: Track assigned projects and handle client requests.
- **Client Portal**: Submit service requests and view project progress.
- **Payment Tracking**: Integrated system for monitoring client payments.
- **Real-time Updates**: Interactive UI for project status and management.

## Prerequisites

- Python 3.8+
- MySQL Server
- Virtual Environment (`venv`)

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/PHHS-07/Desk_Service_Management_Project.git
cd Desk_Service_Management_Project
```

### 2. Set up the Database
Create the database in MySQL:
```sql
CREATE DATABASE project_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Environment Configuration
Set up your MySQL environment variables. You can create a `.env` file or set them in your shell:
```powershell
$env:MYSQL_DATABASE="project_management"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
```

### 4. Install Dependencies
```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run Migrations
```powershell
python manage.py migrate
```

### 6. Create Superuser
```powershell
python manage.py createsuperuser
```

## Running the Application

To start the development server, you can use the provided script which ensures the port is available:
```powershell
.\scripts\start_server.ps1 -Port 8000
```

Access the application at `http://127.0.0.1:8000/`.

## Project Structure

- `core/`: Main application logic, templates, and static files.
- `config/`: Project configuration and settings.
- `scripts/`: Helper scripts for deployment and management.
- `media/`: User-uploaded content.

## License
This project is for internal use at PHHS.
