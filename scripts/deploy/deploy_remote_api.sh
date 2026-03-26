#!/bin/bash
echo "Uploading remote_api.py to VM2..."
gcloud compute scp /home/terraria/servers/web_interface/remote_api.py root@instance-20260220-174959:/home/terraria/servers/remote_api.py --zone="asia-east1-c" --project="project-ad2eecb1-dd0f-4cf4-b1a"
echo "Restarting remote_agent service on VM2..."
gcloud compute ssh root@instance-20260220-174959 --zone="asia-east1-c" --project="project-ad2eecb1-dd0f-4cf4-b1a" --command="systemctl restart mc_agent && systemctl status mc_agent --no-pager"
echo "Deployment completed!"
