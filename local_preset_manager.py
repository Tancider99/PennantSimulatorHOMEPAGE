# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Local Preset Manager
Manages presets saved on the local disk.
"""
import os
import json
import datetime
import shutil

class LocalPresetManager:
    """Manages local preset files"""
    
    PRESET_DIR = "local_presets"
    MAX_PRESETS = 50
    
    def __init__(self):
        self._ensure_dir()
        
    def _ensure_dir(self):
        if not os.path.exists(self.PRESET_DIR):
            os.makedirs(self.PRESET_DIR)
            
    def get_all_presets(self):
        """
        Get all local presets sorted by updated_at desc
        
        Returns:
            list: List of dicts containing metadata
        """
        presets = []
        if not os.path.exists(self.PRESET_DIR):
            return presets
            
        for filename in os.listdir(self.PRESET_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(self.PRESET_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Ensure minimal metadata
                        meta = {
                            "filename": filename,
                            "name": data.get("name", "Unknown"),
                            "description": data.get("description", ""),
                            "author": data.get("author", "Anonymous"),
                            "created_at": data.get("created_at", ""),
                            "updated_at": data.get("updated_at", "")
                        }
                        presets.append(meta)
                except Exception as e:
                    print(f"[ERROR] Failed to load preset metadata {filename}: {e}")
                    
        # Sort by updated_at descending
        presets.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return presets
    
    def save_preset(self, data, name, description, author="Anonymous"):
        """
        Save a preset locally
        
        Args:
            data (dict): Game data
            name (str): Preset name
            description (str): Description
            author (str): Author
            
        Returns:
            bool: True if successful
            str: Error message if failed
        """
        self._ensure_dir()
        
        # Check limit
        current_presets = self.get_all_presets()
        if len(current_presets) >= self.MAX_PRESETS:
            return False, f"プリセットの保存上限（{self.MAX_PRESETS}個）に達しています。\n不要なプリセットを削除してください。"
            
        # Create metadata wrapper
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        file_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"preset_{file_id}.json"
        
        preset_content = {
            "name": name,
            "description": description,
            "author": author,
            "version": "1.0",
            "created_at": timestamp,
            "updated_at": timestamp,
            "data": data
        }
        
        filepath = os.path.join(self.PRESET_DIR, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(preset_content, f, ensure_ascii=False, indent=2)
            return True, "Start OK"
        except Exception as e:
            return False, str(e)

    def load_preset_data(self, filename):
        """Load full preset data from file"""
        filepath = os.path.join(self.PRESET_DIR, filename)
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
            return content
        except Exception:
            return None
            
    def delete_preset(self, filename):
        """Delete a local preset"""
        filepath = os.path.join(self.PRESET_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception:
                return False
        return False
        
    def update_preset_metadata(self, filename, new_name, new_description):
        """Update the name and description of a preset"""
        filepath = os.path.join(self.PRESET_DIR, filename)
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            content['name'] = new_name
            content['description'] = new_description
            content['updated_at'] = datetime.datetime.utcnow().isoformat() + "Z"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update preset: {e}")
            return False

# Global instance
local_preset_manager = LocalPresetManager()
