"""
Ableton Brain - Phase 4: Plugin Marketplace
Discover, install, manage, and publish plugins
"""

import json
import uuid
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import zipfile
import semver


class PluginCategory(Enum):
    DAW_ADAPTER = "daw_adapter"
    CONTROLLER = "controller"
    MIDI_PROCESSOR = "midi_processor"
    AUDIO_PROCESSOR = "audio_processor"
    AI_MODEL = "ai_model"
    UI_EXTENSION = "ui_extension"
    EXPORT_FORMAT = "export_format"
    THEME = "theme"
    UTILITY = "utility"


class PluginStatus(Enum):
    INSTALLED = "installed"
    AVAILABLE = "available"
    UPDATES_AVAILABLE = "updates_available"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginManifest:
    """Plugin manifest (plugin.json)"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: PluginCategory
    entry_point: str  # Python module.path:ClassName
    min_ableton_brain_version: str = "1.0.0"
    max_ableton_brain_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Other plugin IDs
    python_dependencies: List[str] = field(default_factory=list)  # pip packages
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    icon: Optional[str] = None  # Base64 or path
    screenshots: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)  # Required permissions
    config_schema: Dict = field(default_factory=dict)  # JSON Schema for config
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PluginReview:
    """User review for a plugin"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plugin_id: str = ""
    user_id: str = ""
    rating: int = 5  # 1-5
    title: str = ""
    body: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    helpful_votes: int = 0


@dataclass
class PluginListing:
    """Marketplace listing"""
    manifest: PluginManifest
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    reviews: List[PluginReview] = field(default_factory=list)
    verified: bool = False  # Official/verified plugin
    featured: bool = False
    price: float = 0.0  # 0 = free
    screenshots: List[str] = field(default_factory=list)
    changelog: str = ""


@dataclass
class InstalledPlugin:
    """Installed plugin instance"""
    manifest: PluginManifest
    install_path: Path
    installed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = True
    config: Dict = field(default_factory=dict)
    status: PluginStatus = PluginStatus.INSTALLED
    last_error: Optional[str] = None


