"""
Ableton Brain - Phase 4: Webhook & Integration System
Zapier, Make, n8n, and custom webhook integrations
"""

import asyncio
import json
import hmac
import hashlib
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict
import aiohttp


class WebhookEvent(Enum):
    """Available webhook events"""
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    PROJECT_EXPORTED = "project.exported"
    
    # Track events
    TRACK_CREATED = "track.created"
    TRACK_UPDATED = "track.updated"
    TRACK_DELETED = "track.deleted"
    TRACK_ARMED = "track.armed"
    
    # Clip events
    CLIP_CREATED = "clip.created"
    CLIP_UPDATED = "clip.updated"
    CLIP_DELETED = "clip.deleted"
    
    # Transport events
    TRANSPORT_PLAY = "transport.play"
    TRANSPORT_STOP = "transport.stop"
    TRANSPORT_SEEK = "transport.seek"
    TEMPO_CHANGED = "tempo.changed"
    TIME_SIGNATURE_CHANGED = "time_signature.changed"
    
    # Device events
    DEVICE_LOADED = "device.loaded"
    DEVICE_UPDATED = "device.updated"
    DEVICE_REMOVED = "device.removed"
    
    # Controller events
    CONTROLLER_CONNECTED = "controller.connected"
    CONTROLLER_DISCONNECTED = "controller.disconnected"
    CONTROLLER_MAPPED = "controller.mapped"
    
    # Collaboration events
    COLLAB_PEER_JOINED = "collab.peer_joined"
    COLLAB_PEER_LEFT = "collab.peer_left"
    COLLAB_CURSOR = "collab.cursor"
    COLLAB_TRANSPORT = "collab.transport"
    
    # Sharing events
    PROJECT_SHARED = "project.shared"
    PROJECT_FORKED = "project.forked"
    TEMPLATE_CREATED = "template.created"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    url: str = ""
    events: List[WebhookEvent] = field(default_factory=list)
    secret: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    active: bool = True
    retry_count: int = 3
    retry_delay: float = 1.0  # seconds
    timeout: float = 10.0  # seconds
    headers: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)  # Event filtering
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_triggered: Optional[str] = None
    last_success: Optional[str] = None
    last_error: Optional[str] = None
    failure_count: int = 0


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    endpoint_id: str = ""
    event: WebhookEvent = WebhookEvent.CUSTOM
    payload: Dict = field(default_factory=dict)
    attempt: int = 1
    status: str = "pending"  # pending, success, failed, retrying
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class ZapierAction:
    """Zapier action definition"""
    key: str
    name: str
    description: str
    input_fields: List[Dict] = field(default_factory=list)
    output_fields: List[Dict] = field(default_factory=list)
    perform: Callable = None  # Function to execute


@dataclass
class ZapierTrigger:
    """Zapier trigger definition"""
    key: str
    name: str
    description: str
    input_fields: List[Dict] = field(default_factory=list)
    output_fields: List[Dict] = field(default_factory=list)
    event_types: List[WebhookEvent] = field(default_factory=list)


