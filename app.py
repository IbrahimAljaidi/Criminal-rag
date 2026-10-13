import os
import secrets
import jwt

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, model_validator

from rag_service import ask

from mongodb import (
    get_or_create_user,
    get_or_create_session,
    create_chat_id,
    save_exchange,
    get_last_exchanges,
    get_user_chats,
    get_chat_exchanges,
    delete_chat,
    create_website_user,
    authenticate_website_user,
    users_collection
)

from auth import (
    create_access_token,
    SECRET_KEY,
    ALGORITHM
)


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="Criminal Procedure RAG API",
    version="1.0.0"
)


# ============================================================
# Request Models
# ============================================================

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    email: EmailStr | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def check_identifier(self):
        # Require at least one login identifier.
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required.")

        return self


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UpdateProfileRequest(BaseModel):
    # Website display name.
    name: str = Field(min_length=1, max_length=100)


class QuestionRequest(BaseModel):
    question: str
    platform: str

    # Required for Telegram requests.
    platform_user_id: str | None = None

    # Optional Telegram display name.
    name: str | None = None

    # Website conversation ID.
    # The API creates one automatically for a new chat.
    chat_id: str | None = None


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Authentication
# ============================================================

load_dotenv()

# Private key used by the Telegram bot to access the API.
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")

# Read Bearer tokens from the Authorization header.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_website_user(token: str):
    """
    Verify the JWT and return the authenticated Website user.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token."
            )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token."
        )

    user = users_collection.find_one(
        {
            "user_id": user_id,
            "platform": "website"
        }
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account not found."
        )

    return user


def require_website_user(
    credentials: HTTPAuthorizationCredentials | None
):
    """
    Require Website authentication and return the user.
    """

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Login is required."
        )

    return get_current_website_user(
        credentials.credentials
    )


# ============================================================
# Home Endpoint
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Criminal Procedure RAG API is running"
    }


# ============================================================
# Register
# ============================================================

@app.post("/register", status_code=201)
def register(request: RegisterRequest):
    """
    Register a new Website user.
    """

    try:
        user_id = create_website_user(
            name=request.name,
            password=request.password,
            email=str(request.email) if request.email else None,
            phone=request.phone
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    access_token = create_access_token(user_id)

    return {
        "message": "Account created successfully.",
        "user_id": user_id,
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============================================================
# Login
# ============================================================

@app.post("/login")
def login(request: LoginRequest):
    """
    Log in using email or phone and password.
    """

    user = authenticate_website_user(
        identifier=request.identifier,
        password=request.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email/phone or password."
        )

    access_token = create_access_token(
        user_id=user["user_id"]
    )

    return {
        "message": "Login successful.",
        "user_id": user["user_id"],
        "name": user["name"],
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============================================================
# Website Profile
# ============================================================

@app.get("/profile")
def get_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    """
    Return the authenticated Website user's profile.
    """

    user = require_website_user(credentials)

    return {
        "user_id": user["user_id"],
        "name": user.get("name", ""),
        "email": user.get("email"),
        "phone": user.get("phone")
    }


@app.patch("/profile")
def update_profile(
    request: UpdateProfileRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    """
    Update the authenticated Website user's display name.
    """

    user = require_website_user(credentials)

    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty."
        )

    users_collection.update_one(
        {
            "user_id": user["user_id"],
            "platform": "website"
        },
        {
            "$set": {
                "name": name
            }
        }
    )

    return {
        "message": "Profile updated successfully.",
        "name": name
    }


# ============================================================
# Ask RAG Endpoint
# ============================================================

@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    # --------------------------------------------------------
    # 1. Authenticate the user
    # --------------------------------------------------------

    if request.platform == "website":

        user = require_website_user(credentials)

        user_id = user["user_id"]
        platform = "website"

        # Use the existing Website chat or create a new one.
        chat_id = request.chat_id or create_chat_id()

        platform_user_id = None

    elif request.platform == "telegram":

        # Verify that the request came from our Telegram bot.
        if (
            not TELEGRAM_API_KEY
            or credentials is None
            or not secrets.compare_digest(
                credentials.credentials,
                TELEGRAM_API_KEY
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized Telegram request."
            )

        if not request.platform_user_id:
            raise HTTPException(
                status_code=400,
                detail="Telegram user ID is required."
            )

        platform_user_id = str(
            request.platform_user_id
        )

        # Find or create the Telegram user.
        user_id = get_or_create_user(
            platform="telegram",
            platform_user_id=platform_user_id,
            name=request.name
        )

        platform = "telegram"
        chat_id = None

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported platform."
        )

    # --------------------------------------------------------
    # 2. Get or create the active storage session
    # --------------------------------------------------------

    try:
        session_id = get_or_create_session(
            user_id=user_id,
            platform=platform,
            platform_user_id=platform_user_id
        )

        # ----------------------------------------------------
        # 3. Get recent conversation context
        # ----------------------------------------------------

        history = get_last_exchanges(
            session_id=session_id,
            user_id=user_id,
            limit=5,
            chat_id=chat_id
        )

        # ----------------------------------------------------
        # 4. Generate the RAG answer
        # ----------------------------------------------------

        answer = ask(
            question=request.question,
            history=history
        )

        # ----------------------------------------------------
        # 5. Save the exchange
        # ----------------------------------------------------

        try:
            # Try to save the exchange in the current storage session.
            save_exchange(
                session_id=session_id,
                user_id=user_id,
                question=request.question,
                answer=answer,
                platform=platform,
                chat_id=chat_id
            )

        except ValueError:
            # The session may have become full because another request
            # saved exchange 100 before this request.
            session_id = get_or_create_session(
                user_id=user_id,
                platform=platform,
                platform_user_id=platform_user_id
            )

            # Retry saving in the available/new storage session.
            save_exchange(
                session_id=session_id,
                user_id=user_id,
                question=request.question,
                answer=answer,
                platform=platform,
                chat_id=chat_id
            )

        # ----------------------------------------------------
        # 6. Build the response
        # ----------------------------------------------------

        response = {
            "question": request.question,
            "answer": answer,
            "session_id": session_id
        }

        if platform == "website":
            response["chat_id"] = chat_id

        return response

    except HTTPException:
        raise

    except Exception as error:
        print("API Error:", error)

        raise HTTPException(
            status_code=500,
            detail="حدث خطأ أثناء معالجة السؤال."
        )


# ============================================================
# Website Chat History
# ============================================================

@app.get("/chats")
def get_chats(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    """
    Return the authenticated Website user's chat history.
    """

    user = require_website_user(credentials)

    chats = get_user_chats(
        user_id=user["user_id"]
    )

    return {
        "chats": chats
    }


# ============================================================
# Get One Website Chat
# ============================================================

@app.get("/chats/{chat_id}")
def get_chat(
    chat_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    """
    Return all exchanges belonging to one Website chat.
    """

    user = require_website_user(credentials)

    exchanges = get_chat_exchanges(
        chat_id=chat_id,
        user_id=user["user_id"]
    )

    return {
        "chat_id": chat_id,
        "messages": exchanges
    }


# ============================================================
# Delete Website Chat
# ============================================================

@app.delete("/chats/{chat_id}")
def remove_chat(
    chat_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):
    """
    Delete one Website chat belonging to the authenticated user.
    """

    user = require_website_user(credentials)

    deleted = delete_chat(
        chat_id=chat_id,
        user_id=user["user_id"]
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Chat not found."
        )

    return {
        "message": "Chat deleted successfully."
    }