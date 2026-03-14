from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_mongo_db  # Import your DI dependency
from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.models.user import UserModel
from app.db.schemas.user import UserCreate, UserLogin

router = APIRouter()

@router.post("/register")
async def register_user(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db) # Use DI for MongoDB
):
    # Check if user exists
    if await db["users"].find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = UserModel(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )

    # Save to MongoDB
    await db["users"].insert_one(new_user.model_dump(by_alias=True))
    return {"message": "User created successfully", "user_id": str(new_user.id)}


@router.post("/login")
async def login(
    user_data: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db) # Use DI for MongoDB
):
    user = await db["users"].find_one({"email": user_data.email})

    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Ensure user["_id"] is converted to string for the token payload
    access_token = create_access_token(data={"sub": str(user["_id"]), "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}