class WebhookManager:
    """Manages webhook endpoints and deliveries"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.endpoints_file = self.storage_path / "webhooks.json"
        self.deliveries_file = self.storage_path / "deliveries.json"
        
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: List[WebhookDelivery] = []
        self._event_handlers: Dict[WebhookEvent, List[Callable]] = defaultdict(list)
        
        self._load_data()
    
    def _load_data(self):
        if self.endpoints_file.exists():
            with open(self.endpoints_file) as f:
                data = json.load(f)
                for item in data:
                    item['events'] = [WebhookEvent(e) for e in item['events']]
                    self._endpoints[item['id']] = WebhookEndpoint(**item)
        
        if self.deliveries_file.exists():
            with open(self.deliveries_file) as f:
                data = json.load(f)
                for item in data:
                    item['event'] = WebhookEvent(item['event'])
                    self._deliveries.append(WebhookDelivery(**item))
    
    def _save_endpoints(self):
        data = []
        for ep in self._endpoints.values():
            item = asdict(ep)
            item['events'] = [e.value for e in ep.events]
            data.append(item)
        with open(self.endpoints_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _save_deliveries(self):
        # Keep last 10000 deliveries
        if len(self._deliveries) > 10000:
            self._deliveries = self._deliveries[-10000:]
        
        data = []
        for d in self._deliveries:
            item = asdict(d)
            item['event'] = d.event.value
            data.append(item)
        with open(self.deliveries_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def register_endpoint(self, name: str, url: str, events: List[WebhookEvent],
                          secret: str = None, headers: Dict = None,
                          filters: Dict = None) -> WebhookEndpoint:
        """Register a new webhook endpoint"""
        endpoint = WebhookEndpoint(
            name=name,
            url=url,
            events=events,
            secret=secret or uuid.uuid4().hex[:32],
            headers=headers or {},
            filters=filters or {}
        )
        self._endpoints[endpoint.id] = endpoint
        self._save_endpoints()
        return endpoint
    
    def update_endpoint(self, endpoint_id: str, updates: Dict) -> Optional[WebhookEndpoint]:
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return None
        
        for key, value in updates.items():
            if key == 'events' and value:
                value = [WebhookEvent(e) if isinstance(e, str) else e for e in value]
            if hasattr(endpoint, key):
                setattr(endpoint, key, value)
        
        endpoint.updated_at = datetime.now().isoformat()
        self._save_endpoints()
        return endpoint
    
    def delete_endpoint(self, endpoint_id: str) -> bool:
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            self._save_endpoints()
            return True
        return False
    
    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        return self._endpoints.get(endpoint_id)
    
    def list_endpoints(self, active_only: bool = True) -> List[WebhookEndpoint]:
        endpoints = list(self._endpoints.values())
        if active_only:
            endpoints = [e for e in endpoints if e.active]
        return endpoints
    
    def get_endpoints_for_event(self, event: WebhookEvent) -> List[WebhookEndpoint]:
        """Get all active endpoints subscribed to an event"""
        return [
            e for e in self._endpoints.values()
            if e.active and event in e.events
        ]
    
    async def trigger_event(self, event: WebhookEvent, payload: Dict,
                            source_id: str = None) -> List[WebhookDelivery]:
        """Trigger webhook for an event"""
        endpoints = self.get_endpoints_for_event(event)
        
        # Apply filters
        filtered_endpoints = []
        for ep in endpoints:
            if self._matches_filters(ep, payload):
                filtered_endpoints.append(ep)
        
        deliveries = []
        for ep in filtered_endpoints:
            delivery = await self._deliver(ep, event, payload)
            deliveries.append(delivery)
        
        return deliveries
    
    def _matches_filters(self, endpoint: WebhookEndpoint, payload: Dict) -> bool:
        """Check if payload matches endpoint filters"""
        for key, expected in endpoint.filters.items():
            actual = payload.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                # Operator-based filtering
                for op, val in expected.items():
                    if op == "equals" and actual != val:
                        return False
                    elif op == "contains" and val not in str(actual):
                        return False
                    elif op == "gt" and not (actual > val):
                        return False
                    elif op == "lt" and not (actual < val):
                        return False
            elif actual != expected:
                return False
        return True
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for payload"""
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    
    async def _deliver(self, endpoint: WebhookEndpoint, event: WebhookEvent,
                       payload: Dict) -> WebhookDelivery:
        """Deliver webhook to endpoint with retries"""
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            event=event,
            payload=payload
        )
        self._deliveries.append(delivery)
        
        # Prepare request
        body = json.dumps({
            "event": event.value,
            "timestamp": datetime.now().isoformat(),
            "data": payload
        })
        
        headers = {
            "Content-Type": "application/json",
            "X-Abelton-Brain-Event": event.value,
            "X-Abelton-Brain-Signature": self._sign_payload(body, endpoint.secret),
            "X-Abelton-Brain-Delivery": delivery.id,
            **endpoint.headers
        }
        
        for attempt in range(1, endpoint.retry_count + 1):
            delivery.attempt = attempt
            delivery.status = "retrying" if attempt > 1 else "pending"
            
            try:
                timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(endpoint.url, data=body, headers=headers) as resp:
                        delivery.response_code = resp.status
                        delivery.response_body = await resp.text()
                        
                        if 200 <= resp.status < 300:
                            delivery.status = "success"
                            delivery.completed_at = datetime.now().isoformat()
                            endpoint.last_success = datetime.now().isoformat()
                            endpoint.failure_count = 0
                            break
                        else:
                            delivery.error = f"HTTP {resp.status}: {delivery.response_body}"
            
            except asyncio.TimeoutError:
                delivery.error = f"Timeout after {endpoint.timeout}s"
            except Exception as e:
                delivery.error = str(e)
            
            # Wait before retry
            if attempt < endpoint.retry_count:
                await asyncio.sleep(endpoint.retry_delay * attempt)
        
        if delivery.status != "success":
            delivery.status = "failed"
            delivery.completed_at = datetime.now().isoformat()
            endpoint.last_error = delivery.error
            endpoint.failure_count += 1
            
            # Auto-disable after 10 consecutive failures
            if endpoint.failure_count >= 10:
                endpoint.active = False
        
        endpoint.last_triggered = datetime.now().isoformat()
        self._save_endpoints()
        self._save_deliveries()
        
        return delivery
    
    def get_deliveries(self, endpoint_id: str = None, event: WebhookEvent = None,
                       status: str = None, limit: int = 100) -> List[WebhookDelivery]:
        """Get delivery history"""
        results = self._deliveries
        
        if endpoint_id:
            results = [d for d in results if d.endpoint_id == endpoint_id]
        if event:
            results = [d for d in results if d.event == event]
        if status:
            results = [d for d in results if d.status == status]
        
        return results[-limit:]
    
    def get_stats(self) -> Dict:
        """Get webhook statistics"""
        total = len(self._deliveries)
        success = len([d for d in self._deliveries if d.status == "success"])
        failed = len([d for d in self._deliveries if d.status == "failed"])
        
        return {
            "total_endpoints": len(self._endpoints),
            "active_endpoints": len([e for e in self._endpoints.values() if e.active]),
            "total_deliveries": total,
            "successful_deliveries": success,
            "failed_deliveries": failed,
            "success_rate": success / total if total > 0 else 0,
            "events_configured": list(set(e for ep in self._endpoints.values() for e in ep.events))
        }


