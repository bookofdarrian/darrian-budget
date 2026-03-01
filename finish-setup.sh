#!/bin/bash
# Run this on the Proxmox host once apt is free
# ssh root@100.117.1.50 "bash /root/finish-setup.sh"
apt-get update -qq && apt-get install -y fail2ban unattended-upgrades
systemctl enable fail2ban && systemctl restart fail2ban
systemctl is-active fail2ban && echo "fail2ban: DONE"
echo "All post-install steps complete."
