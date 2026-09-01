import logging
import re
from typing import Optional
from app.extensions import db
from app.models import User

logger = logging.getLogger(__name__)

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class AuthError(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _validate_email(email: str) -> bool:
    """Validate email format."""
    return EMAIL_REGEX.match(email) is not None


def register_user(name: Optional[str], email: Optional[str], password: Optional[str]) -> User:
    """
    Register a new user with the provided credentials.

    Args:
        name: User's full name
        email: User's email address
        password: User's password

    Returns:
        User: The newly created user object

    Raises:
        AuthError: If validation fails or user already exists
    """
    if not name or not name.strip():
        logger.warning("Registration attempt with empty name")
        raise AuthError("Name is required", 400)

    if not email or not email.strip():
        logger.warning("Registration attempt with empty email")
        raise AuthError("Email is required", 400)

    if not password or len(password) < 8:
        logger.warning("Registration attempt with weak password")
        raise AuthError("Password must be at least 8 characters", 400)

    if not _validate_email(email):
        logger.warning(f"Registration attempt with invalid email format: {email}")
        raise AuthError("Invalid email format", 400)

    existing_user = User.query.filter_by(email=email.lower()).first()
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {email}")
        raise AuthError("Email already registered", 409)

    user = User(name=name.strip(), email=email.lower())
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        logger.info(f"User registered successfully: {user.email}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to register user: {str(e)}", exc_info=True)
        raise AuthError("Failed to create user account", 500)

    return user


def authenticate_user(email: Optional[str], password: Optional[str]) -> User:
    """
    Authenticate a user with email and password.

    Args:
        email: User's email address
        password: User's password

    Returns:
        User: The authenticated user object

    Raises:
        AuthError: If credentials are invalid or the account is inactive
    """
    if not email or not email.strip():
        logger.warning("Login attempt with empty email")
        raise AuthError("Email is required", 400)

    if not password:
        logger.warning("Login attempt with empty password")
        raise AuthError("Password is required", 400)

    user = User.query.filter_by(email=email.lower()).first()
    if not user or not user.check_password(password):
        logger.warning(f"Failed login attempt for: {email}")
        raise AuthError("Invalid email or password", 401)

    if not user.is_active:
        logger.warning(f"Login attempt for deactivated account: {email}")
        raise AuthError("This account has been deactivated", 403)

    logger.info(f"User logged in successfully: {email}")
    return user