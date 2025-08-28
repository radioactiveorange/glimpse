"""Collection management for organizing image sources."""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from PySide6.QtCore import QStandardPaths

from .image_utils import get_images_in_folder


class Collection:
    """Represents a collection of image folders."""
    
    def __init__(self, name: str, paths: List[str], created_date: Optional[str] = None, 
                 last_used: Optional[str] = None, image_count: int = 0):
        self.name = name
        self.paths = paths
        self.created_date = created_date or datetime.now().isoformat()
        self.last_used = last_used
        self.image_count = image_count
    
    def to_dict(self) -> Dict:
        """Convert collection to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'paths': self.paths,
            'created_date': self.created_date,
            'last_used': self.last_used,
            'image_count': self.image_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Collection':
        """Create collection from dictionary."""
        return cls(
            name=data['name'],
            paths=data['paths'],
            created_date=data.get('created_date'),
            last_used=data.get('last_used'),
            image_count=data.get('image_count', 0)
        )
    
    def get_all_images(self) -> List[str]:
        """Get all images from all paths in this collection."""
        all_images = []
        for path in self.paths:
            if os.path.exists(path):
                all_images.extend(get_images_in_folder(path))
        return all_images
    
    def update_image_count(self):
        """Update the cached image count."""
        self.image_count = len(self.get_all_images())
    
    def mark_as_used(self):
        """Mark collection as recently used."""
        self.last_used = datetime.now().isoformat()


class CollectionManager:
    """Manages loading, saving, and organizing collections."""
    
    def __init__(self):
        self.collections_dir = self._get_collections_dir()
        self._ensure_collections_dir()
    
    def _get_collections_dir(self) -> str:
        """Get the collections directory path."""
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not app_data_dir:
            app_data_dir = os.path.expanduser("~/.glimpse")
        return os.path.join(app_data_dir, "collections")
    
    def _ensure_collections_dir(self):
        """Ensure collections directory exists."""
        os.makedirs(self.collections_dir, exist_ok=True)
    
    def _get_collection_file_path(self, collection_name: str) -> str:
        """Get the file path for a collection."""
        # Sanitize collection name for filename
        safe_name = "".join(c for c in collection_name if c.isalnum() or c in (' ', '-', '_')).strip()
        return os.path.join(self.collections_dir, f"{safe_name}.json")
    
    def save_collection(self, collection: Collection) -> bool:
        """Save a collection to disk."""
        try:
            file_path = self._get_collection_file_path(collection.name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(collection.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving collection '{collection.name}': {e}")
            return False
    
    def load_collection(self, collection_name: str) -> Optional[Collection]:
        """Load a collection from disk."""
        try:
            file_path = self._get_collection_file_path(collection_name)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Collection.from_dict(data)
        except Exception as e:
            print(f"Error loading collection '{collection_name}': {e}")
            return None
    
    def get_all_collections(self) -> List[Collection]:
        """Get all available collections."""
        collections = []
        try:
            for filename in os.listdir(self.collections_dir):
                if filename.endswith('.json'):
                    collection_name = filename[:-5]  # Remove .json extension
                    collection = self.load_collection(collection_name)
                    if collection:
                        collections.append(collection)
        except Exception as e:
            print(f"Error loading collections: {e}")
        
        # Sort by last used (most recent first), then by name
        collections.sort(key=lambda c: (c.last_used or '', c.name))
        collections.reverse()  # Most recent first
        return collections
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from disk."""
        try:
            file_path = self._get_collection_file_path(collection_name)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting collection '{collection_name}': {e}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection already exists."""
        file_path = self._get_collection_file_path(collection_name)
        return os.path.exists(file_path)
    
    def create_collection(self, name: str, paths: List[str]) -> Optional[Collection]:
        """Create a new collection with the given paths."""
        if self.collection_exists(name):
            return None  # Collection already exists
        
        collection = Collection(name, paths)
        collection.update_image_count()  # Calculate initial image count
        
        if self.save_collection(collection):
            return collection
        return None