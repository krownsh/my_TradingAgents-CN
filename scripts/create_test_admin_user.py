
import sys
import os
import asyncio

# 添加当前目錄到系統路徑
sys.path.append(os.getcwd())

from app.services.user_service import user_service

async def create_user():
    try:
        print("🚀 [Step 1] Connecting to MongoDB via UserService...")
        # UserService 在初始化時會自動連接
        
        username = "admin"
        password = "password123"
        email = "admin@example.com"
        
        print(f"🔍 [Step 2] Checking if user '{username}' exists...")
        user = await user_service.get_user_by_username(username)
        
        if user:
            print(f"✅ User '{username}' already exists (ID: {user.id})")
            print(f"🔄 [Step 3] Resetting password to '{password}'...")
            
            # 直接使用 hash_password 和 MongoDB 更新，避免 change_password 需要舊密碼
            hashed_password = user_service.hash_password(password)
            result = user_service.users_collection.update_one(
                {"username": username},
                {"$set": {"hashed_password": hashed_password, "is_active": True}}
            )
            print(f"✨ Password reset successfully! ({result.modified_count} records updated)")
        else:
            print(f"🆕 [Step 3] Creating new admin user '{username}'...")
            # 使用內置的 create_admin_user 方法
            user = await user_service.create_admin_user(
                username=username,
                password=password,
                email=email
            )
            if user:
                print(f"✨ Admin user created successfully! (ID: {user.id})")
            else:
                print("❌ Failed to create admin user.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error occurred: {e}")
    finally:
        user_service.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(create_user())
