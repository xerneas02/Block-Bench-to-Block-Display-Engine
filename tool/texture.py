import base64
import json
from PIL import Image
import io
import os
from datetime import datetime

class TextureDecoder:
    """Decoder for BDEngine textures"""
    
    def __init__(self):
        self.output_dir = "decoded_textures"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def decode_base64_image(self, base64_data):
        """Decode base64 image data to PIL Image"""
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image/'):
                # Extract just the base64 part
                base64_data = base64_data.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_data)
            
            # Create PIL Image
            image = Image.open(io.BytesIO(image_data))
            return image
            
        except Exception as e:
            print(f"Error decoding image: {e}")
            return None
    
    def extract_textures_from_bdengine(self, bdengine_file):
        """Extract all textures from a decoded BDEngine file"""
        try:
            with open(bdengine_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            textures = []
            self._find_textures_recursive(data, textures)
            
            return textures
            
        except Exception as e:
            print(f"Error reading BDEngine file: {e}")
            return []
    
    def _find_textures_recursive(self, obj, textures, path=""):
        """Recursively find texture data in nested structures"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if key == "paintTexture" and isinstance(value, str) and value.startswith("data:image/"):
                    textures.append({
                        "path": current_path,
                        "data": value,
                        "type": "paintTexture"
                    })
                elif key == "tagHead" and isinstance(value, dict) and "Value" in value:
                    # Handle player head textures
                    head_value = value["Value"]
                    if head_value and isinstance(head_value, str):
                        textures.append({
                            "path": current_path,
                            "data": head_value,
                            "type": "headTexture"
                        })
                else:
                    self._find_textures_recursive(value, textures, current_path)
                    
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._find_textures_recursive(item, textures, current_path)
    
    def save_texture(self, texture_data, filename_prefix="texture"):
        """Save texture data as image file"""
        image = self.decode_base64_image(texture_data)
        if image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            image.save(filepath)
            print(f"Texture saved: {filepath}")
            print(f"Image size: {image.size}")
            print(f"Image mode: {image.mode}")
            
            return filepath
        return None
    
    def analyze_texture(self, texture_data):
        """Analyze texture properties"""
        image = self.decode_base64_image(texture_data)
        if image:
            info = {
                "size": image.size,
                "mode": image.mode,
                "format": image.format,
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            }
            
            # Get color palette for small images
            if image.size[0] <= 64 and image.size[1] <= 64:
                colors = image.getcolors(maxcolors=256)
                if colors:
                    info["color_count"] = len(colors)
                    info["dominant_colors"] = sorted(colors, reverse=True)[:5]
            
            return info
        return None

def decode_bdengine_textures(bdengine_json_file):
    """Main function to decode textures from BDEngine file"""
    decoder = TextureDecoder()
    
    # Extract textures
    textures = decoder.extract_textures_from_bdengine(bdengine_json_file)
    
    if not textures:
        print("No textures found in the file")
        return
    
    print(f"Found {len(textures)} texture(s)")
    
    for i, texture in enumerate(textures):
        print(f"\n--- Texture {i+1} ---")
        print(f"Path: {texture['path']}")
        print(f"Type: {texture['type']}")
        
        # Analyze texture
        info = decoder.analyze_texture(texture['data'])
        if info:
            print(f"Properties: {info}")
        
        # Save texture
        filename_prefix = f"texture_{i+1}_{texture['type']}"
        saved_path = decoder.save_texture(texture['data'], filename_prefix)
        
        if saved_path:
            print(f"Saved to: {saved_path}")

if __name__ == "__main__":
    # Decode textures from the Test file
    bdengine_file = "decoded_bdengine/Test_20250725_101841.json"
    decode_bdengine_textures(bdengine_file)