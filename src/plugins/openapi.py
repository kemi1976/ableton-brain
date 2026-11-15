"""
Ableton Brain - Phase 4: OpenAPI/Swagger Documentation
Auto-generated OpenAPI 3.0 spec from REST API routes
"""

import json
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, get_type_hints
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class OpenAPISpec:
    """OpenAPI 3.0 specification generator"""
    
    def __init__(self, title: str = "Ableton Brain API", version: str = "1.0.0"):
        self.spec = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": "Cross-DAW music production automation REST API with WebSocket support",
                "contact": {
                    "name": "KEMERTARIAN",
                    "url": "https://github.com/kemertarian/ableton-brain"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {"url": "http://localhost:8080", "description": "Development server"},
                {"url": "https://api.ableton-brain.local", "description": "Production server"}
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    },
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            },
            "security": [{"ApiKeyAuth": []}],
            "tags": []
        }
        
        self._tag_descriptions = {
            "health": "Health check endpoints",
            "daw": "DAW connection and management",
            "project": "Project operations",
            "tracks": "Track management",
            "devices": "Device/Instrument management",
            "transport": "Transport control",
            "clips": "MIDI clip operations",
            "controllers": "Hardware controller management",
            "quick": "Quick actions",
            "database": "Knowledge database",
            "machines": "Multi-machine orchestration",
            "collab": "Real-time collaboration",
            "projects": "Project sharing and marketplace",
            "templates": "Project templates",
            "learning": "Education and learning paths",
            "websocket": "WebSocket real-time updates",
            "plugins": "Plugin marketplace",
            "webhooks": "Webhook integrations",
            "i18n": "Internationalization",
            "mobile": "Mobile endpoints"
        }
    
    def add_tag(self, name: str, description: str = None):
        if name not in [t["name"] for t in self.spec["tags"]]:
            self.spec["tags"].append({
                "name": name,
                "description": description or self._tag_descriptions.get(name, "")
            })
    
    def add_path(self, path: str, method: str, operation: Dict):
        if path not in self.spec["paths"]:
            self.spec["paths"][path] = {}
        self.spec["paths"][path][method.lower()] = operation
    
    def add_schema(self, name: str, schema: Dict):
        self.spec["components"]["schemas"][name] = schema
    
    def to_dict(self) -> Dict:
        return self.spec
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.spec, indent=indent, default=str)
    
    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(self.to_json())


# Standard response schemas
def create_standard_schemas(spec: OpenAPISpec):
    spec.add_schema("APIResponse", {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "data": {},
            "error": {"type": "string", "nullable": True},
            "timestamp": {"type": "string", "format": "date-time"}
        },
        "required": ["success", "timestamp"]
    })
    
    spec.add_schema("ErrorResponse", {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [False]},
            "error": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"}
        },
        "required": ["success", "error", "timestamp"]
    })
    
    spec.add_schema("ProjectInfo", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "tempo": {"type": "number", "format": "float"},
            "time_signature": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
            "sample_rate": {"type": "integer"},
            "bit_depth": {"type": "integer"},
            "tracks": {"type": "array", "items": {"$ref": "#/components/schemas/TrackInfo"}}
        }
    })
    
    spec.add_schema("TrackInfo", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["midi", "audio", "return", "master", "group"]},
            "color": {"type": "string", "nullable": True},
            "volume": {"type": "number", "format": "float", "minimum": 0, "maximum": 1},
            "pan": {"type": "number", "format": "float", "minimum": -1, "maximum": 1},
            "mute": {"type": "boolean"},
            "solo": {"type": "boolean"},
            "armed": {"type": "boolean"},
            "devices": {"type": "array", "items": {"$ref": "#/components/schemas/DeviceInfo"}}
        }
    })
    
    spec.add_schema("DeviceInfo", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["instrument", "audio_effect", "midi_effect"]},
            "enabled": {"type": "boolean"},
            "parameters": {"type": "object", "additionalProperties": {"type": "number"}}
        }
    })
    
    spec.add_schema("ControllerInfo", {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "connected": {"type": "boolean"},
            "mapping": {"type": "string", "nullable": True}
        }
    })
    
    spec.add_schema("DAWInfo", {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "platform": {"type": "string"},
            "connected": {"type": "boolean"},
            "version": {"type": "string", "nullable": True}
        }
    })
    
    spec.add_schema("CollaborationPeer", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "color": {"type": "string"},
            "is_host": {"type": "boolean"},
            "cursor": {"type": "object", "nullable": True},
            "selection": {"type": "object", "nullable": True}
        }
    })
    
    spec.add_schema("SharedProject", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "owner_id": {"type": "string"},
            "visibility": {"type": "string", "enum": ["private", "link", "public"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "daw_compatible": {"type": "array", "items": {"type": "string"}},
            "download_count": {"type": "integer"},
            "fork_count": {"type": "integer"},
            "like_count": {"type": "integer"},
            "updated_at": {"type": "string", "format": "date-time"}
        }
    })
    
    spec.add_schema("Template", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "author": {"type": "string"},
            "estimated_time": {"type": "integer"},
            "required_plugins": {"type": "array", "items": {"type": "string"}},
            "tutorial_steps": {"type": "integer"}
        }
    })
    
    spec.add_schema("LearningPath", {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "level": {"type": "string"},
            "estimated_hours": {"type": "number"},
            "prerequisites": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "modules": {"type": "integer"}
        }
    })
    
    spec.add_schema("MachineInfo", {
        "type": "object",
        "properties": {
            "ip": {"type": "string"},
            "name": {"type": "string"},
            "role": {"type": "string"},
            "status": {"type": "string"},
            "capabilities": {"type": "array", "items": {"type": "string"}}
        }
    })


