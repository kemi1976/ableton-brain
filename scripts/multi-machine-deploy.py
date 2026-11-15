#!/usr/bin/env python3
"""
🚀 Multi-Machine Deployment Script
Deploys Eliza instances across the network
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List
import os

class MultiMachineDeployer:
    def __init__(self, config_path: str = "knowledge/ableton-brain/multi-eliza-config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.project_root = Path(__file__).parent.parent.parent
    
    def _load_config(self) -> Dict:
        """Load multi-eliza configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def deploy_to_lenovo(self):
        """Deploy secondary Eliza to Lenovo desktop"""
        
        secondary = self.config.get('network', {}).get('secondary', {})
        if not secondary:
            print("❌ Lenovo (secondary) not found in config")
            return False
        
        ip = secondary.get('ip')
        name = secondary.get('name', 'lenovo')
        
        print(f"\n🚀 DEPLOYING TO LENOVO DESKTOP ({ip})")
        print("="*70)
        
        # Step 1: Check connectivity
        print(f"\n1️⃣ Checking connectivity to {name}...")
        result = subprocess.run(['ping', '-n', '1', ip], capture_output=True)
        if result.returncode != 0:
            print(f"   ❌ Cannot reach {ip}")
            return False
        print(f"   ✅ Can reach {ip}")
        
        # Step 2: Check if SSH works
        print(f"\n2️⃣ Testing SSH connection...")
        ssh_test = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=5', f'moadeeb@{ip}', 'echo "connected"'],
            capture_output=True,
            text=True
        )
        
        if ssh_test.returncode == 0:
            print("   ✅ SSH connection successful")
            ssh_available = True
        else:
            print("   ⚠️ SSH not available, will use alternative method")
            ssh_available = False
        
        # Step 3: Deploy files
        print(f"\n3️⃣ Deploying Eliza files...")
        
        if ssh_available:
            # Create directory on remote
            print("   Creating remote directory...")
            subprocess.run([
                'ssh', f'moadeeb@{ip}', 
                'mkdir -p ~/eliza-secondary'
            ], capture_output=True)
            
            # Copy files via SCP
            print("   Copying files via SCP...")
            files_to_copy = [
                'knowledge/ableton-brain',
                'Scripts',
                'knowledge/artist-database.json'
            ]
            
            for file in files_to_copy:
                src = self.project_root / file
                if src.exists():
                    subprocess.run([
                        'scp', '-r', 
                        str(src), 
                        f'moadeeb@{ip}:~/eliza-secondary/'
                    ], capture_output=True)
                    print(f"   Copied: {file}")
        else:
            print("   ⚠️ Skipping remote deployment (SSH unavailable)")
            print("   To deploy manually:")
            print(f"      1. Share folder from this machine")
            print(f"      2. Map network drive on {name}")
            print(f"      3. Copy files manually")
        
        # Step 4: Create secondary Eliza config
        print(f"\n4️⃣ Creating secondary Eliza configuration...")
        
        secondary_config = {
            "name": "Eliza-Secondary",
            "role": "assistant",
            "ip": ip,
            "port": 8000,
            "services": ["ml-processing", "file-backup", "database-sync"],
            "mode": "assistant",
            "primary_coordinator": self.config['network']['primary']['ip'],
            "features": {
                "ml_processing": True,
                "file_backup": True,
                "database_sync": True,
                "notifications": True
            }
        }
        
        config_file = self.project_root / "knowledge" / "ableton-brain" / "secondary-config.json"
        with open(config_file, 'w') as f:
            json.dump(secondary_config, f, indent=2)
        print(f"   Saved: {config_file}")
        
        # Step 5: Create startup script
        print(f"\n5️⃣ Creating startup scripts...")
        
        startup_script = f"""#!/bin/bash
# Startup script for Secondary Eliza on {name}

cd ~/eliza-secondary
python3 eliza.py --mode assistant --port 8000 --role secondary

# Or if using Python 3.14:
# /c/Users/pc/AppData/Local/Programs/Python/Python314/python.exe eliza.py --mode assistant --port 8000
"""
        
        script_path = self.project_root / "knowledge" / "ableton-brain" / "scripts" / "start-secondary.sh"
        with open(script_path, 'w') as f:
            f.write(startup_script)
        print(f"   Created: {script_path}")
        
        return True
    
    def deploy_to_mobiles(self):
        """Show deployment instructions for mobile devices"""
        mobile_devices = self.config.get('network', {}).get('mobile', [])
        
        print(f"\n📱 MOBILE DEVICE SETUP")
        print("="*70)
        
        for mobile in mobile_devices:
            print(f"\n📱 {mobile['name']} ({mobile['ip']})")
            print(f"   Status: {'✅ Online' if mobile.get('online') else '❌ Offline'}")
            print(f"   Type: {mobile.get('os', 'unknown')}")
            
            if mobile['name'] == 'moas-galaxy-s9':
                print(f"\n   SETUP INSTRUCTIONS:")
                print(f"   1. Install Termux from Google Play Store")
                print(f"   2. Open Termux and run:")
                print(f"      pkg install python git")
                print(f"      cd ~")
                print(f"      git clone [your-eliza-repo]")
                print(f"      python eliza.py --mode mobile --port 3000")
                
            elif mobile['name'] == 'z2464n':
                print(f"\n   SETUP INSTRUCTIONS:")
                print(f"   1. Access your development Eliza")
                print(f"   2. Run in client mode:")
                print(f"      python eliza.py --mode client --port 3001")
    
    def generate_deployment_summary(self):
        """Generate deployment summary"""
        print("\n" + "="*70)
        print("📋 DEPLOYMENT SUMMARY")
        print("="*70)
        
        print(f"\n🤖 INSTALLED ELIZA INSTANCES:")
        
        primary = self.config.get('network', {}).get('primary', {})
        if primary:
            print(f"\n   ✅ PRIMARY: {primary.get('name', 'Primary PC')}")
            print(f"      Address: {primary.get('ip')}")
            print(f"      Role: Orchestrator")
            print(f"      Status: Main instance (already deployed)")
        
        secondary = self.config.get('network', {}).get('secondary', {})
        if secondary:
            print(f"\n   ✅ SECONDARY: {secondary.get('name', 'Lenovo')}")
            print(f"      Address: {secondary.get('ip')}")
            print(f"      Role: Assistant/Processing")
            print(f"      Status: Configuration created")
            print(f"      Next: Run start-secondary.sh on the machine")
        
        print(f"\n   📱 MOBILE CLIENTS:")
        for mobile in self.config.get('network', {}).get('mobile', []):
            print(f"      • {mobile.get('name')} - {mobile.get('ip')}")
        
        unknown = self.config.get('network', {}).get('unknown', [])
        if unknown:
            print(f"\n   ❓ UNKNOWN: {len(unknown)} devices found")
            for device in unknown:
                print(f"      • {device.get('name')} - {device.get('ip')}")
        
        print("\n" + "="*70)
        print("✅ DEPLOYMENT CONFIGURATION COMPLETE")
        print("="*70)
        
        print(f"\n📁 Files Created:")
        print(f"   • knowledge/ableton-brain/multi-eliza-config.json")
        print(f"   • knowledge/ableton-brain/secondary-config.json")
        print(f"   • knowledge/ableton-brain/scripts/start-secondary.sh")
        print(f"   • knowledge/ableton-brain/scripts/network-discovery.py")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. Run: python scripts/network-discovery.py")
        print(f"   2. For Lenovo: Execute start-secondary.sh on that machine")
        print(f"   3. Install Eliza on mobile devices using Termux")
        print(f"   4. Test multi-instance communication")

# Run deployment
if __name__ == "__main__":
    deployer = MultiMachineDeployer()
    
    # Deploy to Lenovo
    deployer.deploy_to_lenovo()
    
    # Show mobile setup
    deployer.deploy_to_mobiles()
    
    # Summary
    deployer.generate_deployment_summary()
    
    print(f"\n✅ Multi-machine deployment preparation complete!")