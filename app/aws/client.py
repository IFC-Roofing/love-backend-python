"""
AWS client factory - centralized boto3 client creation.
"""
import boto3
from typing import Optional
from app.core.config import settings


def get_aws_client(service_name: str, region_name: Optional[str] = None):
    """
    Create and return a boto3 client for any AWS service.
    
    Args:
        service_name: AWS service name (e.g., 'cognito-idp', 's3', 'dynamodb', 'ses')
        region_name: AWS region name (defaults to AWS_REGION from settings)
        
    Returns:
        Boto3 client for the specified service
        
    Examples:
        >>> cognito_client = get_aws_client('cognito-idp')
        >>> s3_client = get_aws_client('s3', region_name='us-west-2')
        >>> ses_client = get_aws_client('ses')
    """
    region = region_name or settings.COGNITO_REGION
    return boto3.client(service_name, region_name=region)
