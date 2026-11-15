"""
Ableton Brain - Phase 3: WebRTC Real-time Collaboration
Peer-to-peer collaboration with presence, cursors, and synchronized state
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import weakref


class MessageType(Enum):
    """Collaboration message types"""
    # Connection
    JOIN = "join"
    LEAVE = "leave"
    PEER_LIST = "peer_list"
    
    # Presence
    CURSOR_POSITION = "cursor_position"
    SELECTION = "selection"
    VIEWPORT = "viewport"
    
    # Project sync
    PROJECT_STATE = "project_state"
    PROJECT_DELTA = "project_delta"
    TRACK_CHANGED = "track_changed"
    CLIP_CHANGED = "clip_changed"
    DEVICE_CHANGED = "device_changed"
    AUTOMATION_CHANGED = "automation_changed"
    
    # Transport
    TRANSPORT_PLAY = "transport_play"
    TRANSPORT_STOP = "transport_stop"
    TRANSPORT_SEEK = "transport_seek"
    TEMPO_CHANGE = "tempo_change"
    
    # Chat/Comments
    CHAT_MESSAGE = "chat_message"
    COMMENT = "comment"
    
    # System
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    ACK = "ack"


@dataclass
class Peer:
    """Collaborating peer"""
    id: str
    name: str
    color: str
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_host: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Presence
    cursor_position: Optional[Dict[str, float]] = None
    selection: Optional[Dict[str, Any]] = None
    viewport: Optional[Dict[str, float]] = None
    current_track: Optional[str] = None
    current_clip: Optional[str] = None


@dataclass
class CollaborationMessage:
    """WebRTC signaling message"""
    type: MessageType
    sender_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_json(self) -> str:
        return json.dumps({
            'type': self.type.value,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'payload': self.payload,
            'message_id': self.message_id
        })
    
    @staticmethod
    def from_json(json_str: str) -> 'CollaborationMessage':
        data = json.loads(json_str)
        return CollaborationMessage(
            type=MessageType(data['type']),
            sender_id=data['sender_id'],
            timestamp=data['timestamp'],
            payload=data['payload'],
            message_id=data['message_id']
        )


class CollaborationManager:
    """Manages WebRTC peer connections and collaboration state"""
    
    def __init__(self, local_peer_id: str, local_peer_name: str, is_host: bool = False):
        self.local_peer_id = local_peer_id
        self.local_peer_name = local_peer_name
        self.is_host = is_host
        
        # Peers
        self.peers: Dict[str, Peer] = {}
        self.peer_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
        ]
        self._color_index = 0
        
        # Connection state
        self.connected = False
        self.room_id: Optional[str] = None
        
        # Callbacks
        self.on_peer_joined: Optional[Callable[[Peer], None]] = None
        self.on_peer_left: Optional[Callable[[str], None]] = None
        self.on_message: Optional[Callable[[CollaborationMessage], None]] = None
        self.on_project_delta: Optional[Callable[[Dict], None]] = None
        self.on_transport_change: Optional[Callable[[str, Dict], None]] = None
        self.on_cursor_update: Optional[Callable[[str, Dict], None]] = None
        
        # Message history for late joiners
        self.message_history: List[CollaborationMessage] = []
        self.max_history = 1000
        
        # Pending ACKs
        self.pending_acks: Dict[str, asyncio.Future] = {}
        
        # WebRTC data channels (simulated - would use aiortc in production)
        self.data_channels: Dict[str, Any] = {}
    
    def _get_next_color(self) -> str:
        color = self.peer_colors[self._color_index % len(self.peer_colors)]
        self._color_index += 1
        return color
    
    async def join_room(self, room_id: str, signaling_server: str = "wss://signaling.example.com"):
        """Join collaboration room"""
        self.room_id = room_id
        self.connected = True
        
        # Create local peer
        local_peer = Peer(
            id=self.local_peer_id,
            name=self.local_peer_name,
            color=self._get_next_color(),
            is_host=self.is_host
        )
        self.peers[self.local_peer_id] = local_peer
        
        # In production: connect to signaling server, establish WebRTC connections
        # For now, simulate
        print(f"Joined room {room_id} as {self.local_peer_name}")
        
        # Simulate other peers joining
        if self.is_host:
            await self._simulate_peers()
    
    async def _simulate_peers(self):
        """Simulate other peers for demo"""
        # In real implementation, this comes from signaling server
        pass
    
    async def leave_room(self):
        """Leave collaboration room"""
        await self._send_message(CollaborationMessage(
            type=MessageType.LEAVE,
            sender_id=self.local_peer_id,
            payload={'peer_id': self.local_peer_id}
        ))
        self.connected = False
        self.peers.clear()
        self.room_id = None
    
    async def _send_message(self, message: CollaborationMessage):
        """Send message to all peers via WebRTC data channels"""
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # In production: send via WebRTC data channels
        # for channel in self.data_channels.values():
        #     channel.send(message.to_json())
        
        # Call local callback for demo
        if self.on_message:
            self.on_message(message)
    
    def handle_message(self, message: CollaborationMessage):
        """Handle incoming message from peer"""
        # Don't process own messages
        if message.sender_id == self.local_peer_id:
            return
        
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Route by type
        if message.type == MessageType.JOIN:
            self._handle_join(message)
        elif message.type == MessageType.LEAVE:
            self._handle_leave(message)
        elif message.type == MessageType.CURSOR_POSITION:
            self._handle_cursor(message)
        elif message.type == MessageType.SELECTION:
            self._handle_selection(message)
        elif message.type == MessageType.PROJECT_DELTA:
            self._handle_project_delta(message)
        elif message.type == MessageType.TRANSPORT_PLAY:
            self._handle_transport(message, 'play')
        elif message.type == MessageType.TRANSPORT_STOP:
            self._handle_transport(message, 'stop')
        elif message.type == MessageType.TRANSPORT_SEEK:
            self._handle_transport(message, 'seek')
        elif message.type == MessageType.TEMPO_CHANGE:
            self._handle_tempo_change(message)
        elif message.type == MessageType.CHAT_MESSAGE:
            self._handle_chat(message)
        elif message.type == MessageType.PING:
            self._send_message(CollaborationMessage(
                type=MessageType.PONG,
                sender_id=self.local_peer_id,
                payload={'original_timestamp': message.timestamp}
            ))
        
        # Call generic handler
        if self.on_message:
            self.on_message(message)
    
    def _handle_join(self, message: CollaborationMessage):
        peer_data = message.payload
        peer = Peer(
            id=peer_data['peer_id'],
            name=peer_data['name'],
            color=peer_data.get('color', self._get_next_color()),
            is_host=peer_data.get('is_host', False)
        )
        self.peers[peer.id] = peer
        
        if self.on_peer_joined:
            self.on_peer_joined(peer)
        
        print(f"Peer joined: {peer.name} ({peer.id})")
    
    def _handle_leave(self, message: CollaborationMessage):
        peer_id = message.payload.get('peer_id')
        if peer_id in self.peers:
            peer_name = self.peers[peer_id].name
            del self.peers[peer_id]
            
            if self.on_peer_left:
                self.on_peer_left(peer_id)
            
            print(f"Peer left: {peer_name} ({peer_id})")
    
    def _handle_cursor(self, message: CollaborationMessage):
        peer_id = message.sender_id
        if peer_id in self.peers:
            cursor = message.payload
            self.peers[peer_id].cursor_position = cursor
            
            if self.on_cursor_update:
                self.on_cursor_update(peer_id, cursor)
    
    def _handle_selection(self, message: CollaborationMessage):
        peer_id = message.sender_id
        if peer_id in self.peers:
            self.peers[peer_id].selection = message.payload
    
    def _handle_project_delta(self, message: CollaborationMessage):
        delta = message.payload
        if self.on_project_delta:
            self.on_project_delta(delta)
    
    def _handle_transport(self, message: CollaborationMessage, action: str):
        if self.on_transport_change:
            self.on_transport_change(action, message.payload)
    
    def _handle_tempo_change(self, message: CollaborationMessage):
        if self.on_transport_change:
            self.on_transport_change('tempo', message.payload)
    
    def _handle_chat(self, message: CollaborationMessage):
        print(f"Chat from {message.sender_id}: {message.payload.get('text', '')}")
    
    # Public API for sending updates
    
    async def send_cursor_position(self, x: float, y: float, track_id: str = None, clip_id: str = None):
        """Send cursor position to peers"""
        payload = {'x': x, 'y': y}
        if track_id:
            payload['track_id'] = track_id
        if clip_id:
            payload['clip_id'] = clip_id
        
        # Update local peer
        if self.local_peer_id in self.peers:
            self.peers[self.local_peer_id].cursor_position = payload
        
        await self._send_message(CollaborationMessage(
            type=MessageType.CURSOR_POSITION,
            sender_id=self.local_peer_id,
            payload=payload
        ))
    
    async def send_selection(self, selection_type: str, ids: List[str]):
        """Send selection to peers"""
        payload = {'type': selection_type, 'ids': ids}
        await self._send_message(CollaborationMessage(
            type=MessageType.SELECTION,
            sender_id=self.local_peer_id,
            payload=payload
        ))
    
    async def send_project_delta(self, delta: Dict[str, Any]):
        """Send project change delta"""
        await self._send_message(CollaborationMessage(
            type=MessageType.PROJECT_DELTA,
            sender_id=self.local_peer_id,
            payload=delta
        ))
    
    async def send_transport_play(self):
        """Send play command"""
        await self._send_message(CollaborationMessage(
            type=MessageType.TRANSPORT_PLAY,
            sender_id=self.local_peer_id,
            payload={'timestamp': datetime.now().isoformat()}
        ))
    
    async def send_transport_stop(self):
        """Send stop command"""
        await self._send_message(CollaborationMessage(
            type=MessageType.TRANSPORT_STOP,
            sender_id=self.local_peer_id,
            payload={'timestamp': datetime.now().isoformat()}
        ))
    
    async def send_transport_seek(self, position: float):
        """Send seek command"""
        await self._send_message(CollaborationMessage(
            type=MessageType.TRANSPORT_SEEK,
            sender_id=self.local_peer_id,
            payload={'position': position}
        ))
    
    async def send_tempo_change(self, tempo: float):
        """Send tempo change"""
        await self._send_message(CollaborationMessage(
            type=MessageType.TEMPO_CHANGE,
            sender_id=self.local_peer_id,
            payload={'tempo': tempo}
        ))
    
    async def send_chat(self, text: str):
        """Send chat message"""
        await self._send_message(CollaborationMessage(
            type=MessageType.CHAT_MESSAGE,
            sender_id=self.local_peer_id,
            payload={'text': text, 'name': self.local_peer_name}
        ))
    
    def get_peer_list(self) -> List[Peer]:
        """Get list of all peers"""
        return list(self.peers.values())
    
    def get_peer(self, peer_id: str) -> Optional[Peer]:
        """Get peer by ID"""
        return self.peers.get(peer_id)
    
    def get_peer_count(self) -> int:
        return len(self.peers)


class CollaborationServer:
    """Simple WebRTC signaling server (for local network)"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of peer_ids
        self.peer_info: Dict[str, Dict] = {}  # peer_id -> info
        self.server = None
    
    async def start(self):
        """Start signaling server"""
        import websockets
        
        async def handler(websocket, path):
            peer_id = None
            try:
                async for message in websocket:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'join':
                        peer_id = data['peer_id']
                        room_id = data['room_id']
                        peer_info = data.get('peer_info', {})
                        
                        if room_id not in self.rooms:
                            self.rooms[room_id] = set()
                        
                        self.rooms[room_id].add(peer_id)
                        self.peer_info[peer_id] = {
                            'websocket': websocket,
                            'room_id': room_id,
                            **peer_info
                        }
                        
                        # Notify others in room
                        await self._broadcast_to_room(room_id, {
                            'type': 'peer_joined',
                            'peer_id': peer_id,
                            'peer_info': peer_info
                        }, exclude=peer_id)
                        
                        # Send current peer list to new peer
                        peer_list = []
                        for pid in self.rooms[room_id]:
                            if pid != peer_id:
                                peer_list.append({
                                    'peer_id': pid,
                                    'peer_info': self.peer_info[pid]
                                })
                        
                        await websocket.send(json.dumps({
                            'type': 'peer_list',
                            'peers': peer_list
                        }))
                    
                    elif msg_type == 'signal':
                        # WebRTC signaling (offer/answer/ice)
                        target_id = data['target_id']
                        if target_id in self.peer_info:
                            await self.peer_info[target_id]['websocket'].send(json.dumps({
                                'type': 'signal',
                                'from': peer_id,
                                'data': data['data']
                            }))
                    
                    elif msg_type == 'message':
                        # Collaboration message
                        room_id = self.peer_info[peer_id]['room_id']
                        await self._broadcast_to_room(room_id, {
                            'type': 'message',
                            'from': peer_id,
                            'data': data['data']
                        }, exclude=peer_id)
            
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                if peer_id and peer_id in self.peer_info:
                    room_id = self.peer_info[peer_id]['room_id']
                    if room_id in self.rooms:
                        self.rooms[room_id].discard(peer_id)
                        await self._broadcast_to_room(room_id, {
                            'type': 'peer_left',
                            'peer_id': peer_id
                        })
                    del self.peer_info[peer_id]
        
        self.server = await websockets.serve(handler, self.host, self.port)
        print(f"Signaling server started on {self.host}:{self.port}")
    
    async def _broadcast_to_room(self, room_id: str, message: Dict, exclude: str = None):
        """Broadcast message to all peers in room"""
        if room_id not in self.rooms:
            return
        
        message_json = json.dumps(message)
        for peer_id in self.rooms[room_id]:
            if peer_id != exclude and peer_id in self.peer_info:
                try:
                    await self.peer_info[peer_id]['websocket'].send(message_json)
                except:
                    pass
    
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


