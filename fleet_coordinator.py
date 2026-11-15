"""
ABLETON BRAIN - Fleet Coordinator
Distributed architecture for Multi-Eliza network
Coordinates: Dell Vostro (DAW), ThinkPad (GPU), Mobile (BLE MIDI), Hermes (Dashboard)
"""
import asyncio
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class NodeRole(Enum):
    DAW_PRIMARY = "daw_primary"        # Dell Vostro - runs Ableton + MCP
    GPU_SECONDARY = "gpu_secondary"    # ThinkPad - runs AI inference
    MOBILE_CONTROLLER = "mobile"       # Galaxy S9 / Neo Nubia - BLE MIDI
    DASHBOARD = "dashboard"            # Hermes - monitoring UI


@dataclass
class FleetNode:
    name: str
    role: NodeRole
    tailscale_ip: str
    hostname: str
    capabilities: List[str]
    status: str = "unknown"
    last_seen: float = 0
    cpu_percent: float = 0.0
    gpu_available: bool = False
    ableton_running: bool = False


class FleetCoordinator:
    """Coordinates distributed Ableton Brain across Multi-Eliza network"""
    
    NODES = {
        "dell-vostro": FleetNode(
            name="Dell Vostro (Primary DAW)",
            role=NodeRole.DAW_PRIMARY,
            tailscale_ip="100.82.15.79",
            hostname="desktop-9v5i173",
            capabilities=["ableton", "mcp_server", "analyzer_bridge", "max_for_live", "audio_interface"],
            gpu_available=False
        ),
        "thinkpad-x13": FleetNode(
            name="ThinkPad X13 (GPU Inference)",
            role=NodeRole.GPU_SECONDARY,
            tailscale_ip="100.90.0.100",
            hostname="desktop-h3gcmqr",
            capabilities=["cuda", "magenta_realtime", "stable_audio", "audioldm", "demucs", "librosa"],
            gpu_available=True
        ),
        "galaxy-s9": FleetNode(
            name="Galaxy S9 (Mobile Controller)",
            role=NodeRole.MOBILE_CONTROLLER,
            tailscale_ip="100.84.148.23",
            hostname="galaxy-s9",
            capabilities=["ble_midi", "touch_osc", "ableton_link"],
            gpu_available=False
        ),
        "neo-nubia": FleetNode(
            name="Neo Nubia (Mobile Controller)",
            role=NodeRole.MOBILE_CONTROLLER,
            tailscale_ip="100.99.81.13",
            hostname="neo-nubia",
            capabilities=["ble_midi", "touch_osc", "ableton_link"],
            gpu_available=False
        ),
        "hermes-dashboard": FleetNode(
            name="Hermes Dashboard",
            role=NodeRole.DASHBOARD,
            tailscale_ip="100.82.15.79",  # Same as Dell
            hostname="desktop-9v5i173",
            capabilities=["monitoring", "fleet_ui", "kanban", "memory"],
            gpu_available=False
        ),
    }
    
    def __init__(self, local_node: str = "dell-vostro"):
        self.local_node = local_node
        self.nodes = self.NODES.copy()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self.syncthing_paths = {
            "projects": r"C:\Users\pc\Documents\Ableton Projects",
            "samples": r"C:\Users\pc\Documents\AI PROJECTS ANDRIOD\knowledge\ableton-brain\samples",
            "analysis": r"C:\Users\pc\Documents\AI PROJECTS ANDRIOD\knowledge\ableton-brain\analysis",
            "stems": r"C:\Users\pc\Documents\AI PROJECTS ANDRIOD\knowledge\ableton-brain\stems",
        }
        
    async def start(self):
        """Start fleet coordination"""
        print(f"[Fleet] Starting coordinator on {self.local_node}")
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor())
        
        # Start task processor
        asyncio.create_task(self._process_tasks())
        
        # Start Syncthing sync monitor
        asyncio.create_task(self._syncthing_monitor())
        
        print("[Fleet] Coordinator started")
        
    async def _health_monitor(self):
        """Monitor node health via Tailscale"""
        while True:
            for node_id, node in self.nodes.items():
                if node_id == self.local_node:
                    node.status = "healthy"
                    node.last_seen = time.time()
                    continue
                    
                # Ping via Tailscale
                try:
                    result = subprocess.run(
                        ["tailscale", "ping", "-c", "1", "-timeout", "2s", node.tailscale_ip],
                        capture_output=True, timeout=5
                    )
                    if result.returncode == 0:
                        node.status = "healthy"
                    else:
                        node.status = "unreachable"
                except:
                    node.status = "unknown"
                    
                node.last_seen = time.time()
                
            await asyncio.sleep(30)
            
    async def _process_tasks(self):
        """Process distributed tasks"""
        while True:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self._execute_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Fleet] Task error: {e}")
                
    async def _execute_task(self, task: Dict):
        """Execute a distributed task"""
        task_id = task.get("id", "unknown")
        target = task.get("target", "auto")
        action = task.get("action")
        params = task.get("params", {})
        
        print(f"[Fleet] Executing task {task_id}: {action} on {target}")
        
        try:
            if target == "gpu" or target == "thinkpad-x13":
                result = await self._offload_to_gpu(action, params)
            elif target == "mobile":
                result = await self._send_to_mobile(action, params)
            elif target == "daw" or target == "dell-vostro":
                result = await self._execute_local(action, params)
            else:
                result = {"error": f"Unknown target: {target}"}
                
            self.results[task_id] = {"status": "completed", "result": result}
            
        except Exception as e:
            self.results[task_id] = {"status": "failed", "error": str(e)}
            
    async def _offload_to_gpu(self, action: str, params: Dict) -> Dict:
        """Offload compute-intensive task to ThinkPad"""
        # This would use SSH or HTTP to ThinkPad
        # For now, simulate
        thinkpad_ip = self.nodes["thinkpad-x13"].tailscale_ip
        
        if action == "magenta_realtime":
            return await self._ssh_run(
                thinkpad_ip,
                f"python magenta_realtime_server.py --style {params.get('style', 'continue')}"
            )
        elif action == "stable_audio":
            return await self._ssh_run(
                thinkpad_ip,
                f"python stable_audio_inference.py --prompt '{params.get('prompt')}'"
            )
        elif action == "demucs":
            return await self._ssh_run(
                thinkpad_ip,
                f"demucs -n htdemucs -o {params.get('output_dir')} {params.get('audio_path')}"
            )
        elif action == "librosa_analysis":
            return await self._ssh_run(
                thinkpad_ip,
                f"python analyze_audio.py {params.get('audio_path')}"
            )
            
        return {"error": f"Unknown GPU action: {action}"}
    
    async def _ssh_run(self, host: str, command: str) -> Dict:
        """Run command via SSH on remote node"""
        try:
            # This would use actual SSH
            # result = subprocess.run(["ssh", f"pc@{host}", command], capture_output=True, text=True, timeout=300)
            return {"simulated": True, "host": host, "command": command}
        except Exception as e:
            return {"error": str(e)}
    
    async def _send_to_mobile(self, action: str, params: Dict) -> Dict:
        """Send command to mobile device via Tailscale/SSH"""
        return {"sent_to_mobile": True, "action": action}
    
    async def _execute_local(self, action: str, params: Dict) -> Dict:
        """Execute task locally on DAW machine"""
        if action == "install_analyzer":
            # Handled by MCP
            return {"local": "mcp_handled"}
        elif action == "sync_project":
            return await self._sync_project(params.get("project_name"))
        return {"local": True, "action": action}
    
    async def _syncthing_monitor(self):
        """Monitor Syncthing folder sync status"""
        while True:
            try:
                # Check Syncthing API
                result = subprocess.run(
                    ["curl", "-s", "http://127.0.0.1:8385/rest/db/status"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    status = json.loads(result.stdout)
                    print(f"[Fleet] Syncthing: {status.get('folder', 'unknown')} - {status.get('state', 'unknown')}")
            except:
                pass
            await asyncio.sleep(60)
    
    async def _sync_project(self, project_name: str) -> Dict:
        """Trigger Syncthing scan for project folder"""
        # Would call Syncthing REST API
        return {"synced": project_name}
    
    def submit_task(self, action: str, params: Dict, target: str = "auto", task_id: str = None) -> str:
        """Submit a task for distributed execution"""
        import uuid
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]
            
        # Auto-select target based on action
        if target == "auto":
            if action in ["magenta_realtime", "stable_audio", "demucs", "librosa_analysis", "audioldm"]:
                target = "gpu"
            elif action in ["ble_midi", "touch_osc"]:
                target = "mobile"
            else:
                target = "daw"
                
        task = {
            "id": task_id,
            "action": action,
            "params": params,
            "target": target,
            "submitted_at": time.time(),
            "submitted_by": self.local_node
        }
        
        asyncio.create_task(self.task_queue.put(task))
        return task_id
    
    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """Get result of completed task"""
        return self.results.get(task_id)
    
    def get_fleet_status(self) -> Dict:
        """Get overall fleet status"""
        return {
            "local_node": self.local_node,
            "nodes": {
                k: {
                    "name": v.name,
                    "role": v.role.value,
                    "ip": v.tailscale_ip,
                    "status": v.status,
                    "capabilities": v.capabilities,
                    "gpu": v.gpu_available,
                    "last_seen": v.last_seen
                }
                for k, v in self.nodes.items()
            },
            "pending_tasks": self.task_queue.qsize(),
            "completed_tasks": len(self.results)
        }
    
    async def start_ble_midi_bridge(self):
        """Start BlueMIDI bridge for mobile controllers"""
        print("[Fleet] Starting BlueMIDI bridge...")
        try:
            # Check if BlueMIDI is installed
            result = subprocess.run(["where", "bluemidi.exe"], capture_output=True)
            if result.returncode == 0:
                subprocess.Popen(["bluemidi.exe", "--autostart"])
                return {"started": True, "note": "BlueMIDI running in system tray"}
            else:
                return {"started": False, "error": "BlueMIDI not installed. Download from github.com/Armazi000/bluemidi"}
        except Exception as e:
            return {"started": False, "error": str(e)}
    
    def setup_ableton_link(self):
        """Configure Ableton Link for tempo sync across devices"""
        # Ableton Link is built into Live 10+
        # Just needs to be enabled in Preferences > Link/Tempo/MIDI > Show Link Toggle
        return {
            "link_enabled": True,
            "port": 3190,  # Default Link port
            "note": "Enable 'Show Link Toggle' in Ableton Preferences > Link/Tempo/MIDI"
        }


# =========================================================================
# HERMES DASHBOARD EMBEDDING
# =========================================================================

FLEET_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Ableton Brain Fleet Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117; color: #e6edf3;
            padding: 20px; min-height: 100vh;
        }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .title { font-size: 1.5rem; font-weight: 600; }
        .status { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; }
        .status.healthy { background: #1a7f37; color: #7ee787; }
        .status.unreachable { background: #9e2a2a; color: #fca5a5; }
        .status.unknown { background: #7c4a03; color: #fde68a; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
        .card h3 { font-size: 1rem; margin-bottom: 12px; color: #58a6ff; }
        .metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #8b949e; }
        .metric-value { font-weight: 600; }
        .capability { display: inline-block; background: #21262d; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 0.75rem; }
        .task-list { max-height: 200px; overflow-y: auto; }
        .task-item { padding: 8px; border-bottom: 1px solid #21262d; font-size: 0.875rem; }
        .task-item:last-child { border-bottom: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">🧠 Ableton Brain Fleet Dashboard</div>
        <div id="fleet-status" class="status unknown">Loading...</div>
    </div>
    
    <div class="grid" id="nodes-grid"></div>
    
    <div class="card" style="margin-top: 16px;">
        <h3>📋 Task Queue</h3>
        <div class="task-list" id="task-list">Loading...</div>
    </div>
    
    <script>
        async function loadDashboard() {
            try {
                const res = await fetch('http://127.0.0.1:8050/api/fleet/status');
                const data = await res.json();
                renderDashboard(data);
            } catch (e) {
                document.getElementById('fleet-status').textContent = 'Dashboard API not running';
                document.getElementById('fleet-status').className = 'status unknown';
            }
        }
        
        function renderDashboard(data) {
            const statusEl = document.getElementById('fleet-status');
            statusEl.textContent = `Fleet: ${Object.values(data.nodes).filter(n => n.status === 'healthy').length}/${Object.keys(data.nodes).length} nodes healthy`;
            statusEl.className = 'status ' + (data.nodes[data.local_node]?.status || 'unknown');
            
            const grid = document.getElementById('nodes-grid');
            grid.innerHTML = '';
            
            for (const [id, node] of Object.entries(data.nodes)) {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <h3>${node.name} ${id === data.local_node ? '📍' : ''}</h3>
                    <div class="metric"><span class="metric-label">Role</span><span class="metric-value">${node.role}</span></div>
                    <div class="metric"><span class="metric-label">Tailscale IP</span><span class="metric-value">${node.ip}</span></div>
                    <div class="metric"><span class="metric-label">Status</span><span class="metric-value status ${node.status}">${node.status}</span></div>
                    <div class="metric"><span class="metric-label">GPU</span><span class="metric-value">${node.gpu ? '✅ Available' : '❌ None'}</span></div>
                    <div class="metric"><span class="metric-label">Ableton</span><span class="metric-value">${node.capabilities.includes('ableton') ? '✅ Running' : '❌ Not detected'}</span></div>
                    <div style="margin-top: 8px;">
                        ${node.capabilities.map(c => `<span class="capability">${c}</span>`).join('')}
                    </div>
                `;
                grid.appendChild(card);
            }
            
            document.getElementById('task-list').innerHTML = 
                data.pending_tasks > 0 
                    ? `<div class="task-item">Pending tasks: ${data.pending_tasks}</div>`
                    : '<div class="task-item">No pending tasks</div>';
        }
        
        loadDashboard();
        setInterval(loadDashboard, 5000);
    </script>
</body>
</html>
"""


def create_fleet_dashboard_html(output_path: str = None):
    """Create fleet dashboard HTML file"""
    if output_path is None:
        output_path = Path(__file__).parent / "fleet_dashboard.html"
    with open(output_path, 'w') as f:
        f.write(FLEET_DASHBOARD_HTML)
    return str(output_path)


if __name__ == "__main__":
    # Test fleet coordinator
    coordinator = FleetCoordinator("dell-vostro")
    status = coordinator.get_fleet_status()
    print(json.dumps(status, indent=2))
    
    # Create dashboard HTML
    create_fleet_dashboard_html()
    print("\nFleet dashboard HTML created")