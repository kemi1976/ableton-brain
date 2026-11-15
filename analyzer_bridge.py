"""
AbletonMCP Analyzer Bridge
Receives real-time audio metrics from Max for Live device via OSC
Port: 9878 (UDP)
"""
import asyncio
import json
import threading
from pythonosc import dispatcher, osc_server
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import time


@dataclass
class TrackMetrics:
    """Real-time audio metrics for a single track"""
    track_index: int
    track_name: str
    timestamp: float
    
    # Loudness (LUFS)
    lufs_integrated: float = -60.0
    lufs_momentary: float = -60.0
    lufs_shortterm: float = -60.0
    lufs_range: float = 0.0  # LRA
    
    # Peak levels
    true_peak_l: float = -60.0
    true_peak_r: float = -60.0
    true_peak_max: float = -60.0
    
    # Stereo
    stereo_correlation: float = 0.0
    stereo_width: float = 0.0
    stereo_balance: float = 0.0
    
    # Spectral (7 bands)
    spectral_sub: float = 0.0      # 20-60 Hz
    spectral_bass: float = 0.0     # 60-250 Hz
    spectral_low_mid: float = 0.0  # 250-500 Hz
    spectral_mid: float = 0.0      # 500-2000 Hz
    spectral_high_mid: float = 0.0 # 2000-4000 Hz
    spectral_high: float = 0.0     # 4000-8000 Hz
    spectral_air: float = 0.0      # 8000-20000 Hz
    
    # Musical
    tempo: float = 0.0
    key: str = "C"
    key_confidence: float = 0.0
    
    # RMS
    rms_l: float = 0.0
    rms_r: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_index": self.track_index,
            "track_name": self.track_name,
            "timestamp": self.timestamp,
            "lufs": {
                "integrated": round(self.lufs_integrated, 1),
                "momentary": round(self.lufs_momentary, 1),
                "shortterm": round(self.lufs_shortterm, 1),
                "range": round(self.lufs_range, 1),
            },
            "true_peak": {
                "left": round(self.true_peak_l, 2),
                "right": round(self.true_peak_r, 2),
                "max": round(self.true_peak_max, 2),
            },
            "stereo": {
                "correlation": round(self.stereo_correlation, 3),
                "width": round(self.stereo_width, 3),
                "balance": round(self.stereo_balance, 3),
            },
            "spectrum": {
                "sub": round(self.spectral_sub, 3),
                "bass": round(self.spectral_bass, 3),
                "low_mid": round(self.spectral_low_mid, 3),
                "mid": round(self.spectral_mid, 3),
                "high_mid": round(self.spectral_high_mid, 3),
                "high": round(self.spectral_high, 3),
                "air": round(self.spectral_air, 3),
            },
            "musical": {
                "tempo": round(self.tempo, 2) if self.tempo else None,
                "key": self.key,
                "key_confidence": round(self.key_confidence, 2),
            },
            "rms": {
                "left": round(self.rms_l, 4),
                "right": round(self.rms_r, 4),
            }
        }


