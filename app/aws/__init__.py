"""
AWS integrations layer.
"""
from app.aws.client import get_aws_client
from app.aws.cognito import CognitoIdentityProviderWrapper
from app.aws.secrets import get_secret

__all__ = [
    "get_aws_client",
    "CognitoIdentityProviderWrapper",
    "get_secret",
]