class ZapierIntegration:
    """Zapier/Make/n8n integration"""
    
    def __init__(self, webhook_manager: WebhookManager):
        self.webhook_manager = webhook_manager
        self.triggers: Dict[str, ZapierTrigger] = {}
        self.actions: Dict[str, ZapierAction] = {}
        
        self._register_default_triggers()
        self._register_default_actions()
    
    def _register_default_triggers(self):
        """Register standard Zapier triggers"""
        self.triggers["new_project"] = ZapierTrigger(
            key="new_project",
            name="New Project",
            description="Triggers when a new project is created",
            event_types=[WebhookEvent.PROJECT_CREATED],
            input_fields=[
                {"key": "owner_id", "label": "Owner ID", "type": "string", "required": False}
            ],
            output_fields=[
                {"key": "project_id", "label": "Project ID", "type": "string"},
                {"key": "name", "label": "Name", "type": "string"},
                {"key": "tempo", "label": "Tempo", "type": "number"},
                {"key": "created_at", "label": "Created At", "type": "datetime"}
            ]
        )
        
        self.triggers["transport_play"] = ZapierTrigger(
            key="transport_play",
            name="Playback Started",
            description="Triggers when playback starts",
            event_types=[WebhookEvent.TRANSPORT_PLAY],
            output_fields=[
                {"key": "position", "label": "Position (beats)", "type": "number"},
                {"key": "tempo", "label": "Tempo", "type": "number"}
            ]
        )
        
        self.triggers["new_track"] = ZapierTrigger(
            key="new_track",
            name="New Track",
            description="Triggers when a track is created",
            event_types=[WebhookEvent.TRACK_CREATED],
            output_fields=[
                {"key": "track_id", "label": "Track ID", "type": "string"},
                {"key": "name", "label": "Track Name", "type": "string"},
                {"key": "type", "label": "Track Type", "type": "string"}
            ]
        )
        
        self.triggers["tempo_changed"] = ZapierTrigger(
            key="tempo_changed",
            name="Tempo Changed",
            description="Triggers when project tempo changes",
            event_types=[WebhookEvent.TEMPO_CHANGED],
            output_fields=[
                {"key": "tempo", "label": "New Tempo", "type": "number"},
                {"key": "previous_tempo", "label": "Previous Tempo", "type": "number"}
            ]
        )
        
        self.triggers["collab_peer_joined"] = ZapierTrigger(
            key="collab_peer_joined",
            name="Collaborator Joined",
            description="Triggers when a peer joins a collaboration session",
            event_types=[WebhookEvent.COLLAB_PEER_JOINED],
            output_fields=[
                {"key": "peer_id", "label": "Peer ID", "type": "string"},
                {"key": "peer_name", "label": "Peer Name", "type": "string"},
                {"key": "room_id", "label": "Room ID", "type": "string"}
            ]
        )
    
    def _register_default_actions(self):
        """Register standard Zapier actions"""
        self.actions["create_project"] = ZapierAction(
            key="create_project",
            name="Create Project",
            description="Create a new project",
            input_fields=[
                {"key": "name", "label": "Project Name", "type": "string", "required": True},
                {"key": "tempo", "label": "Tempo", "type": "number", "required": False, "default": 120},
                {"key": "time_signature", "label": "Time Signature", "type": "string", "required": False, "default": "4/4"},
                {"key": "template_id", "label": "Template ID", "type": "string", "required": False}
            ],
            output_fields=[
                {"key": "project_id", "label": "Project ID", "type": "string"},
                {"key": "name", "label": "Name", "type": "string"}
            ],
            perform=self._action_create_project
        )
        
        self.actions["set_tempo"] = ZapierAction(
            key="set_tempo",
            name="Set Tempo",
            description="Set project tempo",
            input_fields=[
                {"key": "project_id", "label": "Project ID", "type": "string", "required": True},
                {"key": "tempo", "label": "Tempo", "type": "number", "required": True}
            ],
            output_fields=[
                {"key": "success", "label": "Success", "type": "boolean"},
                {"key": "tempo", "label": "New Tempo", "type": "number"}
            ],
            perform=self._action_set_tempo
        )
        
        self.actions["create_track"] = ZapierAction(
            key="create_track",
            name="Create Track",
            description="Create a new track in a project",
            input_fields=[
                {"key": "project_id", "label": "Project ID", "type": "string", "required": True},
                {"key": "name", "label": "Track Name", "type": "string", "required": True},
                {"key": "type", "label": "Track Type", "type": "string", "required": False, "default": "midi", "choices": ["midi", "audio", "return", "master"]}
            ],
            output_fields=[
                {"key": "track_id", "label": "Track ID", "type": "string"},
                {"key": "name", "label": "Name", "type": "string"}
            ],
            perform=self._action_create_track
        )
        
        self.actions["trigger_transport"] = ZapierAction(
            key="trigger_transport",
            name="Control Transport",
            description="Play, stop, or seek playback",
            input_fields=[
                {"key": "action", "label": "Action", "type": "string", "required": True, "choices": ["play", "stop", "seek"]},
                {"key": "position", "label": "Position (beats)", "type": "number", "required": False}
            ],
            output_fields=[
                {"key": "success", "label": "Success", "type": "boolean"},
                {"key": "action", "label": "Action", "type": "string"}
            ],
            perform=self._action_trigger_transport
        )
        
        self.actions["export_audio"] = ZapierAction(
            key="export_audio",
            name="Export Audio",
            description="Export project audio",
            input_fields=[
                {"key": "project_id", "label": "Project ID", "type": "string", "required": True},
                {"key": "format", "label": "Format", "type": "string", "required": False, "default": "wav", "choices": ["wav", "mp3", "flac"]},
                {"key": "sample_rate", "label": "Sample Rate", "type": "number", "required": False, "default": 44100}
            ],
            output_fields=[
                {"key": "success", "label": "Success", "type": "boolean"},
                {"key": "file_path", "label": "File Path", "type": "string"}
            ],
            perform=self._action_export_audio
        )
    
    # Action implementations (to be connected to actual DAW)
    
    async def _action_create_project(self, input_data: Dict) -> Dict:
        """Create project via REST API"""
        # This would call the REST API
        return {"success": True, "project_id": "new-project-id", "name": input_data.get("name")}
    
    async def _action_set_tempo(self, input_data: Dict) -> Dict:
        return {"success": True, "tempo": input_data.get("tempo")}
    
    async def _action_create_track(self, input_data: Dict) -> Dict:
        return {"success": True, "track_id": "new-track-id", "name": input_data.get("name")}
    
    async def _action_trigger_transport(self, input_data: Dict) -> Dict:
        return {"success": True, "action": input_data.get("action")}
    
    async def _action_export_audio(self, input_data: Dict) -> Dict:
        return {"success": True, "file_path": "/exports/project.wav"}
    
    def get_triggers(self) -> List[Dict]:
        """Get triggers for Zapier CLI"""
        return [
            {
                "key": t.key,
                "noun": t.name,
                "display": {
                    "label": t.name,
                    "description": t.description
                },
                "operation": {
                    "inputFields": t.input_fields,
                    "outputFields": t.output_fields,
                    "perform": "webhook_trigger"  # Webhook-based
                }
            }
            for t in self.triggers.values()
        ]
    
    def get_actions(self) -> List[Dict]:
        """Get actions for Zapier CLI"""
        return [
            {
                "key": a.key,
                "noun": a.name,
                "display": {
                    "label": a.name,
                    "description": a.description
                },
                "operation": {
                    "inputFields": a.input_fields,
                    "outputFields": a.output_fields,
                    "perform": a.key
                }
            }
            for a in self.actions.values()
        ]
    
    def generate_zapier_spec(self) -> Dict:
        """Generate Zapier platform specification"""
        return {
            "version": "1.0.0",
            "platformVersion": "12.0.0",
            "authentication": {
                "type": "custom",
                "fields": [
                    {"key": "webhook_url", "label": "Webhook URL", "type": "string", "required": True},
                    {"key": "secret", "label": "Webhook Secret", "type": "string", "required": True}
                ]
            },
            "triggers": self.get_triggers(),
            "actions": self.get_actions(),
            "searches": []
        }
    
    def register_webhook_for_trigger(self, trigger_key: str, webhook_url: str,
                                     secret: str = None) -> WebhookEndpoint:
        """Register webhook endpoint for a Zapier trigger"""
        trigger = self.triggers.get(trigger_key)
        if not trigger:
            raise ValueError(f"Unknown trigger: {trigger_key}")
        
        return self.webhook_manager.register_endpoint(
            name=f"Zapier: {trigger.name}",
            url=webhook_url,
            events=trigger.event_types,
            secret=secret,
            headers={"X-Zapier-Trigger": trigger_key}
        )


