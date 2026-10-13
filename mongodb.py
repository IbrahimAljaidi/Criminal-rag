import os
import re
import uuid

from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from auth import hash_password, verify_password


# Load environment variables from .env
load_dotenv()


# ============================================================
# MongoDB Connection
# ============================================================

MONGODB_URI = os.getenv("MONGODB_URL")

client = MongoClient(MONGODB_URI)

database = client["legal_assistant"]


# ============================================================
# Collections
# ============================================================

# users    -> stores Website and Telegram users
# sessions -> stores user sessions and their messages

users_collection = database["users"]
sessions_collection = database["sessions"]


# Maximum number of Q&A exchanges inside one storage session
MAX_EXCHANGES_PER_SESSION = 100


# ============================================================
# General User Functions
# ============================================================

def get_or_create_user(
    platform,
    platform_user_id,
    name=None
):
    """
    Find an existing platform user or create a new user.

    Mainly used for platforms such as Telegram.

    platform_user_id examples:
        Website  -> Website account ID
        Telegram -> Telegram user ID
    """

    platform_user_id = str(platform_user_id)

    user = users_collection.find_one(
        {
            "platform": platform,
            "platform_user_id": platform_user_id
        }
    )

    if user:
        return user["user_id"]

    user_id = str(uuid.uuid4())

    users_collection.insert_one(
        {
            "user_id": user_id,
            "platform": platform,
            "platform_user_id": platform_user_id,
            "name": name,
            "created_at": datetime.now(timezone.utc)
        }
    )

    return user_id


# ============================================================
# Website Authentication Functions
# ============================================================

def normalize_email(email: str | None) -> str | None:
    """Normalize an email address before saving or searching."""

    if not email:
        return None

    email = email.strip().lower()

    if not email:
        return None

    return email


def normalize_phone(phone: str | None) -> str | None:
    """
    Convert Saudi mobile numbers to +9665XXXXXXXX.

    Supported examples:
        0501234567
        966501234567
        +966501234567
    """

    if not phone:
        return None

    phone = re.sub(r"[\s-]", "", phone)

    if phone.startswith("05"):
        phone = "+966" + phone[1:]

    elif phone.startswith("9665"):
        phone = "+" + phone

    if not re.fullmatch(r"\+9665\d{8}", phone):
        raise ValueError("Invalid Saudi phone number.")

    return phone


def create_website_user(
    name: str,
    password: str,
    email: str | None = None,
    phone: str | None = None
):
    """
    Create a Website account.

    At least one of email or phone is required.
    Passwords are stored as hashes.
    """

    name = name.strip()
    email = normalize_email(email)
    phone = normalize_phone(phone)

    if not name:
        raise ValueError("Name is required.")

    if not email and not phone:
        raise ValueError("Email or phone is required.")

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    conditions = []

    if email:
        conditions.append({"email": email})

    if phone:
        conditions.append({"phone": phone})

    existing_user = users_collection.find_one(
        {
            "platform": "website",
            "$or": conditions
        }
    )

    if existing_user:
        raise ValueError(
            "Email or phone is already registered."
        )

    user_id = str(uuid.uuid4())

    user = {
        "user_id": user_id,
        "platform": "website",
        "platform_user_id": user_id,
        "name": name,
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc)
    }

    try:
        users_collection.insert_one(user)

    except DuplicateKeyError:
        raise ValueError(
            "Email or phone is already registered."
        )

    return user_id


def find_website_user(identifier: str):
    """
    Find a Website account using an email or Saudi phone number.
    """

    identifier = identifier.strip()

    if "@" in identifier:
        email = normalize_email(identifier)

        return users_collection.find_one(
            {
                "platform": "website",
                "email": email
            }
        )

    try:
        phone = normalize_phone(identifier)

    except ValueError:
        return None

    return users_collection.find_one(
        {
            "platform": "website",
            "phone": phone
        }
    )


def authenticate_website_user(
    identifier: str,
    password: str
):
    """
    Authenticate a Website user.

    Return the user document when credentials are correct.
    Return None when authentication fails.
    """

    user = find_website_user(identifier)

    if not user:
        return None

    stored_hash = user.get("password_hash")

    if not stored_hash:
        return None

    if not verify_password(password, stored_hash):
        return None

    return user


# ============================================================
# MongoDB Indexes
# ============================================================

