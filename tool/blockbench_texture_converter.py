"""Converter for Blockbench textures to BDEngine head format"""

import base64
import json
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional

class BlockbenchTextureConverter:
    """Converts Blockbench model textures to BDEngine head format"""
    
    def __init__(self):
        # Head UV mapping: each face is 8x8 pixels in the 32x32 head area
        # CORRECTION: East/West mapping cohérent avec texture_subdivider
        self.head_face_mapping = {
            "up": {"color": "white", "region": (8, 0, 16, 8)},       # Top face (8x8)
            "down": {"color": "yellow", "region": (16, 0, 24, 8)},   # Bottom face (8x8)
            "north": {"color": "red", "region": (8, 8, 16, 16)},     # Front face (8x8)
            "south": {"color": "orange", "region": (24, 8, 32, 16)}, # Back face (8x8)
            "east": {"color": "green", "region": (0, 8, 8, 16)},     # Right side (face droite)
            "west": {"color": "blue", "region": (16, 8, 24, 16)}     # Left side (face gauche)
        }
    
    def extract_blockbench_texture(self, bbmodel_data: Dict[str, Any]) -> Optional[Image.Image]:
        """Extract texture from bbmodel data"""
        try:
            textures = bbmodel_data.get("textures", [])
            if not textures:
                print("No textures found in bbmodel")
                return None
            
            # Get first texture
            texture = textures[0]
            source = texture.get("source", "")
            
            if not source.startswith("data:image/"):
                print("No embedded texture found")
                return None
            
            # Decode base64 image
            base64_data = source.split(',')[1]
            image_data = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_data))
            
            print(f"Extracted texture: {image.size} pixels")
            return image
            
        except Exception as e:
            print(f"Error extracting texture: {e}")
            return None
    
    def normalize_uv_coordinates(self, uv: List[float]) -> Tuple[int, int, int, int]:
        """Normalize UV coordinates to ensure left < right and top < bottom"""
        u1, v1, u2, v2 = uv
        
        # Ensure left < right
        left = min(u1, u2)
        right = max(u1, u2)
        
        # Ensure top < bottom  
        top = min(v1, v2)
        bottom = max(v1, v2)
        
        return (int(left), int(top), int(right), int(bottom))
    
    def analyze_element_uv_mapping(self, element: Dict[str, Any]) -> Dict[str, Tuple[int, int, int, int]]:
        """Analyze UV mapping for a single element"""
        faces = element.get("faces", {})
        uv_mapping = {}
        
        print(f"Analyzing element: {element.get('name', 'unknown')}")
        
        for face_name, face_data in faces.items():
            uv = face_data.get("uv", [0, 0, 0, 0])
            texture_id = face_data.get("texture", 0)
            
            # Normalize UV coordinates to fix coordinate order issues
            uv_region = self.normalize_uv_coordinates(uv)
            uv_mapping[face_name] = uv_region
            
            print(f"  {face_name}: UV {uv} -> normalized region {uv_region}")
        
        return uv_mapping
    
    def create_head_texture_for_element(self, source_texture: Image.Image, 
                                      element: Dict[str, Any]) -> Image.Image:
        """Create 64x64 head texture for a single element"""
        
        # Create 64x64 head texture (standard Minecraft head size)
        # The actual head is in the top-left 32x32 area
        head_texture = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        
        # Get UV mapping for this element
        uv_mapping = self.analyze_element_uv_mapping(element)
        
        print("Creating 64x64 head texture with 32x32 head area...")
        
        # Map each face from source texture to head texture (in 32x32 area)
        for face_name, uv_region in uv_mapping.items():
            if face_name in self.head_face_mapping:
                try:
                    # Extract face from source texture
                    face_image = source_texture.crop(uv_region)
                    
                    # Resize to 8x8 (standard head face size)
                    if face_image.size != (8, 8):
                        face_image = face_image.resize((8, 8), Image.NEAREST)
                    
                    # Get target region in head texture (32x32 area)
                    target_region = self.head_face_mapping[face_name]["region"]
                    
                    # Paste face to head texture
                    head_texture.paste(face_image, target_region)
                    
                    print(f"  ✅ Mapped {face_name}: {uv_region} -> {target_region} (8x8)")
                    
                except Exception as e:
                    print(f"  ❌ Error mapping {face_name}: {e}")
                    
                    # Create a solid color fallback for this face
                    color = self._get_fallback_color(face_name)
                    fallback_face = Image.new('RGBA', (8, 8), color)
                    target_region = self.head_face_mapping[face_name]["region"]
                    head_texture.paste(fallback_face, target_region)
                    print(f"  🔧 Used fallback color for {face_name}")
        
        return head_texture
    
    def _get_fallback_color(self, face_name: str) -> Tuple[int, int, int, int]:
        """Get fallback color for face based on standard mapping"""
        color_map = {
            "up": (255, 255, 255, 255),    # White
            "down": (255, 255, 0, 255),    # Yellow
            "north": (255, 0, 0, 255),     # Red
            "south": (255, 165, 0, 255),   # Orange
            "east": (0, 255, 0, 255),      # Green (was west)
            "west": (0, 0, 255, 255)       # Blue (was east)
        }
        return color_map.get(face_name, (128, 128, 128, 255))  # Gray default
    
    def convert_bbmodel_to_head_texture(self, bbmodel_file: str) -> Optional[str]:
        """Convert bbmodel to head texture and return base64 data"""
        
        try:
            # Load bbmodel
            with open(bbmodel_file, 'r', encoding='utf-8') as f:
                bbmodel_data = json.load(f)
            
            # Extract source texture
            source_texture = self.extract_blockbench_texture(bbmodel_data)
            if not source_texture:
                return None
            
            # Get elements
            elements = bbmodel_data.get("elements", [])
            if not elements:
                print("No elements found in bbmodel")
                return None
            
            # For now, handle single element case
            if len(elements) != 1:
                print(f"Warning: Found {len(elements)} elements, processing first one only")
            
            element = elements[0]
            
            # Create head texture
            head_texture = self.create_head_texture_for_element(source_texture, element)
            
            # Convert to base64
            buffered = io.BytesIO()
            head_texture.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Save for debugging (clean version without grid)
            debug_filename = f"debug_head_texture_{element.get('name', 'cube')}.png"
            head_texture.save(debug_filename)
            print(f"Debug: Clean 64x64 head texture saved as {debug_filename}")
            
            # Also save the source texture for comparison
            source_filename = f"debug_source_texture_{element.get('name', 'cube')}.png"
            source_texture.save(source_filename)
            print(f"Debug: Source texture saved as {source_filename}")
            
            # Save just the 32x32 head area for comparison
            head_area = head_texture.crop((0, 0, 32, 32))
            head_area_filename = f"debug_head_area_{element.get('name', 'cube')}.png"
            head_area.save(head_area_filename)
            print(f"Debug: 32x32 head area saved as {head_area_filename}")
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"Error converting bbmodel texture: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_conversion(self, bbmodel_file: str):
        """Test the conversion process"""
        print(f"=== Testing texture conversion for {bbmodel_file} ===")
        
        # Convert texture
        head_texture_data = self.convert_bbmodel_to_head_texture(bbmodel_file)
        
        if head_texture_data:
            print("✅ Conversion successful!")
            print(f"Generated base64 length: {len(head_texture_data)}")
            
            # Decode and save result for verification
            base64_data = head_texture_data.split(',')[1]
            image_data = base64.b64decode(base64_data)
            result_image = Image.open(io.BytesIO(image_data))
            
            print(f"Final texture size: {result_image.size}")
            
            result_image.save("converted_head_texture_64x64.png")
            print("Result saved as: converted_head_texture_64x64.png")
            
        else:
            print("❌ Conversion failed")

def main():
    """Test the converter with your color.bbmodel file"""
    converter = BlockbenchTextureConverter()
    converter.test_conversion("color.bbmodel")

if __name__ == "__main__":
    main()