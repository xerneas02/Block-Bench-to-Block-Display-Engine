"""Global configuration for BBModel to BDEngine converter"""

import base64
import io
import os
from PIL import Image

class Config:
    """Global converter configuration"""
    
    # Available conversion modes
    CONVERSION_MODES = {
        "stretch": "Stretch heads to match exact shapes",
        "cube": "Decompose into optimized cubes"
    }
    
    DEFAULT_MODE = "cube"
    
    # BDEngine parameters
    MIN_SCALE = 0.0011  # Minimum scale required by BDEngine
    
    # Conversion parameters
    PIXELS_PER_BLOCK = 16  # 16 pixels = 1 Minecraft block
    HEAD_SIZE = 8  # Base size of player head in pixels
    
    # Possible cube sizes for optimization
    CUBE_SIZES = [16, 8, 4, 2, 1]
    INTERMEDIATE_SIZES = [12, 6, 3]
    
    # Texture configuration
    DEFAULT_TEXTURE_PATH = "textures/default.png"
    
    @staticmethod
    def load_default_texture():
        """Load default texture from file and convert to base64"""
        try:
            if os.path.exists(Config.DEFAULT_TEXTURE_PATH):
                image = Image.open(Config.DEFAULT_TEXTURE_PATH)
                
                # Convert to RGBA if not already
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                # Convert to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                print(f"Loaded default texture: {Config.DEFAULT_TEXTURE_PATH} ({image.size})")
                return f"data:image/png;base64,{img_str}"
            else:
                print(f"Warning: Default texture not found at {Config.DEFAULT_TEXTURE_PATH}")
                print("Using fallback rubik's cube texture")
                return Config._get_fallback_texture()
                
        except Exception as e:
            print(f"Error loading default texture: {e}")
            print("Using fallback rubik's cube texture")
            return Config._get_fallback_texture()
    
    @staticmethod
    def _get_fallback_texture():
        """Fallback rubik's cube texture if default.png is not found"""
        print("Using fallback rubik's cube texture")
        return "data:image/png;base64,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"
    
    # Base BDEngine structure
    BDENGINE_BASE_STRUCTURE = {
        "isCollection": True,
        "name": "Converted Model",
        "nbt": "",
        "settings": {
            "defaultBrightness": False
        },
        "mainNBT": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": [],
        "listAnim": [
            {
                "id": 1,
                "name": "Default"
            }
        ]
    }
    
    @staticmethod
    def get_head_base_structure():
        """Get base structure for heads with loaded texture"""
        return {
            "isItemDisplay": True,
            "name": "player_head[display=none]",
            "brightness": {
                "sky": 15,
                "block": 0
            },
            "nbt": "",
            "tagHead": {
                "Value": ""
            },
            "textureValueList": [],
            "paintTexture": Config.load_default_texture(),
            "transforms": []
        }