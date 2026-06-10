import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

users = ["postgres", "phd_user"]
passwords = ["postgres", "phd_pass", "admin", "root", "password", "123456", "1234", "Anuradha", "anuradha"]
databases = ["phd_shortlist", "postgres"]

async def try_conn(user, password, db):
    db_url = f"postgresql+asyncpg://{user}:{password}@localhost:5432/{db}"
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print(f"SUCCESS: user={user}, password={password}, db={db}")
            return db_url
    except Exception as e:
        # print(f"FAILED: user={user}, password={password}, db={db} -> {e}")
        pass
    finally:
        await engine.dispose()
    return None

async def main():
    print("Probing connection...")
    for db in databases:
        for user in users:
            for password in passwords:
                url = await try_conn(user, password, db)
                if url:
                    print("Found valid credentials:", url)
                    return

if __name__ == "__main__":
    asyncio.run(main())
