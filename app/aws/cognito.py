"""
AWS Cognito wrapper class using boto3.
Based on AWS SDK examples: https://github.com/awsdocs/aws-doc-sdk-examples
"""
import base64
import hashlib
import hmac
import uuid
from typing import Dict, Any
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class CognitoIdentityProviderWrapper:
    """
    Encapsulates Amazon Cognito Identity Provider actions.
    """

    def __init__(
        self,
        cognito_client,
        user_pool_id: str,
        client_id: str,
        client_secret: str = None
    ):
        """
        Initialize the Cognito wrapper.

        Args:
            cognito_client: A Boto3 Cognito Identity Provider client
            user_pool_id: The ID of the Cognito user pool
            client_id: The ID of the client application
            client_secret: The client secret (if configured)
        """
        self.cognito_client = cognito_client
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret

    def _secret_hash(self, username: str) -> str:
        """
        Calculate SECRET_HASH for Cognito requests.
        Required when app client has a secret configured.

        Args:
            username: The username

        Returns:
            Base64 encoded secret hash
        """
        if not self.client_secret:
            return None
            
        message = bytes(username + self.client_id, 'utf-8')
        key = bytes(self.client_secret, 'utf-8')
        secret_hash = base64.b64encode(
            hmac.new(key, message, digestmod=hashlib.sha256).digest()
        ).decode()
        
        logger.debug(f"Generated SECRET_HASH for user: {username}")
        return secret_hash

    def sign_up(self, email: str, password: str, **user_attributes) -> Dict[str, Any]:
        """
        Register a new user in the user pool.
        Uses a UUID as Username since pool is configured for email alias.

        Args:
            email: User's email address
            password: User's password
            **user_attributes: Additional user attributes (given_name, family_name, etc.)

        Returns:
            Dict containing UserSub and confirmation status

        Raises:
            ClientError: If sign up fails
        """
        # Generate unique username (pool uses email as alias, not username)
        username = str(uuid.uuid4())
        
        attributes = [{'Name': 'email', 'Value': email}]
        
        for key, value in user_attributes.items():
            attributes.append({'Name': key, 'Value': str(value)})

        try:
            kwargs = {
                'ClientId': self.client_id,
                'Username': username,
                'Password': password,
                'UserAttributes': attributes
            }
            
            if self.client_secret:
                kwargs['SecretHash'] = self._secret_hash(username)
            
            response = self.cognito_client.sign_up(**kwargs)
            logger.info(f"User signed up: {email}")
            return {
                'user_sub': response['UserSub'],
                'username': username,
                'user_confirmed': response['UserConfirmed'],
                'code_delivery_details': response.get('CodeDeliveryDetails')
            }
        except ClientError as e:
            logger.error(f"Sign up failed for {email}: {e.response['Error']['Message']}")
            raise

    def initiate_auth(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user using admin auth flow.
        Uses ADMIN_USER_PASSWORD_AUTH because pool uses email alias + client secret.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dict containing authentication tokens

        Raises:
            ClientError: If authentication fails
        """
        try:
            kwargs = {
                'UserPoolId': self.user_pool_id,
                'ClientId': self.client_id,
                'AuthFlow': 'ADMIN_USER_PASSWORD_AUTH',
                'AuthParameters': {
                    'USERNAME': email,
                    'PASSWORD': password
                }
            }
            
            if self.client_secret:
                kwargs['AuthParameters']['SECRET_HASH'] = self._secret_hash(email)
            
            response = self.cognito_client.admin_initiate_auth(**kwargs)

            auth_result = response['AuthenticationResult']
            logger.info(f"User authenticated: {email}")

            return {
                'id_token': auth_result['IdToken'],
                'access_token': auth_result['AccessToken'],
                'refresh_token': auth_result['RefreshToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType']
            }
        except ClientError as e:
            logger.error(f"Authentication failed for {email}: {e.response['Error']['Message']}")
            raise

    def global_sign_out(self, access_token: str) -> bool:
        """
        Sign out user globally (invalidate all tokens).

        Args:
            access_token: User's access token

        Returns:
            True if successful

        Raises:
            ClientError: If sign out fails
        """
        try:
            self.cognito_client.global_sign_out(AccessToken=access_token)
            logger.info("User signed out globally")
            return True
        except ClientError as e:
            logger.error(f"Global sign out failed: {e.response['Error']['Message']}")
            raise

    def confirm_sign_up(self, username: str, confirmation_code: str) -> bool:
        """
        Confirm user registration with verification code.

        Args:
            username: Cognito username (UUID)
            confirmation_code: Verification code sent to user

        Returns:
            True if successful

        Raises:
            ClientError: If confirmation fails
        """
        try:
            kwargs = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code
            }
            
            # Add SECRET_HASH if client has secret
            if self.client_secret:
                kwargs['SecretHash'] = self._secret_hash(username)
            
            self.cognito_client.confirm_sign_up(**kwargs)
            logger.info(f"User confirmed: {username}")
            return True
        except ClientError as e:
            logger.error(f"Confirmation failed for {username}: {e.response['Error']['Message']}")
            raise

    def resend_confirmation_code(self, username: str) -> Dict[str, Any]:
        """
        Resend confirmation code to user.

        Args:
            username: Cognito username (UUID)

        Returns:
            Dict with code delivery details

        Raises:
            ClientError: If resend fails
        """
        try:
            kwargs = {
                'ClientId': self.client_id,
                'Username': username
            }
            
            # Add SECRET_HASH if client has secret
            if self.client_secret:
                kwargs['SecretHash'] = self._secret_hash(username)
            
            response = self.cognito_client.resend_confirmation_code(**kwargs)
            logger.info(f"Confirmation code resent to: {username}")
            return response.get('CodeDeliveryDetails', {})
        except ClientError as e:
            logger.error(f"Resend code failed for {username}: {e.response['Error']['Message']}")
            raise

    def forgot_password(self, username: str) -> Dict[str, Any]:
        """
        Initiate forgot password flow.

        Args:
            username: Cognito username (UUID)

        Returns:
            Dict with code delivery details

        Raises:
            ClientError: If request fails
        """
        try:
            kwargs = {
                'ClientId': self.client_id,
                'Username': username
            }
            
            # Add SECRET_HASH if client has secret
            if self.client_secret:
                kwargs['SecretHash'] = self._secret_hash(username)
            
            response = self.cognito_client.forgot_password(**kwargs)
            logger.info(f"Password reset initiated for: {username}")
            return response.get('CodeDeliveryDetails', {})
        except ClientError as e:
            logger.error(f"Forgot password failed for {username}: {e.response['Error']['Message']}")
            raise

    def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str
    ) -> bool:
        """
        Confirm forgot password with code and set new password.

        Args:
            username: Cognito username (UUID)
            confirmation_code: Verification code sent to user
            new_password: New password to set

        Returns:
            True if successful

        Raises:
            ClientError: If confirmation fails
        """
        try:
            kwargs = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code,
                'Password': new_password
            }
            
            # Add SECRET_HASH if client has secret
            if self.client_secret:
                kwargs['SecretHash'] = self._secret_hash(username)
            
            self.cognito_client.confirm_forgot_password(**kwargs)
            logger.info(f"Password reset confirmed for: {username}")
            return True
        except ClientError as e:
            logger.error(f"Password reset confirmation failed for {username}: {e.response['Error']['Message']}")
            raise

    def get_user(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from access token.

        Args:
            access_token: User's access token

        Returns:
            Dict with username and user attributes

        Raises:
            ClientError: If request fails
        """
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)

            # Convert attributes list to dict
            attributes = {
                attr['Name']: attr['Value']
                for attr in response['UserAttributes']
            }

            return {
                'username': response['Username'],
                'attributes': attributes
            }
        except ClientError as e:
            logger.error(f"Get user failed: {e.response['Error']['Message']}")
            raise

    def admin_get_user(self, username: str) -> Dict[str, Any]:
        """
        Get user information (admin operation).

        Args:
            username: Username to look up

        Returns:
            Dict with user information

        Raises:
            ClientError: If request fails
        """
        try:
            response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )

            attributes = {
                attr['Name']: attr['Value']
                for attr in response['UserAttributes']
            }

            return {
                'username': response['Username'],
                'user_status': response['UserStatus'],
                'enabled': response['Enabled'],
                'attributes': attributes,
                'user_create_date': response.get('UserCreateDate'),
                'user_last_modified_date': response.get('UserLastModifiedDate')
            }
        except ClientError as e:
            logger.error(f"Admin get user failed for {username}: {e.response['Error']['Message']}")
            raise

    def change_password(
        self,
        access_token: str,
        previous_password: str,
        proposed_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            access_token: User's access token
            previous_password: Current password
            proposed_password: New password

        Returns:
            True if successful

        Raises:
            ClientError: If password change fails
        """
        try:
            self.cognito_client.change_password(
                AccessToken=access_token,
                PreviousPassword=previous_password,
                ProposedPassword=proposed_password
            )
            logger.info("Password changed successfully")
            return True
        except ClientError as e:
            logger.error(f"Password change failed: {e.response['Error']['Message']}")
            raise

    def refresh_tokens(self, refresh_token: str, username: str) -> Dict[str, Any]:
        """
        Refresh authentication tokens.

        Args:
            refresh_token: Refresh token
            username: Username (required for SECRET_HASH calculation)

        Returns:
            Dict with new tokens

        Raises:
            ClientError: If refresh fails
        """
        try:
            kwargs = {
                'ClientId': self.client_id,
                'AuthFlow': 'REFRESH_TOKEN_AUTH',
                'AuthParameters': {
                    'REFRESH_TOKEN': refresh_token
                }
            }
            
            # Add SECRET_HASH if client has secret
            if self.client_secret:
                kwargs['AuthParameters']['SECRET_HASH'] = self._secret_hash(username)
            
            response = self.cognito_client.initiate_auth(**kwargs)

            auth_result = response['AuthenticationResult']
            logger.info("Tokens refreshed successfully")

            return {
                'id_token': auth_result['IdToken'],
                'access_token': auth_result['AccessToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType']
            }
        except ClientError as e:
            logger.error(f"Token refresh failed: {e.response['Error']['Message']}")
            raise

