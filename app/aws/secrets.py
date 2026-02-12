"""
AWS Secrets Manager wrapper.
Based on AWS SDK examples.
"""
import json
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class GetSecretWrapper:
    """Encapsulates AWS Secrets Manager actions."""
    
    def __init__(self, secretsmanager_client):
        self.client = secretsmanager_client

    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve individual secrets from AWS Secrets Manager.

        Args:
            secret_name: The name of the secret to fetch

        Returns:
            Secret string value

        Raises:
            ClientError: If secret retrieval fails
        """
        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=secret_name
            )
            logger.info("Secret retrieved successfully.")
            return get_secret_value_response["SecretString"]
        except self.client.exceptions.ResourceNotFoundException:
            msg = f"The requested secret {secret_name} was not found."
            logger.error(msg)
            raise
        except Exception as e:
            logger.error(f"An unknown error occurred: {str(e)}.")
            raise


def get_secret(secret_name: str, region_name: str = "us-east-1") -> dict:
    """
    Get secret from AWS Secrets Manager and parse as JSON.
    
    Args:
        secret_name: Name/path of the secret
        region_name: AWS region
        
    Returns:
        Dict containing the secret key-value pairs
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    wrapper = GetSecretWrapper(client)
    secret_string = wrapper.get_secret(secret_name)
    
    # Parse JSON string to dict
    return json.loads(secret_string)
