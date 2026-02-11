
import sys
import os
import asyncio

# 添加当前目录到 system path 以便可以导入 app 模块
sys.path.append(os.getcwd())

from app.core.database import init_db, get_mongo_db
from app.services.user_service import user_service
from app.models.user import UserCreate
from app.core.security import get_password_hash

async def create_user():
    try:
        # 1. 初始DB
        await init_db()
        print("✅ Database connected")

        # 2. 检查
        user = await user_service.get_user_by_username("admin")
        
        if user:
            print(f"User admin already exists (ID: {user.id})")
            
            # 3. 重置密码
            print("Resetting password to: password123")
            
            db = get_mongo_db()
            hashed_password = get_password_hash("password123")
            
            # 使用 await 执行 update_one
            result = await db.users.update_one(
                {"username": "admin"},
                {"$set": {"hashed_password": hashed_password}}
            )
            
            print(f"Password reset result: {result.modified_count} modified")
            
        else:
            # 4. 创建
            print("Creating new user admin...")
            new_user = UserCreate(
                username="admin", 
                email="admin@example.com", 
                password="password123",  # 明文密码，service层会hash
                is_admin=True
            )
            
            created_user = await user_service.create_user(new_user)
            print(f"User admin created successfully (ID: {created_user.id})")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(create_user())
    finally:
        loop.close()

