## Database migrations

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Apply migrations:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

Create a new migration after model changes:

```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe change"
```

Mark an existing database as already matching the current schema:

```powershell
.\.venv\Scripts\alembic.exe stamp head
```
