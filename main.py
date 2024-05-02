import aiomysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Конфигурация подключения к базе данных
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "Amirgamer123",
    "db": "registrations",
}

# Класс для работы с базой данных
class DB:
    pool = None

    @classmethod
    async def connect(cls):
        cls.pool = await aiomysql.create_pool(**DATABASE_CONFIG)

    @classmethod
    async def disconnect(cls):
        cls.pool.close()
        await cls.pool.wait_closed()

    @classmethod
    async def execute(cls, query, *args):
        async with cls.pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(query, args)
                await connection.commit()
                return cursor.lastrowid

    @classmethod
    async def fetchone(cls, query, *args):
        async with cls.pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(query, args)
                return await cursor.fetchone()

# Модель пользователя
class User(BaseModel):
    username: str
    password: str

# Регистрация нового пользователя
@app.post("/register/")
async def register_user(user: User):
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    try:
        await DB.execute(query, user.username, user.password)
    except aiomysql.IntegrityError as e:
        if e.args[0] == 1062:  # Duplicate entry error code
            raise HTTPException(status_code=400, detail="Username already registered")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"message": "User successfully registered"}

# Удаление пользователя
@app.delete("/unregister/{username}/")
async def unregister_user(username: str):
    query = "DELETE FROM users WHERE username = %s"
    result = await DB.fetchone("SELECT * FROM users WHERE username = %s", username)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    await DB.execute(query, username)
    return {"message": f"User {username} successfully unregistered"}

# Подключение к базе данных при запуске приложения
@app.on_event("startup")
async def startup_db_client():
    await DB.connect()

# Отключение от базы данных при остановке приложения
@app.on_event("shutdown")
async def shutdown_db_client():
    await DB.disconnect()
