import subprocess
import json
import logging
from typing import Optional

logger = logging.getLogger('hihi_bot')

class GCPManager:
    """
    Manages GCP Compute Engine instances using gcloud CLI wrapped in subprocess.
    This avoids complex OAuth flows since the VM already has the correct IAM roles.
    """
    def __init__(self, project_id: str, zone: str):
        self.project_id = project_id
        self.zone = zone

    def start_instance(self, instance_name: str) -> bool:
        """Starts a specific VM instance."""
        try:
            logger.info(f"Attempting to start GCP instance: {instance_name}")
            cmd = [
                'gcloud', 'compute', 'instances', 'start', instance_name,
                f'--project={self.project_id}',
                f'--zone={self.zone}',
                '--quiet'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully started instance {instance_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start instance {instance_name}. Error: {e.stderr}")
            return False

    def stop_instance(self, instance_name: str) -> bool:
        """Stops a specific VM instance."""
        try:
            logger.info(f"Attempting to stop GCP instance: {instance_name}")
            cmd = [
                'gcloud', 'compute', 'instances', 'stop', instance_name,
                f'--project={self.project_id}',
                f'--zone={self.zone}',
                '--quiet'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully stopped instance {instance_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop instance {instance_name}. Error: {e.stderr}")
            return False

    def get_instance_status(self, instance_name: str) -> Optional[str]:
        """Gets the status (e.g., RUNNING, TERMINATED) of a VM instance."""
        try:
            cmd = [
                'gcloud', 'compute', 'instances', 'describe', instance_name,
                f'--project={self.project_id}',
                f'--zone={self.zone}',
                '--format=value(status)'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            status = result.stdout.strip()
            return status
        except subprocess.TimeoutExpired as e:
            logger.error(f"Timeout getting status for {instance_name}")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get status for {instance_name}. Error: {e.stderr}")
            return None
    
    def get_instance_ip(self, instance_name: str) -> Optional[str]:
         """Gets the internal IP of a VM instance."""
         try:
             cmd = [
                 'gcloud', 'compute', 'instances', 'describe', instance_name,
                 f'--project={self.project_id}',
                 f'--zone={self.zone}',
                 '--format=value(networkInterfaces[0].networkIP)'
             ]
             result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
             ip = result.stdout.strip()
             return ip
         except subprocess.TimeoutExpired as e:
             logger.error(f"Timeout getting IP for {instance_name}")
             return None
         except subprocess.CalledProcessError as e:
             logger.error(f"Failed to get IP for {instance_name}. Error: {e.stderr}")
             return None

    def get_instance_public_ip(self, instance_name: str) -> Optional[str]:
         """Gets the external public IP of a VM instance (For Discord Players)."""
         try:
             cmd = [
                 'gcloud', 'compute', 'instances', 'describe', instance_name,
                 f'--project={self.project_id}',
                 f'--zone={self.zone}',
                 '--format=value(networkInterfaces[0].accessConfigs[0].natIP)'
             ]
             result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
             ip = result.stdout.strip()
             return ip
         except subprocess.TimeoutExpired as e:
             logger.error(f"Timeout getting Public IP for {instance_name}")
             return None
         except subprocess.CalledProcessError as e:
             logger.error(f"Failed to get Public IP for {instance_name}. Error: {e.stderr}")
             return None
