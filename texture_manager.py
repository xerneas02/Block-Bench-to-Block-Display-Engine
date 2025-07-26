"""Gestionnaire de textures multiples pour les modèles Blockbench"""

import base64
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional

class MultiTextureManager:
    """Handle multiple textures in Blockbench models"""
    
    def __init__(self):
        self.textures_cache = {}
    
    def extract_all_textures(self, bbmodel_data: Dict[str, Any]) -> Dict[int, Image.Image]:
        """Extract all textures from BBModel data"""
        
        textures = bbmodel_data.get("textures", [])
        extracted_textures = {}
        
        print(f"### Extraction of {len(textures)} textures ###")
        
        # Find the first texture to use as default (ID 0)
        default_texture = None
        
        for texture_data in textures:
            texture_id = texture_data.get("id")
            texture_name = texture_data.get("name", f"texture_{texture_id}")
            
            if texture_id is None:
                continue
            
            try:
                texture_id = int(texture_id)
                texture_image = self._extract_texture_image(texture_data)
                
                if texture_image:
                    extracted_textures[texture_id] = texture_image
                    print(f"  Texture {texture_id} ({texture_name}): {texture_image.size}")
                    
                    # Store first texture as default
                    if default_texture is None:
                        default_texture = texture_image
                else:
                    print(f"  Error extracting texture {texture_id} ({texture_name})")
                    
            except (ValueError, TypeError):
                print(f"ID of invalid texture: {texture_id}")
                continue
        
        # Add the default texture as ID 0 if needed
        if default_texture and 0 not in extracted_textures:
            extracted_textures[0] = default_texture
            print("  Added first texture as default (ID 0)")
        
        print(f"### {len(extracted_textures)} textures extracted successfully ###")
        return extracted_textures
    
    def _extract_texture_image(self, texture_data: Dict[str, Any]) -> Optional[Image.Image]:
        """Extract texture image from texture data"""
        
        try:
            source = texture_data.get("source", "")
            if not source or not source.startswith("data:image"):
                return None
            
            header, encoded = source.split(',', 1)
            image_data = base64.b64decode(encoded)
            
            texture_image = Image.open(io.BytesIO(image_data))
            
            if texture_image.mode != 'RGBA':
                texture_image = texture_image.convert('RGBA')
            
            return texture_image
            
        except Exception as e:
            print(f"Error extracting texture: {e}")
            return None
    
    def get_element_texture_ids(self, element: Dict[str, Any]) -> List[int]:
        """Get unique texture IDs used by an element's faces"""
        texture_ids = set()
        faces = element.get("faces", {})
        
        for face_name, face_data in faces.items():
            texture_id = face_data.get("texture")
            if texture_id is not None:
                try:
                    # Add this check for ID 0
                    texture_id = int(texture_id) 
                    if texture_id == 0 and 1 in self.textures_cache:
                        # Map texture 0 to first texture if present
                        texture_id = 1
                    texture_ids.add(texture_id)
                except (ValueError, TypeError):
                    pass
        
        return list(texture_ids)
    
    def create_element_texture_atlas(self, element: Dict[str, Any], 
                                   all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Create an atlas texture for an element based on its faces"""
        
        texture_ids = self.get_element_texture_ids(element)
        
        if not texture_ids:
            print("  No textures found for element")
            return None
        
        if len(texture_ids) == 1:
            texture_id = texture_ids[0]
            if texture_id in all_textures:
                print(f"  Texture unique: ID {texture_id}")
                return all_textures[texture_id]
        
        print(f"  Création atlas pour textures: {texture_ids}")
        return self._create_texture_atlas(texture_ids, all_textures, element)
    
    def _create_texture_atlas(self, texture_ids: List[int], 
                            all_textures: Dict[int, Image.Image], 
                            element: Dict[str, Any]) -> Optional[Image.Image]:
        """Create an atlas texture for multiple textures used by an element"""
        
        faces = element.get("faces", {})
        if not faces:
            return None
        
        uv_regions = {}
        
        for face_name, face_data in faces.items():
            texture_id = face_data.get("texture")
            if texture_id is None:
                continue
            
            try:
                texture_id = int(texture_id)
                # Map texture ID 0 to first available texture if needed
                if texture_id == 0 and 0 not in all_textures and len(all_textures) > 0:
                    texture_id = min(all_textures.keys())
            except (ValueError, TypeError):
                continue
            
            if texture_id not in all_textures:
                continue
            
            uv = face_data.get("uv", [0, 0, 16, 16])
            if len(uv) != 4:
                continue
                
            left, top, right, bottom = uv
            
            if left > right:
                left, right = right, left
            if top > bottom:
                top, bottom = bottom, top
            
            if texture_id not in uv_regions:
                uv_regions[texture_id] = []
            
            uv_regions[texture_id].append((left, top, right, bottom))
        
        if not uv_regions:
            print("    Aucune région UV valide trouvée")
            return None

        texture_bounds = {}
        
        for texture_id, regions in uv_regions.items():
            min_x = min(region[0] for region in regions)
            min_y = min(region[1] for region in regions)
            max_x = max(region[2] for region in regions)
            max_y = max(region[3] for region in regions)
            
            texture_bounds[texture_id] = (min_x, min_y, max_x, max_y)
            print(f"    Texture {texture_id}: UV bounds ({min_x}, {min_y}, {max_x}, {max_y})")

        if len(texture_bounds) == 1:
            texture_id = list(texture_bounds.keys())[0]
            texture = all_textures[texture_id]
            min_x, min_y, max_x, max_y = texture_bounds[texture_id]

            pixel_left = max(0, int(min_x))
            pixel_top = max(0, int(min_y))
            pixel_right = min(texture.width, int(max_x))
            pixel_bottom = min(texture.height, int(max_y))
            
            if pixel_right > pixel_left and pixel_bottom > pixel_top:
                cropped = texture.crop((pixel_left, pixel_top, pixel_right, pixel_bottom))
                print(f"    Texture {texture_id} recadrée: {cropped.size}")
                return cropped
            else:
                print(f"    Région invalide pour texture {texture_id}, utilisation complète")
                return texture

        return self._create_multi_texture_atlas(texture_bounds, all_textures)
    
    def _create_multi_texture_atlas(self, texture_bounds: Dict[int, Tuple[float, float, float, float]], 
                                   all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Create an atlas texture for multiple textures with bounds"""

        texture_regions = {}
        max_region_width = 0
        max_region_height = 0
        
        for texture_id, (min_x, min_y, max_x, max_y) in texture_bounds.items():
            if texture_id not in all_textures:
                continue
            
            texture = all_textures[texture_id]

            pixel_left = max(0, int(min_x))
            pixel_top = max(0, int(min_y))
            pixel_right = min(texture.width, int(max_x))
            pixel_bottom = min(texture.height, int(max_y))
            
            if pixel_right > pixel_left and pixel_bottom > pixel_top:
                region = texture.crop((pixel_left, pixel_top, pixel_right, pixel_bottom))
                texture_regions[texture_id] = region
                
                max_region_width = max(max_region_width, region.width)
                max_region_height = max(max_region_height, region.height)
                
                print(f"    Region texture {texture_id}: {region.size}")
        
        if not texture_regions:
            print("    No valid texture regions found")
            return None

        num_textures = len(texture_regions)
        
        if num_textures <= 2:
            atlas_width = max_region_width * num_textures
            atlas_height = max_region_height
            layout = "horizontal"
        elif num_textures <= 4:
            cols = 2
            rows = (num_textures + 1) // 2
            atlas_width = max_region_width * cols
            atlas_height = max_region_height * rows
            layout = "grid"
        else:
            side_length = int(num_textures ** 0.5) + 1
            atlas_width = max_region_width * side_length
            atlas_height = max_region_height * side_length
            layout = "square_grid"
        
        print(f"    Atlas {layout}: {atlas_width}x{atlas_height} for {num_textures} textures")
        
        atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        
        texture_items = list(texture_regions.items())
        
        for i, (texture_id, region) in enumerate(texture_items):
            if layout == "horizontal":
                x = i * max_region_width
                y = 0
            elif layout == "grid":
                x = (i % 2) * max_region_width
                y = (i // 2) * max_region_height
            else:
                side_length = int(len(texture_items) ** 0.5) + 1
                x = (i % side_length) * max_region_width
                y = (i // side_length) * max_region_height
            
            if region.size != (max_region_width, max_region_height):
                region = region.resize((max_region_width, max_region_height), Image.NEAREST)
            
            atlas.paste(region, (x, y))
            print(f"    Texture {texture_id} placed at ({x}, {y})")
        
        return atlas
    
    def convert_element_texture_to_head(self, element: Dict[str, Any], 
                                      all_textures: Dict[int, Image.Image]) -> Optional[str]:
        """Convert element texture to head texture in base64 format"""
        
        element_texture = self.create_element_texture_atlas(element, all_textures)
        
        if not element_texture:
            return None
        
        try:
            from tool.blockbench_texture_converter import BlockbenchTextureConverter
            converter = BlockbenchTextureConverter()
            head_texture = converter.create_head_texture_for_element(element_texture, element)

            buffered = io.BytesIO()
            head_texture.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"Error converting texture element: {e}")
            return None

    def validate_texture(self, texture: Image.Image) -> bool:
        """Validate texture dimensions and format"""
        # Check power of 2 dimensions
        if not (texture.width & (texture.width - 1) == 0) or \
           not (texture.height & (texture.height - 1) == 0):
            print(f"Warning: Texture dimensions ({texture.width}x{texture.height}) are not power of 2")
            return False
            
        # Check maximum size
        if texture.width > 1024 or texture.height > 1024:
            print("Warning: Texture exceeds maximum size of 1024x1024")
            return False
            
        return True