class IntegrationTemplates:
    """Pre-built integration templates for popular services"""
    
    @staticmethod
    def get_templates() -> List[Dict]:
        return [
            {
                "id": "zapier_google_sheets",
                "name": "Log Projects to Google Sheets",
                "description": "Automatically log new projects to a Google Sheet",
                "service": "zapier",
                "trigger": "new_project",
                "action": "google_sheets.create_row",
                "field_mapping": {
                    "project_id": "Project ID",
                    "name": "Project Name",
                    "tempo": "Tempo",
                    "created_at": "Created Date"
                }
            },
            {
                "id": "slack_notifications",
                "name": "Slack Notifications",
                "description": "Send Slack messages on project events",
                "service": "webhook",
                "trigger": "project.created",
                "webhook_url": "https://hooks.slack.com/services/...",
                "payload_template": {
                    "text": "🎵 New project: {{name}} ({{tempo}} BPM)",
                    "blocks": [
                        {"type": "section", "text": {"type": "mrkdwn", "text": "*New Project Created*"}},
                        {"type": "section", "fields": [
                            {"type": "mrkdwn", "text": "*Name:*\n{{name}}"},
                            {"type": "mrkdwn", "text": "*Tempo:*\n{{tempo}} BPM"}
                        ]}
                    ]
                }
            },
            {
                "id": "discord_notifications",
                "name": "Discord Notifications",
                "description": "Post to Discord channel on transport events",
                "service": "webhook",
                "trigger": "transport.play",
                "webhook_url": "https://discord.com/api/webhooks/...",
                "payload_template": {
                    "content": "▶️ Playback started at {{position}} beats"
                }
            },
            {
                "id": "notion_project_db",
                "name": "Notion Project Database",
                "description": "Sync projects to Notion database",
                "service": "make",
                "trigger": "project.created",
                "action": "notion.create_page",
                "field_mapping": {
                    "name": "Name",
                    "tempo": "Tempo",
                    "time_signature": "Time Signature"
                }
            },
            {
                "id": "github_issues",
                "name": "GitHub Issues for Project Tasks",
                "description": "Create GitHub issues from project templates",
                "service": "zapier",
                "trigger": "template.created",
                "action": "github.create_issue",
                "field_mapping": {
                    "title": "Issue Title",
                    "description": "Issue Body"
                }
            }
        ]
    
    @staticmethod
    def create_integration(template_id: str, config: Dict) -> Dict:
        """Create integration from template"""
        templates = {t["id"]: t for t in IntegrationTemplates.get_templates()}
        if template_id not in templates:
            raise ValueError(f"Unknown template: {template_id}")
        
        return {
            "template": templates[template_id],
            "config": config,
            "created_at": datetime.now().isoformat()
        }


