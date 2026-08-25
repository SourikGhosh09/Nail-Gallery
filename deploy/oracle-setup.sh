#!/usr/bin/env bash
# =============================================================================
#  One-time server setup for a fresh Oracle Cloud "Always Free" Ubuntu machine.
# =============================================================================
#  This installs Docker (which runs your website) and opens the firewall so the
#  internet can reach it. You only run this ONCE, the first time you connect.
#
#      bash deploy/oracle-setup.sh
#
#  It's safe to run again if something was interrupted.
# =============================================================================
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive   # never pause to ask questions

echo "==> [1/3] Updating the system's package list..."
sudo apt-get update -y

echo "==> [2/3] Installing Docker (this can take a couple of minutes)..."
if command -v docker >/dev/null 2>&1; then
  echo "    Docker is already installed — skipping."
else
  curl -fsSL https://get.docker.com | sudo sh
fi
# Let you run docker without typing "sudo" every time.
sudo usermod -aG docker "$USER" || true

echo "==> [3/3] Opening the firewall for web traffic (ports 80 and 443)..."
# Oracle's Ubuntu images block these by default with iptables. Open them and
# make the change stick across reboots.
sudo iptables -I INPUT -p tcp --dport 80  -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y netfilter-persistent iptables-persistent >/dev/null 2>&1 || true
sudo netfilter-persistent save >/dev/null 2>&1 || true

echo ""
echo "======================================================================"
echo "  [OK]  Your server is ready."
echo ""
echo "  TWO more things before you launch:"
echo ""
echo "   1) Run this ONE command so Docker works without 'sudo':"
echo "          newgrp docker"
echo "      (or simply log out and connect again)."
echo ""
echo "   2) In the Oracle website console, make sure your network Security"
echo "      List allows incoming TCP on ports 80 and 443."
echo "      (The deployment guide shows exactly where — Part 2.)"
echo "======================================================================"
