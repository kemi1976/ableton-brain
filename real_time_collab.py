#!/usr/bin/env python3
"""
Real-Time Collaboration Module
WebSocket-free TCP session sync: host a project session, peers join and exchange clip/param events.
Uses stdlib socket + threading (no external deps).
Competitor parity: Splice, Studio One collaboration.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field


@dataclass
class SessionEvent:
    """One broadcast event in a collaboration session."""
    id: str
    type: str  # clip_added, param_changed, play, stop, chat, cursor_move
    user_id: str
    payload: Dict
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "user_id": self.user_id,
            "payload": self.payload, "timestamp": self.timestamp,
        }


class CollabServer:
    """Hosts a collaboration session. Peers connect via TCP."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9890):
        self.host = host
        self.port = port
        self.clients: Dict[str, socket.socket] = {}
        self.events: List[SessionEvent] = []
        self.max_events = 5000
        self.running = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.on_event: Optional[Callable[[SessionEvent], None]] = None

    def start(self) -> None:
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        for c in list(self.clients.values()):
            try:
                c.close()
            except Exception:
                pass
        self.clients.clear()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(8)
        srv.settimeout(1.0)
        while self.running:
            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue
            except Exception:
                continue
            uid = str(uuid.uuid4())[:8]
            self.clients[uid] = conn
            threading.Thread(target=self._handle, args=(conn, uid), daemon=True).start()

    def _handle(self, conn: socket.socket, uid: str) -> None:
        buf = b""
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    evt = SessionEvent(
                        id=str(uuid.uuid4())[:8],
                        type=msg.get("type", "unknown"),
                        user_id=uid,
                        payload=msg.get("payload", {}),
                        timestamp=time.time(),
                    )
                    with self._lock:
                        self.events.append(evt)
                        if len(self.events) > self.max_events:
                            self.events = self.events[-self.max_events:]
                    if self.on_event:
                        self.on_event(evt)
                    self._broadcast(evt, skip=uid)
            except Exception:
                break
        try:
            conn.close()
        except Exception:
            pass
        self.clients.pop(uid, None)

    def _broadcast(self, evt: SessionEvent, skip: Optional[str] = None) -> None:
        line = (json.dumps(evt.to_dict()) + "\n").encode("utf-8")
        dead = []
        for uid, conn in self.clients.items():
            if uid == skip:
                continue
            try:
                conn.sendall(line)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.clients.pop(uid, None)

    def get_events(self, since: float = 0.0) -> List[Dict]:
        with self._lock:
            return [e.to_dict() for e in self.events if e.timestamp > since]

    def status(self) -> Dict:
        return {
            "running": self.running,
            "port": self.port,
            "clients": len(self.clients),
            "event_count": len(self.events),
        }


class CollabClient:
    """Connects to a collab session, sends/receives events."""

    def __init__(self, host: str, port: int, user_id: Optional[str] = None):
        self.host = host
        self.port = port
        self.user_id = user_id or str(uuid.uuid4())[:8]
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.events: List[SessionEvent] = []
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.on_event: Optional[Callable[[SessionEvent], None]] = None

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self._thread = threading.Thread(target=self._recv, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self.connected = False
            return False

    def disconnect(self) -> None:
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def send(self, event_type: str, payload: Dict) -> None:
        if not self.connected or not self.sock:
            return
        evt = SessionEvent(
            id=str(uuid.uuid4())[:8], type=event_type, user_id=self.user_id,
            payload=payload, timestamp=time.time(),
        )
        line = (json.dumps(evt.to_dict()) + "\n").encode("utf-8")
        try:
            self.sock.sendall(line)
            with self._lock:
                self.events.append(evt)
        except Exception:
            self.connected = False

    def _recv(self) -> None:
        buf = b""
        while self.connected and self.sock:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    evt = SessionEvent(
                        id=msg["id"], type=msg["type"], user_id=msg["user_id"],
                        payload=msg["payload"], timestamp=msg["timestamp"],
                    )
                    with self._lock:
                        self.events.append(evt)
                    if self.on_event:
                        self.on_event(evt)
            except Exception:
                break
        self.connected = False

    def get_events(self, since: float = 0.0) -> List[Dict]:
        with self._lock:
            return [e.to_dict() for e in self.events if e.timestamp > since]


def start_host(port: int = 9890) -> Dict:
    srv = CollabServer(port=port)
    srv.start()
    return {"status": "hosting", "port": port}


def join_session(host: str, port: int) -> Dict:
    cli = CollabClient(host, port)
    ok = cli.connect()
    return {"status": "connected" if ok else "failed", "user_id": cli.user_id}


if __name__ == "__main__":
    import time
    srv = CollabServer(port=9890)
    srv.start()
    print("Server on 9890")
    cli = CollabClient("127.0.0.1", 9890)
    cli.connect()
    cli.send("chat", {"text": "hello from client"})
    time.sleep(0.5)
    print("Events:", cli.get_events())
    cli.disconnect()
    srv.stop()