class AnalyzerBridge:
    """OSC server that receives audio metrics from Max for Live analyzer devices"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9878):
        self.host = host
        self.port = port
        self.server: Optional[osc_server.AsyncIOOSCUDPServer] = None
        self.transport = None
        self.metrics: Dict[int, TrackMetrics] = {}
        self.history: Dict[int, list] = defaultdict(list)
        self.max_history = 300  # 5 minutes at 1Hz
        self.callbacks: list = []
        self._running = False
        
        # Track name mapping (index -> name)
        self.track_names: Dict[int, str] = {}
        
    def start(self):
        """Start the OSC server"""
        if self._running:
            return
            
        disp = dispatcher.Dispatcher()
        disp.map("/analyzer/*", self._handle_analyzer_message)
        disp.map("/track/name", self._handle_track_name)
        
        loop = asyncio.new_event_loop()
        
        def run_server():
            asyncio.set_event_loop(loop)
            self.server = osc_server.AsyncIOOSCUDPServer(
                (self.host, self.port), disp, loop
            )
            loop.run_until_complete(self.server.create_serve_endpoint())
            self._running = True
            print(f"[AnalyzerBridge] OSC server listening on {self.host}:{self.port}")
            loop.run_forever()
            
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the OSC server"""
        if self.server:
            self.server = None
        self._running = False
        
    def _handle_track_name(self, address: str, *args):
        """Handle track name registration: /track/name <index> <name>"""
        if len(args) >= 2:
            index = int(args[0])
            name = str(args[1])
            self.track_names[index] = name
            if index in self.metrics:
                self.metrics[index].track_name = name
                
    def _handle_analyzer_message(self, address: str, *args):
        """Handle analyzer metrics: /analyzer/<track_index> <metrics...>"""
        try:
            # Extract track index from address
            parts = address.split("/")
            if len(parts) < 3:
                return
            track_index = int(parts[2])
            
            # Get or create metrics object
            if track_index not in self.metrics:
                self.metrics[track_index] = TrackMetrics(
                    track_index=track_index,
                    track_name=self.track_names.get(track_index, f"Track {track_index}"),
                    timestamp=time.time()
                )
                
            m = self.metrics[track_index]
            m.timestamp = time.time()
            m.track_name = self.track_names.get(track_index, m.track_name)
            
            # Parse metrics based on argument count
            # Expected: integrated_lufs, momentary_lufs, shortterm_lufs, lra,
            #           true_peak_l, true_peak_r, stereo_corr,
            #           spectral_0..6 (7 bands),
            #           tempo, key_index, key_confidence,
            #           rms_l, rms_r
            
            if len(args) >= 20:
                m.lufs_integrated = float(args[0])
                m.lufs_momentary = float(args[1])
                m.lufs_shortterm = float(args[2])
                m.lufs_range = float(args[3])
                m.true_peak_l = float(args[4])
                m.true_peak_r = float(args[5])
                m.true_peak_max = max(m.true_peak_l, m.true_peak_r)
                m.stereo_correlation = float(args[6])
                
                # 7 spectral bands
                m.spectral_sub = float(args[7])
                m.spectral_bass = float(args[8])
                m.spectral_low_mid = float(args[9])
                m.spectral_mid = float(args[10])
                m.spectral_high_mid = float(args[11])
                m.spectral_high = float(args[12])
                m.spectral_air = float(args[13])
                
                m.tempo = float(args[14])
                key_idx = int(args[15])
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                m.key = keys[key_idx % 12]
                m.key_confidence = float(args[16])
                
                m.rms_l = float(args[17])
                m.rms_r = float(args[18])
                
                # Calculate stereo width from correlation
                m.stereo_width = max(0.0, 1.0 - abs(m.stereo_correlation))
                m.stereo_balance = m.rms_l - m.rms_r
                
                # Store in history
                self.history[track_index].append(m.to_dict())
                if len(self.history[track_index]) > self.max_history:
                    self.history[track_index].pop(0)
                    
                # Notify callbacks
                for cb in self.callbacks:
                    try:
                        cb(m.to_dict())
                    except Exception as e:
                        print(f"[AnalyzerBridge] Callback error: {e}")
                        
        except Exception as e:
            print(f"[AnalyzerBridge] Parse error: {e}")
            
    def register_callback(self, callback: Callable[[Dict], None]):
        """Register a callback for new metrics"""
        self.callbacks.append(callback)
        
    def get_metrics(self, track_index: int = None) -> Dict:
        """Get current metrics for track(s)"""
        if track_index is not None:
            if track_index in self.metrics:
                return self.metrics[track_index].to_dict()
            return {"error": f"Track {track_index} not found"}
        return {k: v.to_dict() for k, v in self.metrics.items()}
        
    def get_history(self, track_index: int, seconds: int = 60) -> list:
        """Get metrics history for a track"""
        if track_index not in self.history:
            return []
        cutoff = time.time() - seconds
        return [m for m in self.history[track_index] if m["timestamp"] > cutoff]
        
    def get_summary(self) -> Dict:
        """Get summary of all tracks"""
        return {
            "tracks": len(self.metrics),
            "track_indices": list(self.metrics.keys()),
            "server_running": self._running,
            "port": self.port,
        }


# Global instance
_bridge: Optional[AnalyzerBridge] = None


def get_analyzer_bridge() -> AnalyzerBridge:
    """Get or create the global analyzer bridge"""
    global _bridge
    if _bridge is None:
        _bridge = AnalyzerBridge()
    return _bridge


def start_analyzer_bridge():
    """Start the global analyzer bridge"""
    bridge = get_analyzer_bridge()
    bridge.start()
    return bridge


async def main():
    """Run analyzer bridge standalone"""
    bridge = start_analyzer_bridge()
    print("[AnalyzerBridge] Running... Press Ctrl+C to stop")
    try:
        while True:
            await asyncio.sleep(5)
            summary = bridge.get_summary()
            print(f"[AnalyzerBridge] Active tracks: {summary['tracks']}")
    except KeyboardInterrupt:
        print("[AnalyzerBridge] Stopping...")
        bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())