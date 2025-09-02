"""Collection management for organizing image sources."""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from PySide6.QtCore import QStandardPaths

from .image_utils import get_images_in_folder


class Collection:
    """Represents a collection of image folders."""
    
    def __init__(self, name: str, paths: List[str], created_date: Optional[str] = None, 
                 last_used: Optional[str] = None, image_count: int = 0,
                 sort_method: str = "random", sort_descending: bool = False):
        self.name = name
        self.paths = paths
        self.created_date = created_date or datetime.now().isoformat()
        self.last_used = last_used
        self.image_count = image_count
        self.sort_method = sort_method  # "random", "name", "path", "size", "date"
        self.sort_descending = sort_descending
    
    def to_dict(self) -> Dict:
        """Convert collection to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'paths': self.paths,
            'created_date': self.created_date,
            'last_used': self.last_used,
            'image_count': self.image_count,
            'sort_method': self.sort_method,
            'sort_descending': self.sort_descending
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Collection':
        """Create collection from dictionary."""
        return cls(
            name=data['name'],
            paths=data['paths'],
            created_date=data.get('created_date'),
            last_used=data.get('last_used'),
            image_count=data.get('image_count', 0),
            sort_method=data.get('sort_method', 'random'),
            sort_descending=data.get('sort_descending', False)
        )
    
    def get_all_images(self) -> List[str]:
        """Get all images from all paths in this collection."""
        all_images = []
        for path in self.paths:
            if os.path.exists(path):
                all_images.extend(get_images_in_folder(path))
        return all_images
    
    def get_sorted_images(self) -> List[str]:
        """Get all images sorted according to the collection's sort method."""
        images = self.get_all_images()
        
        if self.sort_method == "random":
            import random
            random.shuffle(images)
        elif self.sort_method == "name":
            def natural_sort_key(path):
                """Generate a key for natural/human sorting of filenames.
                
                Converts 'image1.jpg', 'image10.jpg', 'image2.jpg' to sort as:
                'image1.jpg', 'image2.jpg', 'image10.jpg'
                """
                name = os.path.basename(path).lower()
                # Split the filename into text and number parts
                parts = re.split(r'(\d+)', name)
                # Convert numeric parts to integers for proper sorting
                result = []
                for part in parts:
                    if part.isdigit():
                        result.append(int(part))
                    else:
                        result.append(part)
                return result
            
            images.sort(key=natural_sort_key, reverse=self.sort_descending)
        elif self.sort_method == "path":
            def natural_sort_key_path(path):
                """Generate a key for natural/human sorting of full paths."""
                name = path.lower()
                # Split the path into text and number parts
                parts = re.split(r'(\d+)', name)
                # Convert numeric parts to integers for proper sorting
                result = []
                for part in parts:
                    if part.isdigit():
                        result.append(int(part))
                    else:
                        result.append(part)
                return result
            
            images.sort(key=natural_sort_key_path, reverse=self.sort_descending)
        elif self.sort_method == "size":
            # Sort by file size, handling missing files gracefully
            def get_size(path):
                try:
                    return os.path.getsize(path)
                except (OSError, FileNotFoundError):
                    return 0
            images.sort(key=get_size, reverse=self.sort_descending)
        elif self.sort_method == "date":
            # Sort by modification date, handling missing files gracefully
            def get_mtime(path):
                try:
                    return os.path.getmtime(path)
                except (OSError, FileNotFoundError):
                    return 0
            images.sort(key=get_mtime, reverse=self.sort_descending)
        
        return images
    
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
    
    def create_collection(self, name: str, paths: List[str], sort_method: str = "random", 
                         sort_descending: bool = False) -> Optional[Collection]:
        """Create a new collection with the given paths and sorting options."""
        if self.collection_exists(name):
            return None  # Collection already exists
        
        collection = Collection(name, paths, sort_method=sort_method, sort_descending=sort_descending)
        collection.update_image_count()  # Calculate initial image count
        
        if self.save_collection(collection):
            return collection
        return None