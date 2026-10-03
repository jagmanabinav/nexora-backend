"""Background job queue service for async task processing"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import json
from app.core.logging import logger


class JobProvider(ABC):
    """Abstract base for job queue providers"""
    
    @abstractmethod
    async def enqueue(
        self,
        job_name: str,
        job_id: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """Enqueue a job for processing"""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a scheduled job"""
        pass
    
    @abstractmethod
    async def retry_job(self, job_id: str) -> Dict[str, Any]:
        """Retry a failed job"""
        pass


class RedisJobProvider(JobProvider):
    """Redis-based job queue provider (using RQ or similar)"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.jobs_store = {}  # In-memory store for demo (use Redis in production)
    
    async def enqueue(
        self,
        job_name: str,
        job_id: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """Enqueue a job"""
        try:
            job_data = {
                "id": job_id,
                "name": job_name,
                "payload": payload,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "scheduled_at": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat(),
                "retry_count": 0,
                "max_retries": retry_count,
            }
            
            # Store in Redis (or in-memory for demo)
            self.jobs_store[job_id] = job_data
            
            logger.info(f"Job enqueued: {job_name} (ID: {job_id})")
            return {
                "status": "enqueued",
                "job_id": job_id,
                "job_name": job_name,
            }
        
        except Exception as e:
            logger.error(f"Failed to enqueue job: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
            }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        if job_id in self.jobs_store:
            return self.jobs_store[job_id]
        return {
            "status": "not_found",
            "job_id": job_id,
        }
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a job"""
        if job_id in self.jobs_store:
            job = self.jobs_store[job_id]
            job["status"] = "cancelled"
            logger.info(f"Job cancelled: {job_id}")
            return {
                "status": "success",
                "job_id": job_id,
                "message": "Job cancelled",
            }
        return {
            "status": "failed",
            "error": f"Job {job_id} not found",
        }
    
    async def retry_job(self, job_id: str) -> Dict[str, Any]:
        """Retry a failed job"""
        if job_id in self.jobs_store:
            job = self.jobs_store[job_id]
            if job["retry_count"] < job["max_retries"]:
                job["retry_count"] += 1
                job["status"] = "pending"
                logger.info(f"Job retried: {job_id} (attempt {job['retry_count']})")
                return {
                    "status": "success",
                    "job_id": job_id,
                    "retry_count": job["retry_count"],
                }
            else:
                return {
                    "status": "failed",
                    "error": "Max retries exceeded",
                }
        return {
            "status": "failed",
            "error": f"Job {job_id} not found",
        }


class JobQueueService:
    """High-level job queue service"""
    
    def __init__(self, provider: JobProvider):
        self.provider = provider
        self.job_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, job_name: str, handler: Callable) -> None:
        """Register a job handler"""
        self.job_handlers[job_name] = handler
    
    async def enqueue(
        self,
        job_name: str,
        job_id: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """Enqueue a job"""
        return await self.provider.enqueue(
            job_name=job_name,
            job_id=job_id,
            payload=payload,
            delay_seconds=delay_seconds,
            retry_count=retry_count,
        )
    
    async def get_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        return await self.provider.get_job_status(job_id)
    
    async def cancel(self, job_id: str) -> Dict[str, Any]:
        """Cancel a job"""
        return await self.provider.cancel_job(job_id)
    
    async def retry(self, job_id: str) -> Dict[str, Any]:
        """Retry a job"""
        return await self.provider.retry_job(job_id)
    
    # Common job enqueue methods
    async def send_invoice_email(
        self,
        job_id: str,
        invoice_id: str,
        tenant_id: str,
        email: str,
    ) -> Dict[str, Any]:
        """Queue an invoice email send job"""
        return await self.enqueue(
            job_name="send_invoice_email",
            job_id=job_id,
            payload={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "email": email,
            },
        )
    
    async def send_payment_confirmation(
        self,
        job_id: str,
        tenant_id: str,
        invoice_id: str,
        amount: float,
        email: str,
    ) -> Dict[str, Any]:
        """Queue a payment confirmation email"""
        return await self.enqueue(
            job_name="send_payment_confirmation",
            job_id=job_id,
            payload={
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "amount": amount,
                "email": email,
            },
        )
    
    async def send_trial_expiration_warning(
        self,
        job_id: str,
        tenant_id: str,
        days_remaining: int,
        email: str,
    ) -> Dict[str, Any]:
        """Queue a trial expiration warning"""
        return await self.enqueue(
            job_name="send_trial_expiration_warning",
            job_id=job_id,
            payload={
                "tenant_id": tenant_id,
                "days_remaining": days_remaining,
                "email": email,
            },
            delay_seconds=0,  # Send immediately
        )
    
    async def cleanup_old_files(
        self,
        job_id: str,
        older_than_days: int = 30,
    ) -> Dict[str, Any]:
        """Queue a cleanup job for old files"""
        return await self.enqueue(
            job_name="cleanup_old_files",
            job_id=job_id,
            payload={
                "older_than_days": older_than_days,
            },
            delay_seconds=3600,  # Run in 1 hour
        )
    
    async def generate_usage_report(
        self,
        job_id: str,
        tenant_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Queue a usage report generation"""
        return await self.enqueue(
            job_name="generate_usage_report",
            job_id=job_id,
            payload={
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