# Demo/Testing
async def demo_collaboration():
    """Demo collaboration between two peers"""
    print("=== Collaboration Demo ===\n")
    
    # Create two peers
    peer1 = CollaborationManager("peer-1", "Alice", is_host=True)
    peer2 = CollaborationManager("peer-2", "Bob", is_host=False)
    
    # Track events
    peer1_events = []
    peer2_events = []
    
    def on_peer1_message(msg):
        peer1_events.append(msg)
        print(f"[Alice] Received: {msg.type.value}")
    
    def on_peer2_message(msg):
        peer2_events.append(msg)
        print(f"[Bob] Received: {msg.type.value}")
    
    peer1.on_message = on_peer1_message
    peer2.on_message = on_peer2_message
    
    # Join room
    await peer1.join_room("session-1")
    await peer2.join_room("session-1")
    
    # Simulate peer2 joining (in real impl, via signaling)
    join_msg = CollaborationMessage(
        type=MessageType.JOIN,
        sender_id="peer-2",
        payload={'peer_id': 'peer-2', 'name': 'Bob', 'color': '#4ECDC4'}
    )
    peer1.handle_message(join_msg)
    
    # Alice moves cursor
    await peer1.send_cursor_position(100, 200, track_id="track-1")
    
    # Bob receives cursor
    cursor_msg = CollaborationMessage(
        type=MessageType.CURSOR_POSITION,
        sender_id="peer-1",
        payload={'x': 100, 'y': 200, 'track_id': 'track-1'}
    )
    peer2.handle_message(cursor_msg)
    
    # Alice plays
    await peer1.send_transport_play()
    
    play_msg = CollaborationMessage(
        type=MessageType.TRANSPORT_PLAY,
        sender_id="peer-1",
        payload={'timestamp': datetime.now().isoformat()}
    )
    peer2.handle_message(play_msg)
    
    # Alice changes tempo
    await peer1.send_tempo_change(128.0)
    
    tempo_msg = CollaborationMessage(
        type=MessageType.TEMPO_CHANGE,
        sender_id="peer-1",
        payload={'tempo': 128.0}
    )
    peer2.handle_message(tempo_msg)
    
    # Chat
    await peer1.send_chat("Hey Bob, listen to this!")
    
    chat_msg = CollaborationMessage(
        type=MessageType.CHAT_MESSAGE,
        sender_id="peer-1",
        payload={'text': 'Hey Bob, listen to this!', 'name': 'Alice'}
    )
    peer2.handle_message(chat_msg)
    
    print(f"\nAlice peers: {[p.name for p in peer1.get_peer_list()]}")
    print(f"Bob peers: {[p.name for p in peer2.get_peer_list()]}")
    
    await peer1.leave_room()
    await peer2.leave_room()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_collaboration())