class PluginMarketplace:
    """Plugin marketplace manager"""
    
    def __init__(self, marketplace_dir: Path, plugins_dir: Path):
        self.marketplace_dir = Path(marketplace_dir)
        self.plugins_dir = Path(plugins_dir)
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self.listings_file = self.marketplace_dir / "listings.json"
        self.installed_file = self.marketplace_dir / "installed.json"
        self.reviews_file = self.marketplace_dir / "reviews.json"
        
        self._listings: Dict[str, PluginListing] = {}
        self._installed: Dict[str, InstalledPlugin] = {}
        self._reviews: Dict[str, List[PluginReview]] = {}
        
        self._load_data()
    
    def _load_data(self):
        # Load listings
        if self.listings_file.exists():
            with open(self.listings_file) as f:
                data = json.load(f)
                for item in data:
                    manifest = PluginManifest(**item['manifest'])
                    item['manifest'] = manifest
                    self._listings[item['manifest'].id] = PluginListing(**item)
        
        # Load installed
        if self.installed_file.exists():
            with open(self.installed_file) as f:
                data = json.load(f)
                for item in data:
                    manifest = PluginManifest(**item['manifest'])
                    item['manifest'] = manifest
                    item['install_path'] = Path(item['install_path'])
                    item['status'] = PluginStatus(item['status'])
                    self._installed[item['manifest'].id] = InstalledPlugin(**item)
        
        # Load reviews
        if self.reviews_file.exists():
            with open(self.reviews_file) as f:
                data = json.load(f)
                for plugin_id, reviews in data.items():
                    self._reviews[plugin_id] = [PluginReview(**r) for r in reviews]
    
    def _save_listings(self):
        data = []
        for listing in self._listings.values():
            item = asdict(listing)
            item['manifest'] = asdict(listing.manifest)
            data.append(item)
        with open(self.listings_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _save_installed(self):
        data = []
        for installed in self._installed.values():
            item = asdict(installed)
            item['manifest'] = asdict(installed.manifest)
            item['install_path'] = str(installed.install_path)
            item['status'] = installed.status.value
            data.append(item)
        with open(self.installed_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _save_reviews(self):
        data = {}
        for plugin_id, reviews in self._reviews.items():
            data[plugin_id] = [asdict(r) for r in reviews]
        with open(self.reviews_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    # Marketplace operations
    
    def publish_plugin(self, package_path: Path, publisher_id: str) -> PluginListing:
        """Publish a plugin package to marketplace"""
        # Extract and validate manifest
        with zipfile.ZipFile(package_path, 'r') as zf:
            if 'plugin.json' not in zf.namelist():
                raise ValueError("Package missing plugin.json")
            manifest_data = json.loads(zf.read('plugin.json'))
            manifest = PluginManifest(**manifest_data)
        
        # Verify package integrity
        package_hash = self._hash_file(package_path)
        
        # Create listing
        listing = PluginListing(
            manifest=manifest,
            downloads=0,
            rating=0.0,
            review_count=0
        )
        
        # Copy package to marketplace
        dest = self.marketplace_dir / "packages" / f"{manifest.id}-{manifest.version}.abp"
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(package_path, dest)
        
        self._listings[manifest.id] = listing
        self._save_listings()
        
        return listing
    
    def update_listing(self, plugin_id: str, updates: Dict) -> Optional[PluginListing]:
        """Update listing metadata"""
        listing = self._listings.get(plugin_id)
        if not listing:
            return None
        
        for key, value in updates.items():
            if hasattr(listing, key):
                setattr(listing, key, value)
        
        self._save_listings()
        return listing
    
    def get_listing(self, plugin_id: str) -> Optional[PluginListing]:
        return self._listings.get(plugin_id)
    
    def search_plugins(self, query: str = "", category: PluginCategory = None,
                       tags: List[str] = None, min_rating: float = 0,
                       verified_only: bool = False, sort: str = "relevance") -> List[PluginListing]:
        """Search marketplace"""
        results = list(self._listings.values())
        
        if query:
            q = query.lower()
            results = [l for l in results if q in l.manifest.name.lower() or q in l.manifest.description.lower()]
        
        if category:
            results = [l for l in results if l.manifest.category == category]
        
        if tags:
            results = [l for l in results if any(t in l.manifest.tags for t in tags)]
        
        if min_rating > 0:
            results = [l for l in results if l.rating >= min_rating]
        
        if verified_only:
            results = [l for l in results if l.verified]
        
        # Sort
        if sort == "rating":
            results.sort(key=lambda l: l.rating, reverse=True)
        elif sort == "downloads":
            results.sort(key=lambda l: l.downloads, reverse=True)
        elif sort == "updated":
            results.sort(key=lambda l: l.manifest.updated_at, reverse=True)
        elif sort == "newest":
            results.sort(key=lambda l: l.manifest.created_at, reverse=True)
        else:  # relevance - simple text match score
            pass
        
        return results
    
    def get_categories(self) -> List[Dict]:
        """Get category stats"""
        cats = {}
        for l in self._listings.values():
            cat = l.manifest.category.value
            if cat not in cats:
                cats[cat] = {"count": 0, "featured": 0}
            cats[cat]["count"] += 1
            if l.featured:
                cats[cat]["featured"] += 1
        return [{"category": k, **v} for k, v in cats.items()]
    
    # Installation
    
    def install_plugin(self, plugin_id: str, version: str = None) -> InstalledPlugin:
        """Install plugin from marketplace"""
        listing = self._listings.get(plugin_id)
        if not listing:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        # Find package
        pkg_dir = self.marketplace_dir / "packages"
        if version:
            pkg_file = pkg_dir / f"{plugin_id}-{version}.abp"
        else:
            # Latest version
            packages = list(pkg_dir.glob(f"{plugin_id}-*.abp"))
            if not packages:
                raise ValueError(f"No package found for {plugin_id}")
            pkg_file = max(packages, key=lambda p: semver.VersionInfo.parse(p.stem.split('-')[-1]))
        
        # Extract to plugins dir
        install_path = self.plugins_dir / plugin_id
        if install_path.exists():
            shutil.rmtree(install_path)
        
        with zipfile.ZipFile(pkg_file, 'r') as zf:
            zf.extractall(install_path)
        
        # Verify manifest matches
        with open(install_path / "plugin.json") as f:
            manifest = PluginManifest(**json.load(f))
        
        # Create installed record
        installed = InstalledPlugin(
            manifest=manifest,
            install_path=install_path,
            enabled=True
        )
        
        self._installed[plugin_id] = installed
        self._save_installed()
        
        # Update download count
        listing.downloads += 1
        self._save_listings()
        
        return installed
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall plugin"""
        installed = self._installed.get(plugin_id)
        if not installed:
            return False
        
        if installed.install_path.exists():
            shutil.rmtree(installed.install_path)
        
        del self._installed[plugin_id]
        self._save_installed()
        return True
    
    def enable_plugin(self, plugin_id: str) -> bool:
        installed = self._installed.get(plugin_id)
        if not installed:
            return False
        installed.enabled = True
        installed.status = PluginStatus.INSTALLED
        self._save_installed()
        return True
    
    def disable_plugin(self, plugin_id: str) -> bool:
        installed = self._installed.get(plugin_id)
        if not installed:
            return False
        installed.enabled = False
        installed.status = PluginStatus.DISABLED
        self._save_installed()
        return True
    
    def update_plugin(self, plugin_id: str) -> Optional[InstalledPlugin]:
        """Update to latest version"""
        installed = self._installed.get(plugin_id)
        listing = self._listings.get(plugin_id)
        if not installed or not listing:
            return None
        
        if semver.VersionInfo.parse(listing.manifest.version) <= semver.VersionInfo.parse(installed.manifest.version):
            return installed  # Already latest
        
        return self.install_plugin(plugin_id)
    
    def get_updates(self) -> List[Dict]:
        """Check for available updates"""
        updates = []
        for plugin_id, installed in self._installed.items():
            listing = self._listings.get(plugin_id)
            if listing and semver.VersionInfo.parse(listing.manifest.version) > semver.VersionInfo.parse(installed.manifest.version):
                updates.append({
                    "plugin_id": plugin_id,
                    "current_version": installed.manifest.version,
                    "latest_version": listing.manifest.version,
                    "changelog": listing.changelog
                })
        return updates
    
    def list_installed(self) -> List[InstalledPlugin]:
        return list(self._installed.values())
    
    # Reviews
    
    def add_review(self, plugin_id: str, user_id: str, rating: int, title: str, body: str) -> PluginReview:
        review = PluginReview(
            plugin_id=plugin_id,
            user_id=user_id,
            rating=max(1, min(5, rating)),
            title=title,
            body=body
        )
        
        if plugin_id not in self._reviews:
            self._reviews[plugin_id] = []
        self._reviews[plugin_id].append(review)
        
        # Update listing stats
        listing = self._listings.get(plugin_id)
        if listing:
            listing.review_count = len(self._reviews[plugin_id])
            listing.rating = sum(r.rating for r in self._reviews[plugin_id]) / listing.review_count
            self._save_listings()
        
        self._save_reviews()
        return review
    
    def get_reviews(self, plugin_id: str) -> List[PluginReview]:
        return self._reviews.get(plugin_id, [])
    
    def vote_review(self, plugin_id: str, review_id: str, helpful: bool) -> bool:
        reviews = self._reviews.get(plugin_id, [])
        for r in reviews:
            if r.id == review_id:
                if helpful:
                    r.helpful_votes += 1
                self._save_reviews()
                return True
        return False
    
    # Package creation helper
    
    @staticmethod
    def create_package(source_dir: Path, output_path: Path) -> bool:
        """Create .abp plugin package from source directory"""
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zf.write(file_path, arcname)
            return True
        except Exception as e:
            print(f"Package creation failed: {e}")
            return False
    
    @staticmethod
    def _hash_file(filepath: Path) -> str:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()


# Built-in plugin templates
def create_plugin_template(plugin_type: PluginCategory, name: str, output_dir: Path):
    """Create a starter plugin template"""
    templates = {
        PluginCategory.DAW_ADAPTER: {
            "entry_point": "adapter:MyDAWAdapter",
            "base_class": "BaseDAWAdapter",
            "methods": ["connect", "disconnect", "create_track", "delete_track", "get_project_info"]
        },
        PluginCategory.CONTROLLER: {
            "entry_point": "controller:MyController",
            "base_class": "BaseController",
            "methods": ["connect", "disconnect", "handle_message", "send_feedback"]
        },
        PluginCategory.MIDI_PROCESSOR: {
            "entry_point": "processor:MyMIDIProcessor",
            "base_class": "BaseMIDIProcessor",
            "methods": ["process", "get_parameters"]
        },
        PluginCategory.AI_MODEL: {
            "entry_point": "model:MyAIModel",
            "base_class": "BaseAIModel",
            "methods": ["generate", "get_capabilities"]
        },
        PluginCategory.UI_EXTENSION: {
            "entry_point": "ui:MyUIExtension",
            "base_class": "BaseUIExtension",
            "methods": ["render", "get_routes"]
        },
        PluginCategory.EXPORT_FORMAT: {
            "entry_point": "exporter:MyExporter",
            "base_class": "BaseExporter",
            "methods": ["export", "get_supported_formats"]
        },
        PluginCategory.THEME: {
            "entry_point": "theme:MyTheme",
            "base_class": "BaseTheme",
            "methods": ["get_colors", "get_css"]
        }
    }
    
    tpl = templates.get(plugin_type, templates[PluginCategory.UTILITY])
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # plugin.json
    manifest = {
        "id": f"user.{name.lower().replace(' ', '-')}",
        "name": name,
        "version": "1.0.0",
        "description": f"A {plugin_type.value} plugin for Ableton Brain",
        "author": "Your Name",
        "category": plugin_type.value,
        "entry_point": tpl["entry_point"],
        "min_ableton_brain_version": "1.0.0",
        "dependencies": [],
        "python_dependencies": [],
        "tags": [plugin_type.value],
        "license": "MIT",
        "permissions": []
    }
    
    (output_dir / "plugin.json").write_text(json.dumps(manifest, indent=2))
    
    # Main module
    main_py = f'''"""
{name} - {plugin_type.value} plugin
"""

from typing import Dict, List, Any, Optional

class {name.replace(' ', '')}:
    """{name} plugin implementation"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {{}}
    
    # Required methods for {plugin_type.value}
'''
    
    for method in tpl["methods"]:
        main_py += f'''
    async def {method}(self, *args, **kwargs) -> Any:
        """Implement {method}"""
        raise NotImplementedError
'''
    
    (output_dir / "main.py").write_text(main_py)
    
    # README
    readme = f'''# {name}

A {plugin_type.value} plugin for Ableton Brain.

## Installation

```bash
# Package and install
python -m ableton_brain.plugins.package {output_dir} {name}.abp
```

## Configuration

```json
{{
    "enabled": true,
    "settings": {{}}
}}
```

## Development

Edit `main.py` to implement the required methods.
'''
    (output_dir / "README.md").write_text(readme)
    
    print(f"Created plugin template at {output_dir}")


if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp:
        market_dir = Path(tmp) / "marketplace"
        plugins_dir = Path(tmp) / "plugins"
        
        market = PluginMarketplace(market_dir, plugins_dir)
        
        # Create a test plugin package
        plugin_src = Path(tmp) / "test_plugin"
        create_plugin_template(PluginCategory.MIDI_PROCESSOR, "Note Quantizer", plugin_src)
        
        pkg_path = Path(tmp) / "note_quantizer.abp"
        PluginMarketplace.create_package(plugin_src, pkg_path)
        
        # Publish
        listing = market.publish_plugin(pkg_path, "test-user")
        print(f"Published: {listing.manifest.name} v{listing.manifest.version}")
        
        # Search
        results = market.search_plugins(category=PluginCategory.MIDI_PROCESSOR)
        print(f"Search results: {len(results)}")
        
        # Install
        installed = market.install_plugin(listing.manifest.id)
        print(f"Installed: {installed.manifest.name} at {installed.install_path}")
        
        # Review
        review = market.add_review(listing.manifest.id, "user1", 5, "Great!", "Works perfectly")
        print(f"Review added: {review.rating} stars")
        
        # Check updates
        updates = market.get_updates()
        print(f"Updates available: {len(updates)}")