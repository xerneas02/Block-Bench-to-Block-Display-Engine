"""MultiTextureManager: A class to handle multiple textures in Blockbench models."""

import base64
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional

class TextureRect:
    """Rectangle for bin packing algorithm"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def fits(self, width: int, height: int) -> bool:
        """Check if a texture of given size fits in this rectangle"""
        return width <= self.width and height <= self.height
        
    def split(self, width: int, height: int) -> List['TextureRect']:
        """Split this rectangle after placing a texture, return remaining rectangles"""
        remaining = []
        
        if self.width > width:
            remaining.append(TextureRect(
                self.x + width, self.y, 
                self.width - width, height
            ))
            
        if self.height > height:
            remaining.append(TextureRect(
                self.x, self.y + height,
                self.width, self.height - height
            ))
            
        if self.width > width and self.height > height:
            remaining.append(TextureRect(
                self.x + width, self.y + height,
                self.width - width, self.height - height
            ))
            
        return remaining

class BinPacker:
    """Simple bin packing algorithm for texture atlasing"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.free_rects = [TextureRect(0, 0, width, height)]
        self.placements = {}
        
    def pack(self, texture_id: int, width: int, height: int) -> Optional[Tuple[int, int]]:
        """Try to pack a texture, return position if successful"""
        best_rect = None
        best_index = -1
        
        for i, rect in enumerate(self.free_rects):
            if rect.fits(width, height):
                if best_rect is None or (rect.width * rect.height) < (best_rect.width * best_rect.height):
                    best_rect = rect
                    best_index = i
                    
        if best_rect is None:
            return None
            
        pos_x, pos_y = best_rect.x, best_rect.y
        self.placements[texture_id] = (pos_x, pos_y, width, height)
        
        del self.free_rects[best_index]
        split_rects = best_rect.split(width, height)
        self.free_rects.extend(split_rects)
        
        return (pos_x, pos_y)

class MultiTextureManager:
    """Handle multiple textures in Blockbench models"""
    
    def __init__(self):
        self.textures_cache = {}
    
    def extract_all_textures(self, bbmodel_data: Dict[str, Any]) -> Dict[int, Image.Image]:
        """Extract all textures from BBModel data"""
        
        textures = bbmodel_data.get("textures", [])
        extracted_textures = {}
        
        print(f"### Extraction of {len(textures)} textures ###")

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
                    
                    if default_texture is None:
                        default_texture = texture_image
                else:
                    print(f"  Error extracting texture {texture_id} ({texture_name})")
                    
            except (ValueError, TypeError):
                print(f"ID of invalid texture: {texture_id}")
                continue
        
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
                    texture_id = int(texture_id) 
                    if texture_id == 0 and 1 in self.textures_cache:
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
        """Create an atlas texture for multiple textures using bin packing algorithm"""

        texture_regions = {}
        texture_sizes = []
        
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
                texture_sizes.append((texture_id, region.width, region.height))
                print(f"    Region texture {texture_id}: {region.size}")
        
        if not texture_regions:
            print("    No valid texture regions found")
            return None

        texture_sizes.sort(key=lambda x: x[1] * x[2], reverse=True)
        
        total_area = sum(w * h for _, w, h in texture_sizes)
        initial_size = max(64, int((total_area ** 0.5) * 1.2))
        
        for atlas_size in [initial_size, initial_size * 2, initial_size * 4]:
            packer = BinPacker(atlas_size, atlas_size)
            
            all_packed = True
            for texture_id, width, height in texture_sizes:
                if packer.pack(texture_id, width, height) is None:
                    all_packed = False
                    break
            
            if all_packed:
                print(f"    Bin-packed atlas: {atlas_size}x{atlas_size} for {len(texture_sizes)} textures")
                
                atlas = Image.new('RGBA', (atlas_size, atlas_size), (0, 0, 0, 0))
                
                for texture_id, (x, y, width, height) in packer.placements.items():
                    region = texture_regions[texture_id]
                    atlas.paste(region, (x, y))
                    print(f"      Placed texture {texture_id} at ({x}, {y})")
                
                return atlas
        
        print("    Bin packing failed, falling back to grid layout")
        return self._create_grid_atlas(texture_regions)
        
    def _create_grid_atlas(self, texture_regions: Dict[int, Image.Image]) -> Image.Image:
        """Fallback grid-based atlas creation"""
        num_textures = len(texture_regions)
        max_width = max(region.width for region in texture_regions.values())
        max_height = max(region.height for region in texture_regions.values())
        
        cols = int(num_textures ** 0.5) + 1
        rows = (num_textures + cols - 1) // cols
        
        atlas_width = max_width * cols
        atlas_height = max_height * rows
        
        atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        
        for i, (texture_id, region) in enumerate(texture_regions.items()):
            row = i // cols
            col = i % cols
            x = col * max_width
            y = row * max_height
            atlas.paste(region, (x, y))
            
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
        if not (texture.width & (texture.width - 1) == 0) or \
           not (texture.height & (texture.height - 1) == 0):
            print(f"Warning: Texture dimensions ({texture.width}x{texture.height}) are not power of 2")
            return False

        if texture.width > 1024 or texture.height > 1024:
            print("Warning: Texture exceeds maximum size of 1024x1024")
            return False
            
        return True