# Generate full OpenAPI spec from REST API
def generate_openapi_spec(api_instance) -> OpenAPISpec:
    """Generate OpenAPI spec from AbletonBrainAPI instance"""
    spec = OpenAPISpec()
    create_standard_schemas(spec)
    
    # Collect all routes
    routes_by_path = {}
    for route in api_instance.app.router.routes():
        resource = route.resource
        path = None
        
        if hasattr(resource, '_path'):
            path = resource._path
        elif hasattr(resource, '_pattern'):
            # DynamicResource - convert regex pattern to path template
            pattern = resource._pattern.pattern
            # Convert regex pattern to OpenAPI path template
            import re
            # Replace named groups like (?P<name>[^{}/]+) with {name}
            path = re.sub(r'\(\?P<(\w+)>[^)]+\)', r'{\1}', pattern)
            # Remove ^ and $ anchors
            path = path.replace('^', '').replace('$', '')
        
        if not path:
            continue
            
        method = route.method
        
        # Skip static files and non-API routes
        if not (path.startswith('/api/') or path == '/health' or path == '/ws'):
            continue
        
        # Get handler
        handler = route.handler
        if not handler:
            continue
        
        if path not in routes_by_path:
            routes_by_path[path] = {}
        routes_by_path[path][method] = handler
    
    # Generate operations for each path
    for path, methods in routes_by_path.items():
        tag = _get_tag_for_path(path)
        spec.add_tag(tag)
        
        for method, handler in methods.items():
            operation = _create_operation(handler, path, method, tag)
            spec.add_path(path, method, operation)
    
    return spec


def _get_tag_for_path(path: str) -> str:
    """Determine tag from path"""
    if path == '/health':
        return 'health'
    elif path.startswith('/api/daws'):
        return 'daw'
    elif path.startswith('/api/project') and '/tracks' not in path and '/clips' not in path:
        return 'project'
    elif path.startswith('/api/tracks'):
        return 'tracks'
    elif path.startswith('/api/transport'):
        return 'transport'
    elif path.startswith('/api/clips'):
        return 'clips'
    elif path.startswith('/api/controllers'):
        return 'controllers'
    elif path.startswith('/api/quick'):
        return 'quick'
    elif path.startswith('/api/database'):
        return 'database'
    elif path.startswith('/api/machines') or path.startswith('/api/tasks'):
        return 'machines'
    elif path.startswith('/api/collab'):
        return 'collab'
    elif path.startswith('/api/projects'):
        return 'projects'
    elif path.startswith('/api/templates'):
        return 'templates'
    elif path.startswith('/api/learning'):
        return 'learning'
    elif path.startswith('/api/plugins'):
        return 'plugins'
    elif path.startswith('/api/webhooks') or path.startswith('/api/integrations'):
        return 'webhooks'
    elif path.startswith('/api/i18n'):
        return 'i18n'
    elif path.startswith('/api/mobile'):
        return 'mobile'
    elif path == '/ws':
        return 'websocket'
    else:
        return 'other'


def _create_operation(handler, path: str, method: str, tag: str) -> Dict:
    """Create OpenAPI operation from handler"""
    # Get docstring
    doc = inspect.getdoc(handler) or ""
    summary = doc.split('\n')[0] if doc else f"{method} {path}"
    
    # Get parameters from path
    path_params = _extract_path_params(path)
    
    # Get request body schema
    request_body = _get_request_body_schema(handler, method)
    
    # Build operation
    operation = {
        "tags": [tag],
        "summary": summary,
        "description": doc,
        "operationId": f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}",
        "parameters": path_params,
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/APIResponse"}
                    }
                }
            },
            "400": {
                "description": "Bad request",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "401": {
                "description": "Unauthorized",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "500": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            }
        },
        "security": [{"ApiKeyAuth": []}]
    }
    
    if request_body:
        operation["requestBody"] = request_body
    
    return operation


def _extract_path_params(path: str) -> List[Dict]:
    """Extract path parameters from path template"""
    import re
    params = []
    for match in re.finditer(r'\{(\w+)\}', path):
        param_name = match.group(1)
        params.append({
            "name": param_name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
            "description": f"Path parameter: {param_name}"
        })
    return params


