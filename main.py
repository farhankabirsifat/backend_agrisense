import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import mysql.connector
import aiosmtplib
from email.message import EmailMessage
import os

from models.croprequest import CropRequest
from models.emailrequest import EmailRequest
from models.soildatainput import SoilDataInput
from models.userlogin import UserLogin
from models.usersignup import UserSignup

# Initialize FastAPI app
app = FastAPI()

# Email Configuration (Use an App Password for Gmail)
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 587
# EMAIL_SENDER = "farhan017kabir@gmail.com"
# EMAIL_PASSWORD = "lerf wmws nmvc cbhv"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your Flutter app's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MySQL database configuration
# db_config = {
#     "host": "localhost",
#     "user": "root",
#     "password": "",
#     "database": "crop_and_fertilizer_recommendation_db",
#     "port": 4306,
# }

# db_config = {
#     "host": "bepjd6wyxkg8i157jrtn-mysql.services.clever-cloud.com",
#     "user": "ux3pl9tv87elba36",
#     "password": "nQjG2mZ3xUSIdLePpbKg",
#     "database": "bepjd6wyxkg8i157jrtn",
#     "port": 3306,
# }

db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")


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
            "INSERT INTO users (email, username, password) VALUES (%s, %s, %s)",
            (user.email, user.username, hashed_password),
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


# Root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Welcome to the Crop Recommendation API"}


# Entry point for Render deployment
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
