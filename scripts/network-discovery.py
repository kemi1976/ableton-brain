#!/usr/bin/env python3
"""
🔍 Network Discovery Tool for Multi-Eliza Setup
Discovers Eliza instances and network devices
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import socket

class NetworkDiscoverer:
    def __init__(self):
        self.tailscale_peers = []
        self.eliza_instances = []
        self.devices = {
            'primary': None,
            'secondary': None,
            'mobile': [],
            'unknown': []
        }
    
    def get_tailscale_peers(self) -> List[Dict]:
        """Get list of Tailscale network peers"""
        try:
            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                peers = data.get('peer', [])
                
                peer_list = []
                for peer in peers:
                    peer_list.append({
                        'name': peer.get('HostName', 'unknown'),
                        'ip': peer.get('TailscaleIPs', [''])[0],
                        'os': peer.get('OS', 'unknown'),
                        'online': peer.get('Online', False),
                        'last_seen': peer.get('LastSeen', '')
                    })
                
                return peer_list
        except Exception as e:
            print(f"Error getting Tailscale peers: {e}")
        
        return []
    
    def scan_for_eliza(self, ip: str, port: int = 5000) -> bool:
        """Check if Eliza instance is running on IP:port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                # Try to ping Eliza health endpoint
                try:
                    import urllib.request
                    url = f"http://{ip}:{port}/health"
                    response = urllib.request.urlopen(url, timeout=2)
                    return response.status == 200
                except:
                    return True  # Port is open at least
        except:
            pass
        
        return False
    
    def classify_device(self, name: str, ip: str) -> str:
        """Classify device type by name"""
        name_lower = name.lower()
        
        # Primary PC
        if 'desktop-9v5i173' in name or 'moadeeb' in name:
            return 'primary'
        
        # Lenovo/Secondary
        if 'lenovo' in name or 'desktop-h3gcmqr' in name:
            return 'secondary'
        
        # Samsung phones
        if 'samsung' in name or 'moas' in name:
            return 'mobile'
        
        # Neo/Tablet
        if 'neo' in name or 'z2464n' in name or 'android' in name:
            return 'mobile'
        
        # ThinkPads
        if 'thinkpad' in name or 't4' in name or 't5' in name or 'lenovo' in name:
            return 'unknown'
        
        # Macs
        if 'mac' in name or 'macbook' in name or 'imac' in name:
            return 'unknown'
        
        return 'unknown'
    
    def discover_all_devices(self) -> Dict:
        """Run full discovery and classify devices"""
        # Get Tailscale peers
        peers = self.get_tailscale_peers()
        
        print("="*70)
        print("🌐 NETWORK DISCOVERY RESULTS")
        print("="*70)
        
        print(f"\n📡 Found {len(peers)} Tailscale peers:")
        
        for peer in peers:
            if not peer['online']:
                continue
            
            device_type = self.classify_device(peer['name'], peer['ip'])
            
            print(f"\n   🖥️  {peer['name']}")
            print(f"      IP: {peer['ip']}")
            print(f"      OS: {peer['os']}")
            print(f"      Type: {device_type}")
            
            # Check for Eliza
            has_eliza = self.scan_for_eliza(peer['ip'])
            if has_eliza:
                print(f"      🤖 Eliza: ✅ RUNNING")
            else:
                print(f"      🤖 Eliza: ❌ Not detected")
            
            # Store in appropriate category
            if device_type == 'primary':
                self.devices['primary'] = {
                    'name': peer['name'],
                    'ip': peer['ip'],
                    'os': peer['os'],
                    'has_eliza': has_eliza
                }
            elif device_type == 'secondary':
                self.devices['secondary'] = {
                    'name': peer['name'],
                    'ip': peer['ip'],
                    'os': peer['os'],
                    'has_eliza': has_eliza
                }
            elif device_type == 'mobile':
                self.devices['mobile'].append({
                    'name': peer['name'],
                    'ip': peer['ip'],
                    'os': peer['os'],
                    'has_eliza': has_eliza
                })
            else:
                self.devices['unknown'].append({
                    'name': peer['name'],
                    'ip': peer['ip'],
                    'os': peer['os'],
                    'has_eliza': has_eliza
                })
        
        return self.devices
    
    def print_summary(self):
        """Print network summary"""
        print("\n" + "="*70)
        print("📋 NETWORK SUMMARY")
        print("="*70)
        
        print(f"\n✅ PRIMARY ELIZA: {self.devices['primary']['name'] if self.devices['primary'] else 'Not found'}")
        if self.devices['primary']:
            print(f"   IP: {self.devices['primary']['ip']}")
            print(f"   Eliza: {'✅ Running' if self.devices['primary'].get('has_eliza') else '❌ Not installed'}")
        
        print(f"\n✅ SECONDARY ELIZA: {self.devices['secondary']['name'] if self.devices['secondary'] else 'Not found'}")
        if self.devices['secondary']:
            print(f"   IP: {self.devices['secondary']['ip']}")
            print(f"   Eliza: {'✅ Running' if self.devices['secondary'].get('has_eliza') else '❌ Not installed'}")
        
        print(f"\n📱 MOBILE ELIZAS: {len(self.devices['mobile'])}")
        for mobile in self.devices['mobile']:
            print(f"   • {mobile['name']} ({mobile['ip']})")
        
        print(f"\n❓ UNKNOWN DEVICES: {len(self.devices['unknown'])}")
        for device in self.devices['unknown']:
            print(f"   • {device['name']} ({device['ip']})")
        
        print("\n" + "="*70)
        
        # Generate config
        self.generate_config()
    
    def generate_config(self):
        """Generate multi-eliza configuration"""
        config = {
            'version': '1.0',
            'network': {
                'primary': self.devices['primary'],
                'secondary': self.devices['secondary'],
                'mobile': self.devices['mobile'],
                'unknown': self.devices['unknown']
            },
            'services': {
                'primary': ['orchestrator', 'music-production', 'ai-brain', 'coordination'],
                'secondary': ['ml-processing', 'file-backup', 'database-sync'],
                'mobile': ['remote-control', 'notifications', 'queries'],
                'unknown': ['light-services', 'monitoring']
            }
        }
        
        # Save config
        config_path = Path('knowledge/ableton-brain/multi-eliza-config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n📄 Configuration saved to: {config_path}")

# Run discovery
if __name__ == "__main__":
    discoverer = NetworkDiscoverer()
    devices = discoverer.discover_all_devices()
    discoverer.print_summary()
    
    print("\n✅ Network discovery complete!")
    print("   Next steps:")
    print("   1. Review UNKNOWN DEVICES above")
    print("   2. Install/configure Eliza on secondary machines")
    print("   2. Run deployment script: multi-machine-deploy.py")