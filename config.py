import os
import json
import shutil
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "network_magic": 2,
    "blockfrost_api_key": "",
    "blockfrost_url": "https://cardano-preprod.blockfrost.io/api/v0",
    "cardano_cli_path": "",
    "cardano_address_path": "",
    "last_wallet_name": ""
}

def get_platform_executable_name(base_name):
    """Return the name of the executable based on the operating system."""
    if sys.platform.startswith("win"):
        return f"{base_name}.exe"
    return base_name

def find_executable(name):
    """
    Search for cardano binaries in various common locations:
    1. Current folder
    2. Parent folder
    3. Old project folder (../16.air-gap-wallet)
    4. System PATH
    """
    exec_name = get_platform_executable_name(name)
    
    # 1. Current folder
    if os.path.exists(exec_name) and os.access(exec_name, os.X_OK):
        return os.path.abspath(exec_name)
    
    # 2. Parent folder
    parent_path = os.path.join("..", exec_name)
    if os.path.exists(parent_path) and os.access(parent_path, os.X_OK):
        return os.path.abspath(parent_path)
    
    # 3. Old project folder (../16.air-gap-wallet)
    old_project_path = os.path.join("..", "16.air-gap-wallet", exec_name)
    if os.path.exists(old_project_path) and os.access(old_project_path, os.X_OK):
        return os.path.abspath(old_project_path)
        
    # 4. System PATH
    path_lookup = shutil.which(name)
    if path_lookup:
        return path_lookup
        
    return name  # fallback to name, letting system resolve or error

class AppConfig:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()
        self.auto_detect_binaries()

    def load(self):
        """Load configuration from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Update defaults with loaded values
                    for k, v in loaded.items():
                        if k in self.config:
                            self.config[k] = v
            except Exception as e:
                print(f"Error loading config file: {e}")

    def save(self):
        """Save configuration to JSON file."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config file: {e}")

    def auto_detect_binaries(self):
        """Detect cardano-cli and cardano-address if not already configured."""
        save_needed = False
        
        if not self.config.get("cardano_cli_path"):
            detected = find_executable("cardano-cli")
            self.config["cardano_cli_path"] = detected
            save_needed = True
            
        if not self.config.get("cardano_address_path"):
            detected = find_executable("cardano-address")
            self.config["cardano_address_path"] = detected
            save_needed = True
            
        if save_needed:
            self.save()

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    @property
    def network_param(self):
        """Return the appropriate cardano-cli network parameter."""
        magic = self.config.get("network_magic")
        if magic == 1 or magic == 764824074: # Mainnet magic numbers
            return ["--mainnet"]
        elif magic is None or magic == "":
            return ["--mainnet"]
        else:
            return ["--testnet-magic", str(magic)]