def create_user_indexes():
    """
    Create indexes used by Website and Telegram users.
    """

    users_collection.create_index(
        [
            ("platform", 1),
            ("platform_user_id", 1)
        ],
        unique=True,
        name="unique_platform_user"
    )

    users_collection.create_index(
        [
            ("platform", 1),
            ("email", 1)
        ],
        unique=True,
        partialFilterExpression={
            "platform": "website",
            "email": {"$type": "string"}
        },
        name="unique_website_email"
    )

    users_collection.create_index(
        [
            ("platform", 1),
            ("phone", 1)
        ],
        unique=True,
        partialFilterExpression={
            "platform": "website",
            "phone": {"$type": "string"}
        },
        name="unique_website_phone"
    )

    sessions_collection.create_index(
        [
            ("platform", 1),
            ("user_id", 1),
            ("updated_at", -1)
        ],
        name="user_sessions"
    )

    sessions_collection.create_index(
        [
            ("session_id", 1),
            ("user_id", 1)
        ],
        unique=True,
        name="unique_session"
    )

    # Helps Website history queries find chats inside storage sessions.
    sessions_collection.create_index(
        [
            ("platform", 1),
            ("user_id", 1),
            ("messages.chat_id", 1)
        ],
        name="website_chat_history"
    )


# ============================================================
# Session Functions
# ============================================================

def create_session(
    user_id,
    platform,
    platform_user_id=None
):
    """
    Create a new storage session.

    One storage session can contain up to 100 Q&A exchanges.

    Website:
        Different chat_id values may exist inside one session.

    Telegram:
        The original Telegram user ID is also stored.
    """

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    session = {
        "session_id": session_id,
        "user_id": str(user_id),
        "platform": platform,
        "count": 0,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }

    # Store the original Telegram ID for easier identification.
    if platform == "telegram" and platform_user_id is not None:
        session["platform_user_id"] = str(platform_user_id)

    sessions_collection.insert_one(session)

    return session_id


def get_active_session(
    user_id,
    platform
):
    """
    Get the latest storage session that still has space.

    Return None if:
        - No session exists.
        - The latest session reached 100 exchanges.
    """

    session = sessions_collection.find_one(
        {
            "user_id": str(user_id),
            "platform": platform
        },
        sort=[
            ("updated_at", -1)
        ]
    )

    if not session:
        return None

    if session.get("count", 0) >= MAX_EXCHANGES_PER_SESSION:
        return None

    return session


def get_or_create_session(
    user_id,
    platform,
    platform_user_id=None
):
    """
    Return the current storage session.

    If the current session reached 100 exchanges,
    automatically create a new one.
    """

    session = get_active_session(
        user_id=user_id,
        platform=platform
    )

    if session:
        return session["session_id"]

    return create_session(
        user_id=user_id,
        platform=platform,
        platform_user_id=platform_user_id
    )

# ============================================================
# Website Chat Functions
# ============================================================

def create_chat_id():
    """
    Generate a new Website chat ID.

    Creating a chat ID does NOT create a new MongoDB session.
    """

    return str(uuid.uuid4())


# ============================================================
# Save Exchange
# ============================================================

def save_exchange(
    session_id,
    user_id,
    question,
    answer,
    platform,
    chat_id=None
):
    """
    Save one complete question/answer exchange inside sessions.messages.

    Website:
        chat_id is required.

    Telegram:
        chat_id is not required.
    """

    if platform == "website" and not chat_id:
        raise ValueError(
            "chat_id is required for Website messages."
        )

    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    exchange = {
        "message_id": message_id,
        "question": question,
        "answer": answer,
        "created_at": now
    }

    # Only Website exchanges need chat_id.
    if platform == "website":
        exchange["chat_id"] = str(chat_id)

    # count < 100 is part of the update condition.
    # This prevents this session from accepting exchange 101.
    result = sessions_collection.update_one(
        {
            "session_id": str(session_id),
            "user_id": str(user_id),
            "platform": platform,
            "count": {
                "$lt": MAX_EXCHANGES_PER_SESSION
            }
        },
        {
            "$push": {
                "messages": exchange
            },
            "$inc": {
                "count": 1
            },
            "$set": {
                "updated_at": now
            }
        }
    )

    if result.modified_count == 0:
        raise ValueError(
            "Session does not exist or has reached its exchange limit."
        )

    return message_id

# ============================================================
# Get Recent Exchanges
# ============================================================

