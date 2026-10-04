import asyncio
from backend.app.database import engine
from backend.app.models import Base

async def test_database_and_models():
    print("Initiating ORM Test...")
    try:
        # Use the async engine to connect to PostgreSQL
        async with engine.begin() as conn:
            print("Connection successful. Creating tables...")
            
            # run_sync forces the async engine to execute the standard SQLAlchemy table creation
            await conn.run_sync(Base.metadata.create_all)
            
        print("SUCCESS: ALL MedFlow tables were mapped and created in the database!")
    except Exception as e:
        print(f"FAILED: Connection or mapping error: {e}")
        
if __name__ == "__main__":
    asyncio.run(test_database_and_models())