import logging
import time
from typing import Optional
from googleapiclient import discovery
from google.auth import compute_engine

logger = logging.getLogger('hihi_bot')

class GCPManager:
    """
    Manages GCP Compute Engine instances using Google API Client Library.
    Using discovery-based approach for zero-external-CLI dependency.
    """
    def __init__(self, project_id: str, zone: str):
        self.project_id = project_id
        self.zone = zone
        # 使用預設憑證 (在 GCP VM 內會自動透過 Metadata Server 取得)
        self.compute = discovery.build('compute', 'v1')

    def start_instance(self, instance_name: str) -> bool:
        """Starts a specific VM instance."""
        try:
            logger.info(f"Attempting to start GCP instance: {instance_name}")
            request = self.compute.instances().start(
                project=self.project_id, zone=self.zone, instance=instance_name)
            request.execute()
            logger.info(f"Successfully sent start request for {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start instance {instance_name}. Error: {e}")
            return False

    def stop_instance(self, instance_name: str) -> bool:
        """Stops a specific VM instance."""
        try:
            logger.info(f"Attempting to stop GCP instance: {instance_name}")
            request = self.compute.instances().stop(
                project=self.project_id, zone=self.zone, instance=instance_name)
            request.execute()
            logger.info(f"Successfully sent stop request for {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop instance {instance_name}. Error: {e}")
            return False

    def get_instance_status(self, instance_name: str) -> Optional[str]:
        """Gets the status (e.g., RUNNING, TERMINATED) of a VM instance."""
        try:
            request = self.compute.instances().get(
                project=self.project_id, zone=self.zone, instance=instance_name)
            response = request.execute()
            return response.get('status')
        except Exception as e:
            logger.error(f"Failed to get status for {instance_name}. Error: {e}")
            return None
    
    def get_instance_ip(self, instance_name: str) -> Optional[str]:
         """Gets the internal IP of a VM instance."""
         try:
             request = self.compute.instances().get(
                 project=self.project_id, zone=self.zone, instance=instance_name)
             response = request.execute()
             # 取第一個網路介面的內部 IP
             return response['networkInterfaces'][0]['networkIP']
         except Exception as e:
             logger.error(f"Failed to get IP for {instance_name}. Error: {e}")
             return None

    def get_instance_public_ip(self, instance_name: str) -> Optional[str]:
         """Gets the external public IP of a VM instance (For Discord Players)."""
         try:
             request = self.compute.instances().get(
                 project=self.project_id, zone=self.zone, instance=instance_name)
             response = request.execute()
             # 取第一個網路介面第一個 Access Config 的外部 IP
             return response['networkInterfaces'][0]['accessConfigs'][0]['natIP']
         except Exception as e:
             logger.error(f"Failed to get Public IP for {instance_name}. Error: {e}")
             return None
