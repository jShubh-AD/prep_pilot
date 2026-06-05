import boto3
from mypy_boto3_s3 import S3Client
from app.core.settings import settings

class S3Service:
    def __init__(self):
        self.client: S3Client | None = None
        self.bucket_name = settings.AWS_S3_BUCKET

    def initialize(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key= settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION
        )
        
    def health_check(self):
        return self.client.head_bucket(
            Bucket=self.bucket_name
        )
    
    def upload_file(self,file_obj, key: str):
        self.client.upload_fileobj(
            Fileobj=file_obj,
            Key=key,
            Bucket=self.bucket_name
        )
    
        
s3_service  = S3Service()