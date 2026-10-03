"""File storage service for S3-compatible storage"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
from app.core.logging import logger


class StorageProvider(ABC):
    """Abstract base for storage providers"""
    
    @abstractmethod
    async def upload(
        self,
        bucket: str,
        key: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload a file and return metadata"""
        pass
    
    @abstractmethod
    async def download(
        self,
        bucket: str,
        key: str,
    ) -> BinaryIO:
        """Download a file"""
        pass
    
    @abstractmethod
    async def delete(
        self,
        bucket: str,
        key: str,
    ) -> Dict[str, Any]:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> Dict[str, Any]:
        """List objects in a bucket"""
        pass
    
    @abstractmethod
    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a presigned URL for temporary access"""
        pass


class S3StorageProvider(StorageProvider):
    """AWS S3 storage provider"""
    
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.endpoint_url = endpoint_url
    
    async def upload(
        self,
        bucket: str,
        key: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload a file to S3"""
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
            )
            
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            s3_client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
            
            logger.info(f"File uploaded to S3: s3://{bucket}/{key}")
            return {
                "status": "success",
                "bucket": bucket,
                "key": key,
                "url": f"s3://{bucket}/{key}",
                "provider": "s3",
            }
        
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "s3",
            }
    
    async def download(
        self,
        bucket: str,
        key: str,
    ) -> BinaryIO:
        """Download a file from S3"""
        try:
            import boto3
            from io import BytesIO
            
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
            )
            
            file_obj = BytesIO()
            s3_client.download_fileobj(bucket, key, file_obj)
            file_obj.seek(0)
            
            logger.info(f"File downloaded from S3: s3://{bucket}/{key}")
            return file_obj
        
        except Exception as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise
    
    async def delete(self, bucket: str, key: str) -> Dict[str, Any]:
        """Delete a file from S3"""
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
            )
            
            s3_client.delete_object(Bucket=bucket, Key=key)
            
            logger.info(f"File deleted from S3: s3://{bucket}/{key}")
            return {
                "status": "success",
                "bucket": bucket,
                "key": key,
                "provider": "s3",
            }
        
        except Exception as e:
            logger.error(f"Failed to delete from S3: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "s3",
            }
    
    async def list_objects(self, bucket: str, prefix: str = "") -> Dict[str, Any]:
        """List objects in S3 bucket"""
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
            )
            
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            objects = []
            if 'Contents' in response:
                objects = [
                    {
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "modified": obj['LastModified'].isoformat(),
                    }
                    for obj in response['Contents']
                ]
            
            return {
                "status": "success",
                "bucket": bucket,
                "prefix": prefix,
                "objects": objects,
                "count": len(objects),
                "provider": "s3",
            }
        
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "s3",
            }
    
    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get presigned URL for S3 object"""
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
            )
            
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in,
            )
            
            logger.info(f"Presigned URL generated for s3://{bucket}/{key}")
            return url
        
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise


class LocalFileStorageProvider(StorageProvider):
    """Local filesystem storage provider (for development)"""
    
    def __init__(self, base_path: str = "/tmp/nexora-storage"):
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)
    
    async def upload(
        self,
        bucket: str,
        key: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload a file to local filesystem"""
        try:
            import os
            
            bucket_path = os.path.join(self.base_path, bucket)
            os.makedirs(bucket_path, exist_ok=True)
            
            file_path = os.path.join(bucket_path, key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_obj.read())
            
            logger.info(f"File uploaded to local storage: {file_path}")
            return {
                "status": "success",
                "bucket": bucket,
                "key": key,
                "path": file_path,
                "provider": "local",
            }
        
        except Exception as e:
            logger.error(f"Failed to upload to local storage: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "local",
            }
    
    async def download(self, bucket: str, key: str) -> BinaryIO:
        """Download a file from local filesystem"""
        try:
            import os
            
            file_path = os.path.join(self.base_path, bucket, key)
            
            with open(file_path, 'rb') as f:
                return f
        
        except Exception as e:
            logger.error(f"Failed to download from local storage: {str(e)}")
            raise
    
    async def delete(self, bucket: str, key: str) -> Dict[str, Any]:
        """Delete a file from local filesystem"""
        try:
            import os
            
            file_path = os.path.join(self.base_path, bucket, key)
            os.remove(file_path)
            
            logger.info(f"File deleted from local storage: {file_path}")
            return {
                "status": "success",
                "bucket": bucket,
                "key": key,
                "provider": "local",
            }
        
        except Exception as e:
            logger.error(f"Failed to delete from local storage: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "local",
            }
    
    async def list_objects(self, bucket: str, prefix: str = "") -> Dict[str, Any]:
        """List objects in local filesystem"""
        try:
            import os
            
            bucket_path = os.path.join(self.base_path, bucket)
            objects = []
            
            if os.path.exists(bucket_path):
                for root, dirs, files in os.walk(bucket_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, bucket_path)
                        
                        if rel_path.startswith(prefix):
                            stat = os.stat(file_path)
                            objects.append({
                                "key": rel_path,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            })
            
            return {
                "status": "success",
                "bucket": bucket,
                "prefix": prefix,
                "objects": objects,
                "count": len(objects),
                "provider": "local",
            }
        
        except Exception as e:
            logger.error(f"Failed to list local storage: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "local",
            }
    
    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get local file URL (not truly presigned, but provides download link)"""
        # For local storage, we just return a path indicator
        # In production, use S3 or similar
        return f"/api/v1/files/download/{bucket}/{key}"


class FileStorageService:
    """High-level file storage service"""
    
    def __init__(self, provider: StorageProvider, default_bucket: str = "nexora-uploads"):
        self.provider = provider
        self.default_bucket = default_bucket
    
    async def upload(
        self,
        key: str,
        file_obj: BinaryIO,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload a file"""
        bucket = bucket or self.default_bucket
        return await self.provider.upload(bucket, key, file_obj, metadata)
    
    async def download(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> BinaryIO:
        """Download a file"""
        bucket = bucket or self.default_bucket
        return await self.provider.download(bucket, key)
    
    async def delete(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a file"""
        bucket = bucket or self.default_bucket
        return await self.provider.delete(bucket, key)
    
    async def list_objects(
        self,
        prefix: str = "",
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files with optional prefix"""
        bucket = bucket or self.default_bucket
        return await self.provider.list_objects(bucket, prefix)
    
    async def get_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        """Get a download URL for a file"""
        bucket = bucket or self.default_bucket
        return await self.provider.get_presigned_url(bucket, key, expires_in)
