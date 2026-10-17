#!/bin/bash
# ==============================================================================
# Reddit Intelligence Platform - Oracle Cloud Infrastructure (OCI) Host Setup
# Target Instance: VM.Standard.E2.1.Micro (1 OCPU, 1 GB RAM, Always Free Tier)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "  Configuring OCI Micro Instance (1 GB RAM Optimization)  "
echo "=========================================================="

# 1. Require root / sudo
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run this script with sudo: sudo bash scripts/oci_setup.sh"
  exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"

# 2. Configure 4 GB Swap File
echo "[1/5] Configuring 4 GB swap space..."
if [ ! -f /swapfile ]; then
  echo "    Creating /swapfile (4 GB)..."
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "    Swap created and activated successfully."
else
  echo "    /swapfile already exists. Ensuring swap is active..."
  swapon /swapfile 2>/dev/null || true
fi

# 3. Kernel Memory Tuning for 1 GB RAM
echo "[2/5] Tuning kernel memory and swappiness parameters..."
cat << 'EOF' > /etc/sysctl.d/99-oci-micro.conf
# Reddit Intelligence Platform - OCI Micro Tuning
# vm.swappiness=20: Prefer physical RAM while keeping swap ready for spike allocations
vm.swappiness=20
# vm.vfs_cache_pressure=50: Retain filesystem directory & inode caches
vm.vfs_cache_pressure=50
# vm.overcommit_memory=1: Support Redis memory allocation without crash
vm.overcommit_memory=1
EOF

sysctl --system > /dev/null 2>&1 || true
echo "    Kernel parameters updated (swappiness=20, vfs_cache_pressure=50, overcommit=1)."

# 4. Host OS Firewall Configuration (Ports 80 & 443)
echo "[3/5] Configuring host OS firewall for HTTP (80) and HTTPS (443)..."
if command -v ufw > /dev/null 2>&1; then
  echo "    Configuring UFW..."
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
elif command -v firewall-cmd > /dev/null 2>&1; then
  echo "    Configuring firewalld (Oracle Linux / RHEL)..."
  firewall-cmd --zone=public --permanent --add-service=http || true
  firewall-cmd --zone=public --permanent --add-service=https || true
  firewall-cmd --reload || true
fi

# Ensure OCI Ubuntu default iptables rule does not block port 80/443
if command -v iptables > /dev/null 2>&1; then
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport 80 -j ACCEPT
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport 443 -j ACCEPT
  if command -v netfilter-persistent > /dev/null 2>&1; then
    netfilter-persistent save || true
  fi
fi
echo "    Host firewall rules applied."

# 5. Install Docker and Docker Compose (if not installed)
echo "[4/5] Checking Docker installation..."
if ! command -v docker > /dev/null 2>&1; then
  echo "    Installing Docker Engine via official convenience script..."
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
  systemctl enable docker
  systemctl start docker
  echo "    Docker installed successfully."
else
  echo "    Docker is already installed."
fi

# Add real user to docker group
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
  usermod -aG docker "$REAL_USER" || true
  echo "    User '$REAL_USER' added to 'docker' group."
fi

# 6. Verification and Next Steps Summary
echo "[5/5] Setup Complete!"
echo "=========================================================="
echo "  Instance Optimization Verification:"
echo "    RAM & Swap:  $(free -h | awk '/Mem:/ {print $2}') physical / $(free -h | awk '/Swap:/ {print $2}') swap"
echo "    Swappiness:  $(cat /proc/sys/vm/swappiness)"
echo "=========================================================="
echo ""
echo "Next Steps to deploy Reddit Intelligence Platform:"
echo "1. Verify OCI Cloud Console Security List:"
echo "   Ensure Ingress Rules allow TCP destination port 80 and 443 from 0.0.0.0/0."
echo "2. Create or verify your .env file with production credentials:"
echo "   cp .env.example .env (and configure POSTGRES_PASSWORD, GROQ_API_KEY, HF_TOKEN, etc.)"
echo "3. Build and launch the optimized stack:"
echo "   docker compose -f docker-compose.oci.yml up -d --build"
echo "4. Monitor container health & memory consumption:"
echo "   docker stats"
echo "=========================================================="
