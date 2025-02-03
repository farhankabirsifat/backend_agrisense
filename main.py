import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import mysql.connector
import aiosmtplib
from email.message import EmailMessage
import os

from database import get_db_connection
from models.AdminAction import AdminAction
from models.croprequest import CropRequest
from models.deleteUser import DeleteUserRequest
from models.emailrequest import EmailRequest
from models.soildatainput import SoilDataInput
from models.userCreate import UserCreate
from models.userUpdate import UserUpdate
from models.userlogin import UserLogin
from models.usersignup import UserSignup

# Initialize FastAPI app
app = FastAPI()

# Email Configuration (Use an App Password for Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "farhan017kabir@gmail.com"
EMAIL_PASSWORD = "lerf wmws nmvc cbhv"

# SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
# EMAIL_SENDER = os.getenv("EMAIL_SENDER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your Flutter app's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Hash a password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Verify a password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# API route for user signup
@app.post("/signup")
async def signup(user: UserSignup):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the email or username already exists
        cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (user.email, user.username))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email or username already exists")

        # Insert the new user
        hashed_password = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (email, username, password,is_admin) VALUES (%s, %s, %s, %s)",
            (user.email, user.username, hashed_password,0),
        )
        conn.commit()

        return {"message": "User registered successfully"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# API route for user login
@app.post("/login")
async def login(user: UserLogin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the user by email
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()

        if not db_user or not verify_password(user.password, db_user["password"]):
            raise HTTPException(status_code=400, detail="Invalid email or password")

        return {"message": "Login successful", "username": db_user["username"]}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# API route for enhanced fertilizer recommendation
@app.post("/fertilizer_recommendations")
async def get_recommendations(request: CropRequest):
    crop_name = request.crop_name
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all relevant details for the given crop
        query = """
        SELECT
            fertilizer,
            soil,
            ideal_ph,
            ideal_humidity,
            natural_fertilizer_tips
        FROM fertilizer_recommendation
        WHERE crop_name = %s
        """
        cursor.execute(query, (crop_name,))
        result = cursor.fetchone()

        if result:
            return result
        else:
            raise HTTPException(status_code=404, detail="Crop not found")
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# API route to recommend multiple crops based on user input
@app.post("/recommend-crop/", response_model=list[str])
async def recommend_crop(soil_data: SoilDataInput):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Fetch all crop data from the database
        cursor.execute("SELECT * FROM crop_data")
        crops = cursor.fetchall()

        # List to store recommended crops and their scores
        recommended_crops = []

        # Compare user input with each crop's ideal parameters
        for crop in crops:
            score = 0

            # Check nitrogen
            if crop["min_nitrogen"] <= soil_data.nitrogen <= crop["max_nitrogen"]:
                score += 1

            # Check phosphorus
            if crop["min_phosphorus"] <= soil_data.phosphorus <= crop["max_phosphorus"]:
                score += 1

            # Check potassium
            if crop["min_potassium"] <= soil_data.potassium <= crop["max_potassium"]:
                score += 1

            # Check pH
            if crop["min_ph"] <= soil_data.ph <= crop["max_ph"]:
                score += 1

            # Check humidity
            if crop["min_humidity"] <= soil_data.humidity <= crop["max_humidity"]:
                score += 1

            # Check temperature
            if crop["min_temperature"] <= soil_data.temperature <= crop["max_temperature"]:
                score += 1

            # If the crop matches at least one parameter, add it to the list
            if score > 0:
                recommended_crops.append({
                    "crop_name": crop["crop_name"],
                    "score": score
                })

        # Sort the recommended crops by score (descending order)
        recommended_crops.sort(key=lambda x: x["score"], reverse=True)

        # Extract the crop names from the sorted list
        # crop_names = [crop["crop_name"] for crop in recommended_crops]
        # Extract the top 5 crop names from the sorted list
        top_5_crops = [crop["crop_name"] for crop in recommended_crops[:5]]

        # If no crops match, return an error
        if not top_5_crops:
            raise HTTPException(status_code=404, detail="No matching crops found for the given soil parameters.")

        return top_5_crops
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        db.close()


@app.post("/send-email/")
async def send_email(request: EmailRequest):
    try:
        # Create Email Message
        email_message = EmailMessage()
        email_message["From"] = EMAIL_SENDER
        email_message["To"] = EMAIL_SENDER  # You will receive the email
        email_message["Subject"] = "New Contact Form Submission"
        email_message.set_content(
            f"Name: {request.name}\nEmail: {request.email}\nMessage: {request.message}"
        )

        # Send Email using SMTP
        await aiosmtplib.send(
            email_message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=EMAIL_SENDER,
            password=EMAIL_PASSWORD,
        )

        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")


# Helper function to check if a user is an admin
def is_admin(email: str):
    """Check if the user with given email is an admin."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user or user["is_admin"] != 1:
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")


@app.post("/admin/login")
async def admin_login(user: UserLogin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the user by email and check if they are an admin
        cursor.execute(
            "SELECT * FROM users WHERE email = %s AND is_admin = 1",
            (user.email,)
        )
        admin_user = cursor.fetchone()

        if not admin_user or not verify_password(user.password, admin_user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password or not an admin user"
            )

        return {
            "message": "Admin login successful",
            "username": admin_user["username"],
            "is_admin": True
        }

    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ✅ Create a new user
@app.post("/admin/create-user/")
async def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Hash the password
    hashed_password = pwd_context.hash(user.password)

    # Insert the user
    cursor.execute("INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
                   (user.username, user.email, hashed_password, 0))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "User created successfully"}


# ✅ Get all users
@app.get("/admin/users/")
async def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, username, email, is_admin FROM users")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"users": users}


# ✅ Update username or password
@app.put("/admin/update-user/")
async def update_user(user_update: UserUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    if user_update.new_username:
        cursor.execute("UPDATE users SET username = %s WHERE username = %s", (user_update.new_username, user_update.username,))

    if user_update.new_password:
        hashed_password = pwd_context.hash(user_update.new_password)
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, user_update.username,))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "User details updated successfully"}


# ✅ Delete a user
# @app.delete("/admin/delete-user/{user_id}")
# async def delete_user(user_id: int):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
#     conn.commit()
#
#     cursor.close()
#     conn.close()
#
#     return {"message": "User deleted successfully"}

@app.delete("/admin/delete-user/")
async def delete_user(request: DeleteUserRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.username,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Delete the user
        cursor.execute("DELETE FROM users WHERE username = %s", (request.username,))
        conn.commit()

        return {"message": "User deleted successfully"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ✅ Promote a user to admin
# @app.put("/admin/promote-user/")
# async def promote_user(action: AdminAction):
#     is_admin(action.admin_email)  # Check if requester is admin
#
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     cursor.execute("SELECT * FROM users WHERE id = %s", (action.target_user_id,))
#     user = cursor.fetchone()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     cursor.execute("UPDATE users SET is_admin = 1 WHERE id = %s", (action.target_user_id,))
#     conn.commit()
#
#     cursor.close()
#     conn.close()
#
#     return {"message": "User promoted to admin successfully"}

@app.put("/admin/promote-user/")
async def promote_user(action: AdminAction):
    is_admin(action.admin_email)  # Check if requester is admin

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the target user exists using username
    cursor.execute("SELECT * FROM users WHERE username = %s", (action.username,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Promote user to admin
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = %s", (action.username,))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": f"User '{action.username}' promoted to admin successfully"}




# ✅ Demote an admin to normal user
# @app.put("/admin/demote-user/")
# async def demote_user(action: AdminAction):
#     is_admin(action.admin_email)  # Check if requester is admin
#
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     cursor.execute("SELECT * FROM users WHERE id = %s AND is_admin = 1", (action.target_user_id,))
#     user = cursor.fetchone()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found or not an admin")
#
#     cursor.execute("UPDATE users SET is_admin = 0 WHERE id = %s", (action.target_user_id,))
#     conn.commit()
#
#     cursor.close()
#     conn.close()
#
#     return {"message": "Admin demoted to normal user successfully"}

@app.put("/admin/demote-user/")
async def demote_user(action: AdminAction):
    is_admin(action.admin_email)  # Check if requester is admin

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the user exists
    cursor.execute("SELECT * FROM users WHERE username = %s", (action.username,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Demote user to normal user
    cursor.execute("UPDATE users SET is_admin = 0 WHERE username = %s", (action.username,))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": f"User with email '{action.username}' has been demoted successfully"}




# Root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Welcome to the Crop Recommendation API"}


# Entry point for Render deployment
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
