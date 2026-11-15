"""
Ableton Brain - Phase 4: REST API Server
Enables remote control via HTTP/WebSocket for web UI, mobile apps, and integrations
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from aiohttp import web, WSMsgType
from aiohttp.web import Request, Response, WebSocketResponse
import aiohttp_cors

from core.adapters import (
    BaseDAWAdapter, daw_registry, connect_daw, quick_action,
    DAWPlatform, TrackType, TrackInfo, DeviceInfo, ProjectInfo
)
from core.controllers import UniversalController, ControllerType as CtrlType
from core.universal_midi_translator import UniversalMIDITranslator
from core.project_format import UniversalProject, UniversalProjectSerializer, get_converter, UniversalTrack, UniversalDevice
from core.collaboration import CollaborationManager, MessageType, CollaborationMessage, CollaborationServer
from core.sharing import ProjectSharingManager, SharedProject, ProjectTemplate, LearningPath, LearningModule, SharePermission, ProjectVisibility, TutorialStep


@dataclass
class APIResponse:
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AbletonBrainAPI:
    """REST API and WebSocket server for Ableton Brain"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.translator = UniversalMIDITranslator()
        self.controller = UniversalController()
        self.ws_clients: set[WebSocketResponse] = set()
        # Collaboration
        self.collab_manager: Optional[CollaborationManager] = None
        # Project sharing
        self.sharing_manager = ProjectSharingManager(Path(__file__).parent.parent.parent / "data" / "sharing")
        self.setup_routes()
        self.setup_cors()

    def setup_cors(self):
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        for route in list(self.app.router.routes()):
            cors.add(route)

    def setup_routes(self):
        # Health check
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/api/status", self.get_status)

        # DAW management
        self.app.router.add_get("/api/daws", self.list_daws)
        self.app.router.add_post("/api/daws/{name}/connect", self.connect_daw)
        self.app.router.add_post("/api/daws/{name}/disconnect", self.disconnect_daw)
        self.app.router.add_get("/api/daws/active", self.get_active_daw)

        # Project operations
        self.app.router.add_get("/api/project", self.get_project)
        self.app.router.add_post("/api/project/save", self.save_project)
        self.app.router.add_post("/api/project/export", self.export_audio)

        # Track operations
        self.app.router.add_get("/api/tracks", self.list_tracks)
        self.app.router.add_post("/api/tracks", self.create_track)
        self.app.router.add_delete("/api/tracks/{track_id}", self.delete_track)
        self.app.router.add_patch("/api/tracks/{track_id}", self.update_track)
        self.app.router.add_post("/api/tracks/{track_id}/arm", self.arm_track)
        self.app.router.add_post("/api/tracks/{track_id}/solo", self.solo_track)
        self.app.router.add_post("/api/tracks/{track_id}/mute", self.mute_track)

        # Device/Instrument operations
        self.app.router.add_post("/api/tracks/{track_id}/instrument", self.load_instrument)
        self.app.router.add_post("/api/tracks/{track_id}/effects/audio", self.add_audio_effect)
        self.app.router.add_post("/api/tracks/{track_id}/effects/midi", self.add_midi_effect)
        self.app.router.add_get("/api/tracks/{track_id}/devices/{device_id}/params", self.get_device_params)
        self.app.router.add_patch("/api/tracks/{track_id}/devices/{device_id}/params", self.set_device_param)

        # Transport
        self.app.router.add_post("/api/transport/play", self.play)
        self.app.router.add_post("/api/transport/stop", self.stop)
        self.app.router.add_post("/api/transport/tempo", self.set_tempo)
        self.app.router.add_post("/api/transport/time-signature", self.set_time_signature)

        # MIDI clips
        self.app.router.add_post("/api/tracks/{track_id}/clips", self.create_clip)
        self.app.router.add_post("/api/clips/{clip_id}/quantize", self.quantize_clip)

        # Controller management
        self.app.router.add_get("/api/controllers", self.list_controllers)
        self.app.router.add_post("/api/controllers/detect", self.detect_controllers)
        self.app.router.add_post("/api/controllers/{type}/connect", self.connect_controller)
        self.app.router.add_post("/api/controllers/{type}/map", self.map_controller)

        # Quick actions
        self.app.router.add_post("/api/quick/{action}", self.quick_action)

        # Database/knowledge
        self.app.router.add_get("/api/database/stats", self.database_stats)
        self.app.router.add_get("/api/database/artists", self.list_artists)
        self.app.router.add_get("/api/database/genres", self.list_genres)
        self.app.router.add_get("/api/database/techniques", self.list_techniques)

        # Multi-machine
        self.app.router.add_get("/api/machines", self.list_machines)
        self.app.router.add_post("/api/tasks", self.create_task)
        self.app.router.add_get("/api/tasks", self.list_tasks)

        # Phase 3: Collaboration
        self.app.router.add_post("/api/collab/join", self.collab_join)
        self.app.router.add_post("/api/collab/leave", self.collab_leave)
        self.app.router.add_get("/api/collab/peers", self.collab_peers)
        self.app.router.add_post("/api/collab/cursor", self.collab_cursor)
        self.app.router.add_post("/api/collab/selection", self.collab_selection)
        self.app.router.add_post("/api/collab/transport", self.collab_transport)
        self.app.router.add_post("/api/collab/chat", self.collab_chat)
        self.app.router.add_get("/api/collab/state", self.collab_state)

        # Phase 3: Project Sharing
        self.app.router.add_post("/api/projects/share", self.share_project)
        self.app.router.add_get("/api/projects/shared", self.list_shared_projects)
        self.app.router.add_get("/api/projects/shared/{project_id}", self.get_shared_project)
        self.app.router.add_post("/api/projects/shared/{project_id}/fork", self.fork_project)
        self.app.router.add_post("/api/projects/export", self.export_project)
        self.app.router.add_post("/api/projects/import", self.import_project)

        # Phase 3: Templates & Education
        self.app.router.add_get("/api/templates", self.list_templates)
        self.app.router.add_get("/api/templates/{template_id}", self.get_template)
        self.app.router.add_post("/api/templates", self.create_template)
        self.app.router.add_post("/api/templates/{template_id}/create", self.create_from_template)
        self.app.router.add_get("/api/learning", self.list_learning_paths)
        self.app.router.add_get("/api/learning/{path_id}", self.get_learning_path)
        self.app.router.add_post("/api/learning", self.create_learning_path)

        # Phase 3: Universal Project Format
        self.app.router.add_post("/api/project/convert", self.convert_project)
        self.app.router.add_post("/api/project/universal", self.export_universal)
        self.app.router.add_post("/api/project/universal/import", self.import_universal)

        # Phase 4: Plugin Marketplace
        self.app.router.add_get("/api/plugins", self.list_marketplace_plugins)
        self.app.router.add_get("/api/plugins/{plugin_id}", self.get_marketplace_plugin)
        self.app.router.add_post("/api/plugins/{plugin_id}/install", self.install_plugin)
        self.app.router.add_post("/api/plugins/{plugin_id}/uninstall", self.uninstall_plugin)
        self.app.router.add_post("/api/plugins/{plugin_id}/enable", self.enable_plugin)
        self.app.router.add_post("/api/plugins/{plugin_id}/disable", self.disable_plugin)
        self.app.router.add_get("/api/plugins/installed", self.list_installed_plugins)
        self.app.router.add_get("/api/plugins/updates", self.check_plugin_updates)
        self.app.router.add_post("/api/plugins/{plugin_id}/review", self.add_plugin_review)
        self.app.router.add_get("/api/plugins/{plugin_id}/reviews", self.get_plugin_reviews)
        self.app.router.add_post("/api/plugins/package", self.create_plugin_package)
        
        # Phase 4: Webhooks & Integrations
        self.app.router.add_post("/api/webhooks", self.create_webhook)
        self.app.router.add_get("/api/webhooks", self.list_webhooks)
        self.app.router.add_get("/api/webhooks/{webhook_id}", self.get_webhook)
        self.app.router.add_patch("/api/webhooks/{webhook_id}", self.update_webhook)
        self.app.router.add_delete("/api/webhooks/{webhook_id}", self.delete_webhook)
        self.app.router.add_get("/api/webhooks/{webhook_id}/deliveries", self.get_webhook_deliveries)
        self.app.router.add_get("/api/webhooks/stats", self.get_webhook_stats)
        self.app.router.add_post("/api/integrations/zapier/spec", self.get_zapier_spec)
        self.app.router.add_post("/api/integrations/zapier/webhook", self.register_zapier_webhook)
        
        # Phase 4: OpenAPI Documentation
        self.app.router.add_get("/api/docs/openapi.json", self.get_openapi_spec)
        self.app.router.add_get("/api/docs/swagger", self.get_swagger_ui)
        self.app.router.add_get("/api/docs/redoc", self.get_redoc_ui)
        
        # Phase 4: Internationalization
        self.app.router.add_get("/api/i18n/locales", self.list_locales)
        self.app.router.add_get("/api/i18n/translate", self.translate_text)
        self.app.router.add_get("/api/i18n/stats", self.get_i18n_stats)
        self.app.router.add_post("/api/i18n/locale", self.set_locale)
        
        # Phase 4: Mobile endpoints
        self.app.router.add_get("/api/mobile/status", self.mobile_status)
        self.app.router.add_post("/api/mobile/quick", self.mobile_quick_action)
        self.app.router.add_get("/api/mobile/projects", self.mobile_list_projects)
        
        # WebSocket for real-time updates
        self.app.router.add_get("/ws", self.websocket_handler)

        # Static files for web UI
        self.app.router.add_static("/ui", Path(__file__).parent.parent.parent / "web_ui", show_index=True)

    # Helper methods
    def _get_active_adapter(self) -> Optional[BaseDAWAdapter]:
        return daw_registry.get_active()

    def _json_response(self, success: bool, data: Any = None, error: str = None) -> Response:
        return web.json_response(asdict(APIResponse(success=success, data=data, error=error)))

    async def _broadcast(self, event: str, data: Any):
        """Broadcast to all WebSocket clients"""
        if self.ws_clients:
            msg = json.dumps({"event": event, "data": data, "timestamp": datetime.now().isoformat()})
            for ws in self.ws_clients.copy():
                try:
                    await ws.send_str(msg)
                except:
                    self.ws_clients.discard(ws)

    # Route handlers
    async def health_check(self, request: Request) -> Response:
        return self._json_response(True, {"status": "ok", "service": "Ableton Brain API"})

    async def get_status(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        return self._json_response(True, {
            "active_daw": adapter.daw_name if adapter else None,
            "connected": adapter.connected if adapter else False,
            "controllers": len(self.controller.supported_controllers) if hasattr(self.controller, 'supported_controllers') else 0,
            "daws_available": daw_registry.list_available(),
        })

    # DAW management
    async def list_daws(self, request: Request) -> Response:
        return self._json_response(True, {
            "available": daw_registry.list_available(),
            "active": daw_registry.get_active().daw_name if daw_registry.get_active() else None
        })

    async def connect_daw(self, request: Request) -> Response:
        name = request.match_info['name']
        success = await connect_daw(name)
        if success:
            await self._broadcast("daw_connected", {"daw": name})
        return self._json_response(success, {"daw": name}, None if success else "Failed to connect")

    async def disconnect_daw(self, request: Request) -> Response:
        name = request.match_info['name']
        adapter = daw_registry.get(name)
        if adapter:
            await adapter.disconnect()
            await self._broadcast("daw_disconnected", {"daw": name})
            return self._json_response(True, {"daw": name})
        return self._json_response(False, error="DAW not found")

    async def get_active_daw(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if adapter:
            return self._json_response(True, {"name": adapter.daw_name, "connected": adapter.connected})
        return self._json_response(False, error="No active DAW")

    # Project operations
    async def get_project(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        project = await adapter.get_project_info()
        return self._json_response(True, asdict(project) if project else None)

    async def save_project(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        data = await request.json()
        path = data.get("path")
        success = await adapter.save_project(path)
        return self._json_response(success, None if success else "Save failed")

    async def export_audio(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        data = await request.json()
        success = await adapter.export_audio(
            data.get("path", "export.wav"),
            data.get("format", "wav"),
            data.get("sample_rate", 44100),
            data.get("bit_depth", 24)
        )
        return self._json_response(success, None if success else "Export failed")

    # Track operations
    async def list_tracks(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        project = await adapter.get_project_info()
        if project:
            return self._json_response(True, [asdict(t) for t in project.tracks])
        return self._json_response(True, [])

    async def create_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        data = await request.json()
        track_id = await adapter.create_track(
            data.get("name", "New Track"),
            TrackType(data.get("type", "midi"))
        )
        await self._broadcast("track_created", {"track_id": track_id, "name": data.get("name")})
        return self._json_response(True, {"track_id": track_id})

    async def delete_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        success = await adapter.delete_track(track_id)
        if success:
            await self._broadcast("track_deleted", {"track_id": track_id})
        return self._json_response(success, None if success else "Delete failed")

    async def update_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()

        results = {}
        if "name" in data:
            results["rename"] = await adapter.rename_track(track_id, data["name"])
        if "volume" in data:
            results["volume"] = await adapter.set_track_volume(track_id, data["volume"])
        if "pan" in data:
            results["pan"] = await adapter.set_track_pan(track_id, data["pan"])
        if "armed" in data:
            results["arm"] = await adapter.arm_track(track_id, data["armed"])
        if "solo" in data:
            results["solo"] = await adapter.solo_track(track_id, data["solo"])
        if "mute" in data:
            results["mute"] = await adapter.mute_track(track_id, data["mute"])

        await self._broadcast("track_updated", {"track_id": track_id, "changes": data})
        return self._json_response(True, results)

    async def arm_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.arm_track(track_id, data.get("arm", True))
        return self._json_response(success)

    async def solo_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.solo_track(track_id, data.get("solo", True))
        return self._json_response(success)

    async def mute_track(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.mute_track(track_id, data.get("mute", True))
        return self._json_response(success)

    # Device operations
    async def load_instrument(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.load_instrument(track_id, data["instrument"], data.get("preset"))
        return self._json_response(success)

    async def add_audio_effect(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.add_audio_effect(track_id, data["effect"], data.get("position", -1))
        return self._json_response(success)

    async def add_midi_effect(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        success = await adapter.add_midi_effect(track_id, data["effect"], data.get("position", -1))
        return self._json_response(success)

    async def get_device_params(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        device_id = request.match_info['device_id']
        params = await adapter.get_device_parameters(track_id, device_id)
        return self._json_response(True, params)

    async def set_device_param(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        device_id = request.match_info['device_id']
        data = await request.json()
        success = await adapter.set_device_parameter(track_id, device_id, data["param"], data["value"])
        return self._json_response(success)

    # Transport
    async def play(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        success = await adapter.start_playback()
        await self._broadcast("transport", {"action": "play"})
        return self._json_response(success)

    async def stop(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        success = await adapter.stop_playback()
        await self._broadcast("transport", {"action": "stop"})
        return self._json_response(success)

    async def set_tempo(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        data = await request.json()
        success = await adapter.set_tempo(data["tempo"])
        await self._broadcast("tempo_changed", {"tempo": data["tempo"]})
        return self._json_response(success)

    async def set_time_signature(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        data = await request.json()
        success = await adapter.set_time_signature(data["numerator"], data["denominator"])
        return self._json_response(success)

    # MIDI clips
    async def create_clip(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        track_id = request.match_info['track_id']
        data = await request.json()
        clip_id = await adapter.create_clip(
            track_id,
            data["start_time"],
            data["duration"],
            data["notes"]
        )
        return self._json_response(True, {"clip_id": clip_id})

    async def quantize_clip(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")
        clip_id = request.match_info['clip_id']
        data = await request.json()
        success = await adapter.quantize_clip(clip_id, data.get("grid", "1/16"))
        return self._json_response(success)

    # Controllers
    async def list_controllers(self, request: Request) -> Response:
        return self._json_response(True, {
            "supported": [c.value for c in CtrlType],
            "connected": list(self.controller.supported_controllers.keys()) if hasattr(self.controller, 'supported_controllers') else []
        })

    async def detect_controllers(self, request: Request) -> Response:
        detected = await self.controller.auto_detect()
        return self._json_response(True, detected)

    async def connect_controller(self, request: Request) -> Response:
        ctrl_type = request.match_info['type']
        try:
            ctrl_enum = CtrlType(ctrl_type)
        except ValueError:
            return self._json_response(False, error="Unknown controller type")

        success = await self.controller.connect(ctrl_enum)
        if success:
            await self._broadcast("controller_connected", {"type": ctrl_type})
        return self._json_response(success, {"type": ctrl_type} if success else None)

    async def map_controller(self, request: Request) -> Response:
        ctrl_type = request.match_info['type']
        data = await request.json()
        preset = data.get("preset", "ableton_mixer")
        # This would apply mapping to active controller
        return self._json_response(True, {"mapping": preset})

    # Quick actions
    async def quick_action(self, request: Request) -> Response:
        action = request.match_info['action']
        data = await request.json() if request.can_read_body else {}
        success = await quick_action(action, **data)
        return self._json_response(success)

    # Database
    async def database_stats(self, request: Request) -> Response:
        db = self.translator.database
        return self._json_response(True, {
            "artists": len(db.get('artists', {})),
            "genres": len(self.translator.get_genres()),
            "engineers": len(db.get('engineers', {})),
            "techniques": len(db.get('techniques', {}))
        })

    async def list_artists(self, request: Request) -> Response:
        return self._json_response(True, list(self.translator.database.get('artists', {}).keys()))

    async def list_genres(self, request: Request) -> Response:
        return self._json_response(True, self.translator.get_genres())

    async def list_techniques(self, request: Request) -> Response:
        return self._json_response(True, list(self.translator.database.get('techniques', {}).keys()))

    # Multi-machine
    async def list_machines(self, request: Request) -> Response:
        try:
            from Services.task_orchestrator import TaskOrchestrator
            orchestrator = TaskOrchestrator()
            status = orchestrator.get_status()
            return self._json_response(True, status["machines"])
        except:
            return self._json_response(True, {})

    async def create_task(self, request: Request) -> Response:
        try:
            from Services.task_orchestrator import create_task_from_template
            data = await request.json()
            task = create_task_from_template(data["template"])
            return self._json_response(True, {"task_id": task.id, "name": task.name})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def list_tasks(self, request: Request) -> Response:
        try:
            from Services.task_orchestrator import TaskOrchestrator
            orchestrator = TaskOrchestrator()
            status = orchestrator.get_status()
            return self._json_response(True, {
                "pending": status["pending"],
                "completed": status["recent_completed"]
            })
        except:
            return self._json_response(True, {"pending": [], "completed": []})

    # WebSocket
    async def websocket_handler(self, request: Request) -> WebSocketResponse:
        ws = WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)

        await ws.send_str(json.dumps({
            "event": "connected",
            "data": {"message": "Welcome to Ableton Brain API"},
            "timestamp": datetime.now().isoformat()
        }))

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    # Handle incoming commands
                    await self._handle_ws_command(ws, data)
                except json.JSONDecodeError:
                    pass
            elif msg.type == WSMsgType.ERROR:
                break

        self.ws_clients.discard(ws)
        return ws

    async def _handle_ws_command(self, ws: WebSocketResponse, data: Dict):
        cmd = data.get("cmd")
        if cmd == "ping":
            await ws.send_str(json.dumps({"event": "pong", "timestamp": datetime.now().isoformat()}))
        elif cmd == "subscribe":
            # Could implement event subscriptions here
            await ws.send_str(json.dumps({"event": "subscribed", "topics": data.get("topics", [])}))

    # Phase 3: Collaboration handlers
    async def collab_join(self, request: Request) -> Response:
        data = await request.json()
        room_id = data.get("room_id", "default")
        peer_name = data.get("name", f"User-{uuid.uuid4().hex[:6]}")
        is_host = data.get("is_host", False)

        peer_id = str(uuid.uuid4())

        if not self.collab_manager or self.collab_manager.room_id != room_id:
            self.collab_manager = CollaborationManager(peer_id, peer_name, is_host)
            await self.collab_manager.join_room(room_id)

        return self._json_response(True, {
            "peer_id": peer_id,
            "room_id": room_id,
            "is_host": is_host
        })

    async def collab_leave(self, request: Request) -> Response:
        if self.collab_manager:
            await self.collab_manager.leave_room()
            self.collab_manager = None
        return self._json_response(True)

    async def collab_peers(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(True, {"peers": []})

        peers = []
        for peer in self.collab_manager.get_peer_list():
            peers.append({
                "id": peer.id,
                "name": peer.name,
                "color": peer.color,
                "is_host": peer.is_host,
                "cursor": peer.cursor_position,
                "selection": peer.selection
            })
        return self._json_response(True, {"peers": peers})

    async def collab_cursor(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(False, error="Not in a collaboration session")
        data = await request.json()
        await self.collab_manager.send_cursor_position(
            data["x"], data["y"],
            data.get("track_id"),
            data.get("clip_id")
        )
        return self._json_response(True)

    async def collab_selection(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(False, error="Not in a collaboration session")
        data = await request.json()
        await self.collab_manager.send_selection(data["type"], data["ids"])
        return self._json_response(True)

    async def collab_transport(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(False, error="Not in a collaboration session")
        data = await request.json()
        action = data.get("action")

        if action == "play":
            await self.collab_manager.send_transport_play()
        elif action == "stop":
            await self.collab_manager.send_transport_stop()
        elif action == "seek":
            await self.collab_manager.send_transport_seek(data["position"])
        elif action == "tempo":
            await self.collab_manager.send_tempo_change(data["tempo"])

        return self._json_response(True)

    async def collab_chat(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(False, error="Not in a collaboration session")
        data = await request.json()
        await self.collab_manager.send_chat(data["text"])
        return self._json_response(True)

    async def collab_state(self, request: Request) -> Response:
        if not self.collab_manager:
            return self._json_response(True, {"connected": False})
        return self._json_response(True, {
            "connected": self.collab_manager.connected,
            "room_id": self.collab_manager.room_id,
            "peer_count": self.collab_manager.get_peer_count(),
            "local_peer_id": self.collab_manager.local_peer_id
        })

    # Phase 3: Project Sharing handlers
    async def share_project(self, request: Request) -> Response:
        data = await request.json()
        project_data = data.get("project_data")
        if not project_data:
            return self._json_response(False, error="project_data required")

        project = self.sharing_manager.create_shared_project(
            name=data.get("name", "Untitled"),
            owner_id=data.get("owner_id", "anonymous"),
            project_data=project_data,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            visibility=ProjectVisibility(data.get("visibility", "private"))
        )
        return self._json_response(True, {"project_id": project.id, "name": project.name})

    async def list_shared_projects(self, request: Request) -> Response:
        owner_id = request.query.get("owner_id")
        visibility = request.query.get("visibility")
        tags = request.query.get("tags", "").split(",") if request.query.get("tags") else None

        projects = self.sharing_manager.list_projects(
            owner_id=owner_id,
            visibility=ProjectVisibility(visibility) if visibility else None,
            tags=tags
        )

        return self._json_response(True, {
            "projects": [{
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "owner_id": p.owner_id,
                "visibility": p.visibility.value,
                "tags": p.tags,
                "daw_compatible": p.daw_compatible,
                "download_count": p.download_count,
                "fork_count": p.fork_count,
                "like_count": p.like_count,
                "updated_at": p.updated_at
            } for p in projects]
        })

    async def get_shared_project(self, request: Request) -> Response:
        project_id = request.match_info['project_id']
        project = self.sharing_manager.get_project(project_id)
        if not project:
            return self._json_response(False, error="Project not found")

        project.download_count += 1
        self.sharing_manager._save_project(project)

        return self._json_response(True, {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
            "visibility": project.visibility.value,
            "tags": project.tags,
            "daw_origin": project.daw_origin,
            "daw_compatible": project.daw_compatible,
            "download_count": project.download_count,
            "fork_count": project.fork_count,
            "like_count": project.like_count,
            "version": project.version,
            "project_data": project.project_data,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        })

    async def fork_project(self, request: Request) -> Response:
        project_id = request.match_info['project_id']
        data = await request.json()

        fork = self.sharing_manager.fork_project(
            project_id,
            data.get("owner_id", "anonymous"),
            data.get("name")
        )
        if not fork:
            return self._json_response(False, error="Original project not found")

        return self._json_response(True, {"project_id": fork.id, "name": fork.name})

    async def export_project(self, request: Request) -> Response:
        data = await request.json()
        project_id = data.get("project_id")
        output_path = data.get("output_path")

        if not project_id or not output_path:
            return self._json_response(False, error="project_id and output_path required")

        success = self.sharing_manager.export_project_package(project_id, Path(output_path))
        return self._json_response(success, {"path": output_path} if success else None)

    async def import_project(self, request: Request) -> Response:
        data = await request.json()
        package_path = data.get("package_path")
        owner_id = data.get("owner_id", "anonymous")

        if not package_path:
            return self._json_response(False, error="package_path required")

        project = self.sharing_manager.import_project_package(Path(package_path), owner_id)
        if not project:
            return self._json_response(False, error="Import failed")

        return self._json_response(True, {"project_id": project.id, "name": project.name})

    # Phase 3: Templates & Education handlers
    async def list_templates(self, request: Request) -> Response:
        category = request.query.get("category")
        difficulty = request.query.get("difficulty")
        tags = request.query.get("tags", "").split(",") if request.query.get("tags") else None

        templates = self.sharing_manager.list_templates(category, difficulty, tags)

        return self._json_response(True, {
            "templates": [{
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "difficulty": t.difficulty,
                "tags": t.tags,
                "author": t.author,
                "estimated_time": t.estimated_time,
                "required_plugins": t.required_plugins,
                "tutorial_steps": len(t.tutorial_steps)
            } for t in templates]
        })

    async def get_template(self, request: Request) -> Response:
        template_id = request.match_info['template_id']
        template = self.sharing_manager.get_template(template_id)
        if not template:
            return self._json_response(False, error="Template not found")

        return self._json_response(True, {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "difficulty": template.difficulty,
            "tags": template.tags,
            "author": template.author,
            "estimated_time": template.estimated_time,
            "required_plugins": template.required_plugins,
            "project_data": template.project_data,
            "tutorial_steps": [asdict(s) for s in template.tutorial_steps]
        })

    async def create_template(self, request: Request) -> Response:
        data = await request.json()

        tutorial_steps = []
        for step_data in data.get("tutorial_steps", []):
            tutorial_steps.append(TutorialStep(**step_data))

        template = self.sharing_manager.create_template(
            name=data["name"],
            description=data.get("description", ""),
            project_data=data["project_data"],
            category=data.get("category", ""),
            difficulty=data.get("difficulty", "beginner"),
            tags=data.get("tags", []),
            author=data.get("author", "anonymous"),
            tutorial_steps=tutorial_steps,
            required_plugins=data.get("required_plugins", [])
        )

        return self._json_response(True, {"template_id": template.id, "name": template.name})

    async def create_from_template(self, request: Request) -> Response:
        template_id = request.match_info['template_id']
        data = await request.json()

        project = self.sharing_manager.create_project_from_template(
            template_id,
            data.get("owner_id", "anonymous"),
            data.get("name")
        )

        if not project:
            return self._json_response(False, error="Template not found")

        return self._json_response(True, {"project_id": project.id, "name": project.name})

    async def list_learning_paths(self, request: Request) -> Response:
        level = request.query.get("level")
        tags = request.query.get("tags", "").split(",") if request.query.get("tags") else None

        paths = self.sharing_manager.list_learning_paths(level, tags)

        return self._json_response(True, {
            "paths": [{
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "level": p.level,
                "estimated_hours": p.estimated_hours,
                "prerequisites": p.prerequisites,
                "tags": p.tags,
                "modules": len(p.modules)
            } for p in paths]
        })

    async def get_learning_path(self, request: Request) -> Response:
        path_id = request.match_info['path_id']
        path = self.sharing_manager.get_learning_path(path_id)
        if not path:
            return self._json_response(False, error="Learning path not found")

        return self._json_response(True, {
            "id": path.id,
            "name": path.name,
            "description": path.description,
            "level": path.level,
            "estimated_hours": path.estimated_hours,
            "prerequisites": path.prerequisites,
            "tags": path.tags,
            "modules": [asdict(m) for m in path.modules]
        })

    async def create_learning_path(self, request: Request) -> Response:
        data = await request.json()

        modules = []
        for m_data in data.get("modules", []):
            modules.append(LearningModule(**m_data))

        path = self.sharing_manager.create_learning_path(
            name=data["name"],
            description=data.get("description", ""),
            level=data.get("level", "beginner"),
            modules=modules,
            prerequisites=data.get("prerequisites", []),
            tags=data.get("tags", [])
        )

        return self._json_response(True, {"path_id": path.id, "name": path.name})

    # Phase 3: Universal Project Format handlers
    async def convert_project(self, request: Request) -> Response:
        data = await request.json()
        input_path = data.get("input_path")
        output_path = data.get("output_path")
        target_daw = data.get("target_daw")

        if not input_path or not output_path:
            return self._json_response(False, error="input_path and output_path required")

        from core.project_format import convert_project
        success = convert_project(Path(input_path), Path(output_path), target_daw)

        return self._json_response(success, {"output_path": output_path} if success else None)

    async def export_universal(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")

        # Get project from DAW
        project_info = await adapter.get_project_info()
        if not project_info:
            return self._json_response(False, error="No project open")

        # Convert to universal format
        universal = UniversalProject(
            name=project_info.name,
            tempo=project_info.tempo,
            time_signature_numerator=project_info.time_signature[0],
            time_signature_denominator=project_info.time_signature[1],
            sample_rate=project_info.sample_rate,
            bit_depth=project_info.bit_depth
        )

        for track_info in project_info.tracks:
            track = UniversalTrack(
                id=track_info.id,
                name=track_info.name,
                type=track_info.type.value,
                color=track_info.color,
                volume=track_info.volume,
                pan=track_info.pan,
                mute=track_info.mute,
                solo=track_info.solo,
                armed=track_info.armed
            )
            # Add devices
            for device in track_info.devices:
                track.devices.append(UniversalDevice(
                    name=device.name,
                    type=device.type,
                    plugin_format="vst3",
                    plugin_id=device.id,
                    enabled=device.enabled
                ))
            universal.tracks.append(track)

        return self._json_response(True, {"project": asdict(universal)})

    async def import_universal(self, request: Request) -> Response:
        adapter = self._get_active_adapter()
        if not adapter:
            return self._json_response(False, error="No active DAW")

        data = await request.json()
        universal_data = data.get("project")
        if not universal_data:
            return self._json_response(False, error="project data required")

        # This would create tracks, devices, clips in the DAW
        # For now, return the structure
        return self._json_response(True, {"imported": True, "tracks": len(universal_data.get("tracks", []))})

    # ===== Phase 4: Plugin Marketplace =====
    
    async def list_marketplace_plugins(self, request: Request) -> Response:
        """List available plugins from marketplace"""
        try:
            from plugins.marketplace import PluginMarketplace, PluginCategory
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            category = request.query.get("category")
            search = request.query.get("search")
            
            plugins = marketplace.search_plugins(
                query=search or "",
                category=PluginCategory(category) if category else None
            )
            
            return self._json_response(True, {
                "plugins": [asdict(p) for p in plugins],
                "total": len(plugins)
            })
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_marketplace_plugin(self, request: Request) -> Response:
        """Get detailed info for a marketplace plugin"""
        plugin_id = request.match_info.get("plugin_id")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            plugin = marketplace.get_listing(plugin_id)
            if not plugin:
                return self._json_response(False, error="Plugin not found", status=404)
            
            return self._json_response(True, asdict(plugin))
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def install_plugin(self, request: Request) -> Response:
        """Install a plugin from marketplace"""
        plugin_id = request.match_info.get("plugin_id")
        data = await request.json()
        version = data.get("version")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            result = marketplace.install_plugin(plugin_id, version)
            return self._json_response(True, {"installed": asdict(result)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def uninstall_plugin(self, request: Request) -> Response:
        """Uninstall a plugin"""
        plugin_id = request.match_info.get("plugin_id")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            result = marketplace.uninstall_plugin(plugin_id)
            return self._json_response(True, {"uninstalled": result})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def enable_plugin(self, request: Request) -> Response:
        """Enable an installed plugin"""
        plugin_id = request.match_info.get("plugin_id")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            result = marketplace.enable_plugin(plugin_id)
            return self._json_response(True, {"enabled": result})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def disable_plugin(self, request: Request) -> Response:
        """Disable an installed plugin"""
        plugin_id = request.match_info.get("plugin_id")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            result = marketplace.disable_plugin(plugin_id)
            return self._json_response(True, {"disabled": result})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def list_installed_plugins(self, request: Request) -> Response:
        """List installed plugins"""
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            plugins = marketplace.list_installed()
            return self._json_response(True, {
                "plugins": [asdict(p) for p in plugins],
                "total": len(plugins)
            })
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def check_plugin_updates(self, request: Request) -> Response:
        """Check for plugin updates"""
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            updates = marketplace.get_updates()
            return self._json_response(True, {"updates": updates, "total": len(updates)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def add_plugin_review(self, request: Request) -> Response:
        """Add a review for a plugin"""
        plugin_id = request.match_info.get("plugin_id")
        data = await request.json()
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            review = marketplace.add_review(
                plugin_id=plugin_id,
                user_id=data.get("user_id", "anonymous"),
                rating=data.get("rating", 5),
                title=data.get("title", ""),
                body=data.get("comment", "")
            )
            return self._json_response(True, {"review": asdict(review)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_plugin_reviews(self, request: Request) -> Response:
        """Get reviews for a plugin"""
        plugin_id = request.match_info.get("plugin_id")
        
        try:
            from plugins.marketplace import PluginMarketplace
            from pathlib import Path
            
            marketplace = PluginMarketplace(
                marketplace_dir=Path(__file__).parent.parent.parent / 'data' / 'marketplace',
                plugins_dir=Path(__file__).parent.parent.parent / 'data' / 'plugins'
            )
            
            reviews = marketplace.get_reviews(plugin_id)
            return self._json_response(True, {"reviews": [asdict(r) for r in reviews], "total": len(reviews)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def create_plugin_package(self, request: Request) -> Response:
        """Create a plugin package for distribution"""
        data = await request.json()
        
        try:
            from plugins.marketplace import PluginMarketplace, create_plugin_template
            from pathlib import Path
            
            source_dir = Path(data.get("source_dir", "."))
            output_path = Path(__file__).parent.parent.parent / 'data' / 'marketplace' / f"{data.get('name', 'plugin')}.abp"
            
            # Create plugin package
            success = PluginMarketplace.create_package(source_dir, output_path)
            if success:
                return self._json_response(True, {"package": str(output_path)})
            else:
                return self._json_response(False, error="Failed to create package")
        except Exception as e:
            return self._json_response(False, error=str(e))

    # ===== Phase 4: Webhooks & Integrations =====
    
    async def create_webhook(self, request: Request) -> Response:
        """Create a webhook"""
        data = await request.json()
        
        try:
            from plugins.webhooks import WebhookManager, WebhookEvent, WebhookConfig
            
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            endpoint = WebhookEndpoint(
                name=data.get("name", "Webhook"),
                url=data["url"],
                events=[WebhookEvent(e) for e in data.get("events", [])],
                secret=data.get("secret"),
                headers=data.get("headers", {}),
                retry_count=data.get("retry_count", 3),
                retry_delay=data.get("retry_delay", 1.0),
                timeout=data.get("timeout", 10.0),
                filters=data.get("filter", {})
            )
            
            registered = webhook_manager.register_endpoint(endpoint)
            return self._json_response(True, {"webhook": asdict(registered)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def list_webhooks(self, request: Request) -> Response:
        """List all webhooks"""
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            webhooks = webhook_manager.list_endpoints(active_only=False)
            return self._json_response(True, {"webhooks": [asdict(w) for w in webhooks], "total": len(webhooks)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_webhook(self, request: Request) -> Response:
        """Get a specific webhook"""
        webhook_id = request.match_info.get("webhook_id")
        
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            webhook = webhook_manager.get_endpoint(webhook_id)
            
            if not webhook:
                return self._json_response(False, error="Webhook not found", status=404)
            
            return self._json_response(True, {"webhook": asdict(webhook)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def update_webhook(self, request: Request) -> Response:
        """Update a webhook"""
        webhook_id = request.match_info.get("webhook_id")
        data = await request.json()
        
        try:
            from plugins.webhooks import WebhookManager, WebhookEvent
            
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            updates = {}
            if "name" in data:
                updates["name"] = data["name"]
            if "url" in data:
                updates["url"] = data["url"]
            if "events" in data:
                updates["events"] = [WebhookEvent(e) for e in data["events"]]
            if "secret" in data:
                updates["secret"] = data["secret"]
            if "headers" in data:
                updates["headers"] = data["headers"]
            if "active" in data:
                updates["active"] = data["active"]
            if "retry_count" in data:
                updates["retry_count"] = data["retry_count"]
            if "retry_delay" in data:
                updates["retry_delay"] = data["retry_delay"]
            if "timeout" in data:
                updates["timeout"] = data["timeout"]
            if "filters" in data:
                updates["filters"] = data["filters"]
            
            webhook = webhook_manager.update_endpoint(webhook_id, **updates)
            return self._json_response(True, {"webhook": asdict(webhook)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def delete_webhook(self, request: Request) -> Response:
        """Delete a webhook"""
        webhook_id = request.match_info.get("webhook_id")
        
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            result = webhook_manager.delete_endpoint(webhook_id)
            return self._json_response(True, {"deleted": result})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_webhook_deliveries(self, request: Request) -> Response:
        """Get webhook delivery history"""
        webhook_id = request.match_info.get("webhook_id")
        limit = int(request.query.get("limit", 50))
        
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            deliveries = webhook_manager.get_delivery_history(webhook_id, limit)
            return self._json_response(True, {"deliveries": [asdict(d) for d in deliveries], "total": len(deliveries)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_webhook_stats(self, request: Request) -> Response:
        """Get webhook statistics"""
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            stats = webhook_manager.get_stats()
            return self._json_response(True, stats)
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_zapier_spec(self, request: Request) -> Response:
        """Get Zapier CLI spec"""
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            spec = webhook_manager.generate_zapier_spec()
            return self._json_response(True, spec)
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def register_zapier_webhook(self, request: Request) -> Response:
        """Register webhook for Zapier"""
        data = await request.json()
        
        try:
            from plugins.webhooks import WebhookManager
            webhook_manager = WebhookManager(Path(__file__).parent.parent.parent / 'data' / 'webhooks')
            
            webhook = webhook_manager.register_zapier_webhook(
                zapier_webhook_url=data["zapier_webhook_url"],
                events=data.get("events")
            )
            return self._json_response(True, {"webhook": asdict(webhook)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    # ===== Phase 4: OpenAPI Documentation =====
    
    async def get_openapi_spec(self, request: Request) -> Response:
        """Get OpenAPI specification"""
        try:
            from plugins.openapi import generate_openapi_spec, save_openapi_spec
            from pathlib import Path
            
            spec = generate_openapi_spec(self)
            return self._json_response(True, spec.to_dict())
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_swagger_ui(self, request: Request) -> Response:
        """Serve Swagger UI"""
        try:
            from plugins.openapi import generate_swagger_ui_html
            from pathlib import Path
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                generate_swagger_ui_html(Path(f.name), "openapi.json")
                with open(f.name, 'r') as html_file:
                    html_content = html_file.read()
            
            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_redoc_ui(self, request: Request) -> Response:
        """Serve ReDoc UI"""
        try:
            from plugins.openapi import save_openapi_spec
            from pathlib import Path
            import tempfile
            
            spec = generate_openapi_spec(self)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                from plugins.openapi import _generate_redoc_html
                _generate_redoc_html(spec, Path(f.name))
                with open(f.name, 'r') as html_file:
                    html_content = html_file.read()
            
            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            return self._json_response(False, error=str(e))

    # ===== Phase 4: Internationalization =====
    
    async def list_locales(self, request: Request) -> Response:
        """List available locales"""
        try:
            from plugins.i18n import SupportedLocale, LOCALE_INFO
            
            locales = []
            for locale in SupportedLocale:
                info = LOCALE_INFO[locale]
                locales.append({
                    "code": info.code,
                    "name": info.name,
                    "native_name": info.native_name,
                    "rtl": info.rtl,
                    "currency": info.currency,
                    "region": info.region
                })
            
            return self._json_response(True, {"locales": locales})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def translate_text(self, request: Request) -> Response:
        """Translate text"""
        key = request.query.get("key")
        locale = request.query.get("locale")
        count = request.query.get("count")
        params = {}
        
        # Get query params as format variables
        for k, v in request.query.items():
            if k not in ["key", "locale", "count"]:
                params[k] = v
        
        try:
            from plugins.i18n import I18nManager
            from pathlib import Path
            
            locales_dir = Path(__file__).parent.parent.parent / "locales"
            i18n = I18nManager(locales_dir)
            
            if count:
                result = i18n.t_plural(key, int(count), locale, **params)
            else:
                result = i18n.t(key, locale, **params)
            
            return self._json_response(True, {"translation": result, "locale": locale or i18n.default_locale})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def get_i18n_stats(self, request: Request) -> Response:
        """Get i18n completion stats"""
        try:
            from plugins.i18n import I18nManager
            from pathlib import Path
            
            locales_dir = Path(__file__).parent.parent.parent / "locales"
            i18n = I18nManager(locales_dir)
            
            stats = i18n.get_completion_stats()
            return self._json_response(True, {"stats": stats})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def set_locale(self, request: Request) -> Response:
        """Set user locale preference"""
        data = await request.json()
        locale = data.get("locale")
        
        try:
            from plugins.i18n import I18nManager, SupportedLocale
            from pathlib import Path
            
            locales_dir = Path(__file__).parent.parent.parent / "locales"
            i18n = I18nManager(locales_dir)
            
            if i18n.set_locale(locale):
                return self._json_response(True, {"locale": locale, "success": True})
            else:
                return self._json_response(False, error="Invalid locale")
        except Exception as e:
            return self._json_response(False, error=str(e))

    # ===== Phase 4: Mobile endpoints =====
    
    async def mobile_status(self, request: Request) -> Response:
        """Get mobile-optimized status"""
        daw = self._get_active_adapter()
        if not daw:
            return self._json_response(True, {"connected": False})
        
        try:
            info = await daw.get_daw_info()
            return self._json_response(True, {
                "connected": True,
                "daw": info.name,
                "tempo": info.tempo if hasattr(info, 'tempo') else 120,
                "playing": info.is_playing if hasattr(info, 'is_playing') else False
            })
        except:
            return self._json_response(True, {"connected": True, "daw": "Unknown"})

    async def mobile_quick_action(self, request: Request) -> Response:
        """Execute quick action from mobile"""
        data = await request.json()
        action = data.get("action")
        
        daw = self._get_active_adapter()
        if not daw:
            return self._json_response(False, error="No DAW connected")
        
        try:
            if action == "play":
                await daw.start_transport()
            elif action == "stop":
                await daw.stop_transport()
            elif action == "record":
                await daw.record_transport()
            elif action == "undo":
                await daw.undo()
            elif action == "redo":
                await daw.redo()
            elif action == "tap_tempo":
                # Tap tempo implementation
                pass
            else:
                return self._json_response(False, error=f"Unknown action: {action}")
            
            return self._json_response(True, {"action": action, "success": True})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def mobile_list_projects(self, request: Request) -> Response:
        """List projects for mobile"""
        try:
            from core.project_format import ProjectManager
            
            manager = ProjectManager()
            projects = manager.list_projects()
            
            # Simplified for mobile
            mobile_projects = [
                {
                    "id": p.id,
                    "name": p.name,
                    "modified": p.updated_at if hasattr(p, 'updated_at') else None,
                    "daw": p.daw_compatible[0] if p.daw_compatible else None
                }
                for p in projects
            ]
            
            return self._json_response(True, {"projects": mobile_projects, "total": len(mobile_projects)})
        except Exception as e:
            return self._json_response(False, error=str(e))

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"🌐 Ableton Brain API running at http://{self.host}:{self.port}")
        print(f"   WebSocket: ws://{self.host}:{self.port}/ws")
        print(f"   Web UI: http://{self.host}:{self.port}/ui")
        return runner

    async def stop(self):
        for ws in self.ws_clients:
            await ws.close()
        self.ws_clients.clear()


async def main():
    api = AbletonBrainAPI()
    runner = await api.start()

    try:
        await asyncio.Event().wait()  # Run forever
    except KeyboardInterrupt:
        pass
    finally:
        await api.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
