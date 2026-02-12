"""
Authentication service.
"""
from sqlalchemy.orm import Session
from botocore.exceptions import ClientError
from app.aws import get_aws_client, CognitoIdentityProviderWrapper
from app.core.config import settings
from app.core.exceptions import EmailAlreadyExists, InvalidCredentials
from app.session import create_session, remove_session
from app.crud import user_crud
from app.schema.auth import UserRegister, UserLogin, LoginResponse, UserInfo
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
        # Initialize Cognito wrapper with AWS client
        self.cognito = CognitoIdentityProviderWrapper(
            cognito_client=get_aws_client('cognito-idp'),
            user_pool_id=settings.COGNITO_USER_POOL_ID,
            client_id=settings.COGNITO_CLIENT_ID,
            client_secret=settings.COGNITO_CLIENT_SECRET
        )

    def register_user(self, user_data: UserRegister) -> None:
        """Register a new user in Cognito and local DB."""
        # Check if user exists locally
        if user_crud.get_by_email(self.db, user_data.email):
            raise EmailAlreadyExists()

        try:
            # Register in Cognito FIRST
            cognito_response = self.cognito.sign_up(
                email=user_data.email,
                password=user_data.password
            )
            
            # Create local user record with cognito_username
            user_dict = user_data.model_dump(exclude={"password"})
            user_dict["cognito_username"] = cognito_response['username']
            
            user = user_crud.create_from_dict(self.db, obj_in=user_dict)
            logger.info(f"User registered: {user.email}, Cognito Username: {cognito_response['username']}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise EmailAlreadyExists()
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def login(self, login_data: UserLogin) -> LoginResponse:
        """Authenticate user via Cognito, create session, return tokens."""
        try:
            # Authenticate with Cognito
            tokens = self.cognito.initiate_auth(
                email=login_data.email,
                password=login_data.password
            )
            
            # Get local user record
            user = user_crud.get_by_email(self.db, login_data.email)
            if not user:
                raise InvalidCredentials(message="User not found in local database")
            
            # Store IdToken in session with user data
            id_token = tokens['id_token']
            user_data = {
                "user_id": str(user.id),
                "email": user.email,
                "is_active": user.is_active,
                "access_token": tokens['access_token'],  # Store for sign_out
            }
            create_session(id_token, user_data)

            logger.info(f"User logged in: {user.email}")

            return LoginResponse(
                message="Login successful",
                access_token=id_token,  # Return IdToken as access_token
                user=UserInfo(id=str(user.id), email=user.email, is_active=user.is_active)
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
                raise InvalidCredentials()
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def logout(self, token: str, user_data: dict) -> bool:
        """Sign out from Cognito and remove local session."""
        try:
            # Sign out from Cognito using access_token
            access_token = user_data.get('access_token')
            if access_token:
                self.cognito.global_sign_out(access_token)
        except ClientError as e:
            logger.warning(f"Cognito sign out failed: {e.response['Error']['Message']}")
        
        # Always remove local session
        return remove_session(token)

    def verify_email(self, email: str, code: str) -> None:
        """Confirm user signup with verification code."""
        # Get cognito_username from DB
        user = user_crud.get_by_email(self.db, email)
        if not user:
            raise InvalidCredentials(message="User not found")
        
        try:
            self.cognito.confirm_sign_up(user.cognito_username, code)
            logger.info(f"Email verified: {email}")
        except ClientError as e:
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def resend_verification_code(self, email: str) -> None:
        """Resend verification code to user email."""
        # Get cognito_username from DB
        user = user_crud.get_by_email(self.db, email)
        if not user:
            raise InvalidCredentials(message="User not found")
        
        try:
            self.cognito.resend_confirmation_code(user.cognito_username)
            logger.info(f"Verification code resent to: {email}")
        except ClientError as e:
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def forgot_password(self, email: str) -> None:
        """Initiate forgot password flow - sends reset code to email."""
        # Get cognito_username from DB
        user = user_crud.get_by_email(self.db, email)
        if not user:
            raise InvalidCredentials(message="User not found")
        
        try:
            self.cognito.forgot_password(user.cognito_username)
            logger.info(f"Password reset initiated for: {email}")
        except ClientError as e:
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def reset_password(self, email: str, code: str, new_password: str) -> None:
        """Confirm forgot password with code and set new password."""
        # Get cognito_username from DB
        user = user_crud.get_by_email(self.db, email)
        if not user:
            raise InvalidCredentials(message="User not found")
        
        try:
            self.cognito.confirm_forgot_password(user.cognito_username, code, new_password)
            logger.info(f"Password reset completed for: {email}")
        except ClientError as e:
            raise InvalidCredentials(message=e.response['Error']['Message'])

    def change_password(self, access_token: str, current_password: str, new_password: str) -> None:
        """Change password for logged-in user."""
        try:
            self.cognito.change_password(access_token, current_password, new_password)
            logger.info("Password changed successfully")
        except ClientError as e:
            raise InvalidCredentials(message=e.response['Error']['Message'])