def _get_request_body_schema(handler, method: str) -> Optional[Dict]:
    """Infer request body schema from handler"""
    if method in ['GET', 'HEAD', 'DELETE']:
        return None
    
    # Try to get from type hints
    try:
        hints = get_type_hints(handler)
        if 'request' in hints:
            # This would need more sophisticated analysis
            pass
    except:
        pass
    
    # Default generic schema
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"type": "object", "additionalProperties": True}
            }
        }
    }


# WebSocket documentation
def add_websocket_docs(spec: OpenAPISpec):
    """Add WebSocket documentation"""
    spec.add_schema("WSMessage", {
        "type": "object",
        "properties": {
            "event": {"type": "string"},
            "data": {},
            "timestamp": {"type": "string", "format": "date-time"}
        }
    })
    
    spec.add_schema("WSCommand", {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "enum": ["ping", "subscribe"]},
            "topics": {"type": "array", "items": {"type": "string"}}
        }
    })
    
    # Add WebSocket path
    spec.add_path("/ws", "get", {
        "tags": ["websocket"],
        "summary": "WebSocket connection for real-time updates",
        "description": "Establish WebSocket connection for real-time events. Send JSON commands: {\"cmd\": \"ping\"} or {\"cmd\": \"subscribe\", \"topics\": [\"transport\", \"tracks\"]}",
        "operationId": "websocket_connect",
        "parameters": [],
        "responses": {
            "101": {
                "description": "Switching protocols - WebSocket connection established"
            }
        }
    })


# Save to file
def save_openapi_spec(api_instance, output_dir: Path):
    """Generate and save OpenAPI spec"""
    spec = generate_openapi_spec(api_instance)
    add_websocket_docs(spec)
    
    # Save JSON
    json_path = output_dir / "openapi.json"
    spec.save(json_path)
    
    # Save YAML (if pyyaml available)
    try:
        import yaml
        yaml_path = output_dir / "openapi.yaml"
        with open(yaml_path, 'w') as f:
            yaml.dump(spec.to_dict(), f, sort_keys=False, default_flow_style=False)
    except ImportError:
        yaml_path = None
    
    # Generate HTML docs (Redoc)
    html_path = output_dir / "docs.html"
    _generate_redoc_html(spec, html_path)
    
    print(f"OpenAPI spec saved:")
    print(f"  JSON: {json_path}")
    if yaml_path:
        print(f"  YAML: {yaml_path}")
    print(f"  HTML: {html_path}")
    
    return spec


def _generate_redoc_html(spec: OpenAPISpec, output_path: Path):
    """Generate Redoc HTML documentation"""
    spec_json = spec.to_json()
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Ableton Brain API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
    <script>
        var spec = {spec_json};
        Redoc.init(spec, {{
            scrollYOffset: 50,
            hideDownloadButton: false,
            hideLoading: false,
            nativeScrollbars: true,
            theme: {{
                colors: {{
                    primary: {{
                        main: '#6366f1'
                    }}
                }},
                typography: {{
                    fontSize: '14px',
                    lineHeight: '1.6',
                    code: {{
                        fontSize: '13px'
                    }}
                }},
                sidebar: {{
                    backgroundColor: '#0f172a'
                }}
            }}
        }}, document.getElementById('redoc'));
    </script>
</body>
</html>'''
    
    with open(output_path, 'w') as f:
        f.write(html)


# Swagger UI HTML
def generate_swagger_ui_html(output_path: Path, spec_url: str = "openapi.json"):
    """Generate Swagger UI HTML"""
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Ableton Brain API - Swagger UI</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
    <style>
        body {{ margin: 0; padding: 0; }}
        #swagger-ui {{ max-width: 1200px; margin: 0 auto; }}
        .topbar {{ display: none; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: '{spec_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.presets.standalone
                ],
                layout: "StandaloneLayout",
                displayRequestDuration: true,
                filter: true,
                tryItOutEnabled: true
            }});
        }};
    </script>
</body>
</html>'''
    
    with open(output_path, 'w') as f:
        f.write(html)


# CLI entry point
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
    
    from api.rest_api import AbletonBrainAPI
    
    api = AbletonBrainAPI()
    output_dir = Path(__file__).parent.parent.parent / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    spec = save_openapi_spec(api, output_dir)
    
    # Also generate Swagger UI
    swagger_path = output_dir / "swagger.html"
    generate_swagger_ui_html(swagger_path)
    print(f"Swagger UI: {swagger_path}")
    
    # Print stats
    print(f"\nSpec stats:")
    print(f"  Paths: {len(spec.spec['paths'])}")
    print(f"  Schemas: {len(spec.spec['components']['schemas'])}")
    print(f"  Tags: {len(spec.spec['tags'])}")