def get_last_exchanges(
    session_id,
    user_id,
    limit=5,
    chat_id=None
):
    """
    Get the latest conversation exchanges.

    Website:
        Get the latest exchanges from the same chat_id,
        even if the chat spans multiple storage sessions.

    Telegram:
        Get the latest exchanges for the same Telegram user,
        even if the conversation spans multiple storage sessions.
    """

    user_id = str(user_id)

    # ========================================================
    # Website
    # ========================================================

    if chat_id:
        chat_id = str(chat_id)

        sessions = sessions_collection.find(
            {
                "user_id": user_id,
                "platform": "website",
                "messages.chat_id": chat_id
            },
            {
                "_id": 0,
                "messages": 1
            }
        )

        exchanges = []

        # Collect messages from the requested Website chat only.
        for session in sessions:
            for message in session.get("messages", []):
                if message.get("chat_id") == chat_id:
                    exchanges.append(message)

        # Sort from oldest to newest.
        exchanges.sort(
            key=lambda message: message.get(
                "created_at",
                datetime.min.replace(tzinfo=timezone.utc)
            )
        )

        return exchanges[-limit:]

    # ========================================================
    # Telegram
    # ========================================================

    sessions = sessions_collection.find(
        {
            "user_id": user_id,
            "platform": "telegram"
        },
        {
            "_id": 0,
            "messages": 1
        }
    )

    exchanges = []

    # Collect the Telegram user's exchanges from all sessions.
    for session in sessions:
        exchanges.extend(
            session.get("messages", [])
        )

    # Sort from oldest to newest.
    exchanges.sort(
        key=lambda message: message.get(
            "created_at",
            datetime.min.replace(tzinfo=timezone.utc)
        )
    )

    return exchanges[-limit:]
# ============================================================
# Website Chat History
# ============================================================
def get_user_chats(
    user_id,
    limit=20
):
    """
    Get Website chat history.

    A single chat_id may exist across multiple storage sessions.
    The result contains one entry for each chat_id.
    """

    sessions = sessions_collection.find(
        {
            "user_id": str(user_id),
            "platform": "website",
            "messages.chat_id": {
                "$exists": True
            }
        },
        {
            "_id": 0,
            "messages": 1
        }
    )

    chats = {}

    for session in sessions:
        for message in session.get("messages", []):
            chat_id = message.get("chat_id")

            if not chat_id:
                continue

            created_at = message.get("created_at")

            if chat_id not in chats:
                chats[chat_id] = {
                    "chat_id": chat_id,
                    "title": message.get(
                        "question",
                        "محادثة جديدة"
                    ),
                    "created_at": created_at,
                    "updated_at": created_at
                }

            else:
                if (
                    created_at
                    and (
                        chats[chat_id]["updated_at"] is None
                        or created_at > chats[chat_id]["updated_at"]
                    )
                ):
                    chats[chat_id]["updated_at"] = created_at

    chat_list = list(chats.values())

    # Show the most recently updated chats first.
    chat_list.sort(
        key=lambda chat: chat["updated_at"]
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    return chat_list[:limit]

def get_chat_exchanges(
    chat_id,
    user_id
):
    """
    Get all exchanges for one Website chat.

    The chat may span multiple MongoDB storage sessions.
    """
    sessions = sessions_collection.find(
        {
            "user_id": str(user_id),
            "platform": "website",
            "messages.chat_id": str(chat_id)
        },
        {
            "_id": 0,
            "messages": 1
        }
    )
    exchanges = []

    for session in sessions:
        for message in session.get("messages", []):
            if message.get("chat_id") == str(chat_id):
                exchanges.append(message)

    exchanges.sort(
        key=lambda message: message.get(
            "created_at",
            datetime.min.replace(tzinfo=timezone.utc)
        )
    )
    return exchanges

def delete_chat(
    chat_id,
    user_id
):
    """
    Delete one Website chat.

    Only messages with the requested chat_id are removed.
    Storage sessions themselves are preserved.
    """
    now = datetime.now(timezone.utc)
    sessions = list(
        sessions_collection.find(
            {
                "user_id": str(user_id),
                "platform": "website",
                "messages.chat_id": str(chat_id)
            },
            {
                "_id": 1,
                "messages": 1
            }
        )
    )
    deleted_count = 0

    for session in sessions:
        messages = session.get("messages", [])

        removed = sum(
            1
            for message in messages
            if message.get("chat_id") == str(chat_id)
        )

        if removed == 0:
            continue

        result = sessions_collection.update_one(
            {
                "_id": session["_id"]
            },
            {
                "$pull": {
                    "messages": {
                        "chat_id": str(chat_id)
                    }
                } 
            }
        )
        if result.modified_count:
            deleted_count += removed

    return deleted_count > 0