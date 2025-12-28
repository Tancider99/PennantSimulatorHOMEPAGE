# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Network Manager
Handles communication with Firebase Firestore for preset sharing.
"""
import requests
import gzip
import base64
import json
import os
import datetime


import json
import os
import datetime
import uuid

class NetworkManager:
    """Manages network operations for Firebase Firestore"""
    
    CONFIG_FILE = "firebase_config.json"
    USER_CONFIG_FILE = "user_config.json"
    
    # Defaults (User should replace these with their own if they want to host their own)
    DEFAULT_PROJECT_ID = "pennant-simulator-presets" # Placeholder
    DEFAULT_API_KEY = "" # Placeholder
    
    MAX_DAILY_PUBLISH = 10
    MAX_DAILY_LOAD = 25
    
    def __init__(self):
        self.project_id = self.DEFAULT_PROJECT_ID
        self.api_key = self.DEFAULT_API_KEY
        self.user_id = None
        self.daily_stats = {"date": "", "publish_count": 0, "load_count": 0}
        
        self.load_config()
        self._load_user_config()
        
    def load_config(self):
        """Load Firebase configuration from file"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.project_id = config.get("project_id", self.DEFAULT_PROJECT_ID)
                    self.api_key = config.get("api_key", self.DEFAULT_API_KEY)
            except Exception as e:
                print(f"[ERROR] Failed to load firebase config: {e}")
    
    def save_config(self, project_id, api_key):
        """Save Firebase configuration to file"""
        self.project_id = project_id
        self.api_key = api_key
        
        config = {
            "project_id": project_id,
            "api_key": api_key
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save firebase config: {e}")
            return False

    def _load_user_config(self):
        """Load or create user configuration (ID and stats)"""
        if os.path.exists(self.USER_CONFIG_FILE):
            try:
                with open(self.USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_id = data.get("user_id")
                    self.daily_stats = data.get("daily_stats", self.daily_stats)
            except Exception:
                pass
        
        if not self.user_id:
            self.user_id = str(uuid.uuid4())
            self._save_user_config()
            
        # Reset stats if new day
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.daily_stats.get("date") != today:
            self.daily_stats = {"date": today, "publish_count": 0, "load_count": 0}
            self._save_user_config()

    def _save_user_config(self):
        """Save user configuration"""
        data = {
            "user_id": self.user_id,
            "daily_stats": self.daily_stats
        }
        try:
            with open(self.USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save user config: {e}")

    def is_configured(self):
        """Check if Firebase is configured (Project ID is set)"""
        return bool(self.project_id) and self.project_id != "pennant-simulator-presets"

    def _get_base_url(self):
        return f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"

    def get_remaining_limits(self):
        """Get remaining daily limits"""
        return {
            "publish": max(0, self.MAX_DAILY_PUBLISH - self.daily_stats["publish_count"]),
            "load": max(0, self.MAX_DAILY_LOAD - self.daily_stats["load_count"])
        }

    def get_global_presets(self, page_size=50):
        """
        Get latest global presets
        
        Returns:
            list: List of preset metadata
        """
        if not self.is_configured():
            raise Exception("Firebase Project ID is not configured.")

        url = f"{self._get_base_url()}/presets"
        
        params = {
            "pageSize": page_size,
            "orderBy": "created_at desc"
        }
        if self.api_key:
            params["key"] = self.api_key
            
        try:
            response = requests.get(url, params=params)
        except Exception as e:
            raise Exception(f"Network error: {e}")
            
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            presets = []
            
            for doc in documents:
                fields = doc.get("fields", {})
                # Skip own preset in global list? (Optional, keeping for now)
                
                meta = {
                    "id": doc.get("name", "").split("/")[-1],
                    "name": fields.get("name", {}).get("stringValue", "Unknown"),
                    "description": fields.get("description", {}).get("stringValue", ""),
                    "author": fields.get("author", {}).get("stringValue", "Anonymous"),
                    "author_id": fields.get("author_id", {}).get("stringValue", ""),
                    "created_at": fields.get("created_at", {}).get("timestampValue", ""),
                    "version": fields.get("version", {}).get("stringValue", "1.0"),
                }
                presets.append(meta)
            return presets
        else:
            raise Exception(f"Failed to fetch presets: {response.text}")

    def get_user_preset(self):
        """
        Find the single preset published by the current user
        
        Returns:
            dict: Preset metadata if found, None otherwise
        """
        if not self.is_configured():
            return None
            
        # Unfortunately Firestore simple REST API doesn't support complex filtering 
        # without createIndex processing which might be annoying for users.
        # But we can try structuredQuery if needed.
        # For simplicity in this "Free/Test" mode, we will fetch recent and filter client side
        # OR we assume we store the preset_id in user_config locally?
        # Storing locally is fragile (if user reinstalls).
        # Let's try to search using structuredQuery which is standard.
        
        url = f"{self._get_base_url()}:runQuery"
        
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "presets"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "author_id"},
                        "op": "EQUAL",
                        "value": {"stringValue": self.user_id}
                    }
                },
                "limit": 1
            }
        }
        
        params = {}
        if self.api_key:
            params["key"] = self.api_key
            
        try:
            response = requests.post(url, json=query, params=params)
        except Exception:
            return None
            
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0 and "document" in results[0]:
                doc = results[0]["document"]
                fields = doc.get("fields", {})
                return {
                    "id": doc.get("name", "").split("/")[-1],
                    "name": fields.get("name", {}).get("stringValue", "Unknown"),
                    "created_at": fields.get("created_at", {}).get("timestampValue", "")
                }
        return None

    def publish_preset(self, data, name, description, author="Anonymous"):
        """
        Publish a preset to Firestore (Overwrites existing user preset if any)
        Checks limits.
        """
        if not self.is_configured():
            raise Exception("Firebase Project ID is not configured.")
            
        # Check Daily Limit
        if self.daily_stats["publish_count"] >= self.MAX_DAILY_PUBLISH:
            raise Exception(f"1日の公開上限（{self.MAX_DAILY_PUBLISH}回）に達しました。")
            
        # Check if user already has a preset
        existing_preset = self.get_user_preset()
        
        # Prepare content with compression
        data_json = json.dumps(data, ensure_ascii=False)
        data_bytes = data_json.encode('utf-8')
        compressed_data = gzip.compress(data_bytes)
        b64_data = base64.b64encode(compressed_data).decode('utf-8')
        
        fields = {
            "name": {"stringValue": name},
            "description": {"stringValue": description},
            "author": {"stringValue": author},
            "author_id": {"stringValue": self.user_id},
            "version": {"stringValue": "1.0"},
            "created_at": {"timestampValue": datetime.datetime.utcnow().isoformat() + "Z"},
            "data_b64_gzip": {"stringValue": b64_data}
        }
        
        params = {}
        if self.api_key:
            params["key"] = self.api_key
            
        if existing_preset:
            # Update existing
            doc_id = existing_preset["id"]
            url = f"{self._get_base_url()}/presets/{doc_id}"
            
            # Use PATCH for update (though in Firestore REST, patch updates specified fields)
            # We want to replace mostly everything but ID stays.
            response = requests.patch(url, json={"fields": fields}, params=params)
        else:
            # Create new
            url = f"{self._get_base_url()}/presets"
            payload = {"fields": fields}
            response = requests.post(url, json=payload, params=params)
        
        if response.status_code == 200:
            # Increment stat
            self.daily_stats["publish_count"] += 1
            self._save_user_config()
            
            doc_name = response.json().get("name", "")
            return doc_name.split("/")[-1]
        else:
            raise Exception(f"Failed to publish preset: {response.text}")

    def load_preset(self, preset_id):
        """
        Load a preset from Firestore with limit check
        """
        if not self.is_configured():
            raise Exception("Firebase Project ID is not configured.")

        # Check Daily Limit
        if self.daily_stats["load_count"] >= self.MAX_DAILY_LOAD:
            raise Exception(f"1日のダウンロード上限（{self.MAX_DAILY_LOAD}回）に達しました。")

        url = f"{self._get_base_url()}/presets/{preset_id}"
        
        params = {}
        if self.api_key:
            params["key"] = self.api_key
            
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            doc = response.json()
            fields = doc.get("fields", {})
            
            result = {
                "id": preset_id,
                "name": fields.get("name", {}).get("stringValue", "Unknown"),
                "description": fields.get("description", {}).get("stringValue", ""),
                "author": fields.get("author", {}).get("stringValue", "Anonymous"),
                "author_id": fields.get("author_id", {}).get("stringValue", ""),
                "version": fields.get("version", {}).get("stringValue", "1.0"),
                "created_at": fields.get("created_at", {}).get("timestampValue", ""),
            }
            
            # Decompress
            if "data_b64_gzip" in fields:
                b64_data = fields["data_b64_gzip"].get("stringValue", "")
                try:
                    compressed_data = base64.b64decode(b64_data)
                    data_bytes = gzip.decompress(compressed_data)
                    data_json = data_bytes.decode('utf-8')
                    result["data"] = json.loads(data_json)
                except Exception as e:
                    print(f"[ERROR] Failed to decompress: {e}")
                    result["data"] = {}
            elif "data_json" in fields:
                data_json = fields.get("data_json", {}).get("stringValue", "{}")
                try:
                    result["data"] = json.loads(data_json)
                except json.JSONDecodeError:
                    result["data"] = {}
            else:
                result["data"] = {}
            
            # Increment stat only on success
            self.daily_stats["load_count"] += 1
            self._save_user_config()
                
            return result
        elif response.status_code == 404:
            raise Exception("Preset not found.")
        else:
            raise Exception(f"Failed to load preset: {response.text}")
            
    def delete_preset(self, preset_id):
        """Delete a published preset"""
        if not self.is_configured():
            raise Exception("Config Error")
            
        url = f"{self._get_base_url()}/presets/{preset_id}"
        params = {}
        if self.api_key:
            params["key"] = self.api_key
            
        requests.delete(url, params=params)
        return True

# Global instance
network_manager = NetworkManager()