# Event emitter for internal events
class EventEmitter:
    """Simple event emitter for Ableton Brain events"""
    
    def __init__(self):
        self._listeners: Dict[WebhookEvent, List[Callable]] = defaultdict(list)
    
    def on(self, event: WebhookEvent, callback: Callable):
        self._listeners[event].append(callback)
    
    def off(self, event: WebhookEvent, callback: Callable):
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)
    
    async def emit(self, event: WebhookEvent, data: Dict):
        # Call internal listeners
        for callback in self._listeners[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                print(f"Event listener error: {e}")
        
        # Trigger webhooks (requires webhook_manager reference)
        # This would be called via webhook_manager.trigger_event


# Demo
if __name__ == "__main__":
    import tempfile
    
    async def demo():
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp) / "webhooks"
            wm = WebhookManager(storage)
            
            # Register endpoint
            ep = wm.register_endpoint(
                name="Test Webhook",
                url="https://httpbin.org/post",
                events=[WebhookEvent.PROJECT_CREATED, WebhookEvent.TRANSPORT_PLAY]
            )
            print(f"Registered: {ep.name} ({ep.id})")
            
            # Test trigger
            deliveries = await wm.trigger_event(
                WebhookEvent.PROJECT_CREATED,
                {"project_id": "proj-1", "name": "My Track", "tempo": 128}
            )
            print(f"Deliveries: {len(deliveries)}")
            
            # Zapier integration
            zi = ZapierIntegration(wm)
            spec = zi.generate_zapier_spec()
            print(f"Zapier spec: {len(spec['triggers'])} triggers, {len(spec['actions'])} actions")
            
            # Templates
            templates = IntegrationTemplates.get_templates()
            print(f"Integration templates: {len(templates)}")
    
    asyncio.run(demo())