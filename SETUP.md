# Roriri Project Desk Setup

## MySQL environment variables

Set these before running migrations:

```powershell
$env:MYSQL_DATABASE="project_management"
$env:MYSQL_USER="your_mysql_user"
$env:MYSQL_PASSWORD="9944"
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
```

Create the database in MySQL before migrating:

```sql
CREATE DATABASE project_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Run

```powershell
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
# Start server (safe): this script will kill any process using the port then start runserver
.\scripts\start_server.ps1 -Port 8000
```

Open `http://127.0.0.1:8000/login/`.

Local defaults are already set for `root` / `9944` and database `project_management`.
