"""Factory for creating BDEngine player heads"""

from typing import List, Dict, Any, Tuple
from config import Config
from math_utils import MathUtils, CoordinateConverter

class HeadFactory:
    """Factory for creating player heads"""
    
    def __init__(self):
        self.config = Config()
        self.math_utils = MathUtils()
        self.coord_converter = CoordinateConverter()
    
    def create_head_from_bottom_coords(self, bottom_x: float, bottom_y: float, bottom_z: float,
                                     width: float, height: float, depth: float,
                                     model_center: List[float], rotation: List[float] = None,
                                     texture: str = None) -> Dict[str, Any]:
        """Creates head from bottom corner coordinates and dimensions"""
        
        if rotation is None:
            rotation = [0, 0, 0]
        
        # Calculate scales
        scale_x = max(width / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_y = max(height / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_z = max(depth / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        
        # Convert bottom corner position to head position
        pos_x, pos_y, pos_z = self.coord_converter.bottom_to_head_position(
            bottom_x, bottom_y, bottom_z, width, height, depth, model_center
        )
        
        # Create transformation matrix with rotation
        transforms = self._create_transform_matrix(scale_x, scale_y, scale_z, 
                                                 pos_x, pos_y, pos_z, rotation)
        
        # Create head element with loaded texture
        head_element = self.config.get_head_base_structure()
        head_element["transforms"] = transforms
        
        # Use custom texture if provided, otherwise keep default loaded texture
        if texture is not None:
            head_element["paintTexture"] = texture
        
        return head_element
    
    def create_subdivided_head_with_element_rotation(self, cube_pos: Tuple[float, float, float], 
                                                   cube_size: Tuple[float, float, float],
                                                   element_bottom_corner: Tuple[float, float, float],
                                                   element_size: Tuple[float, float, float],
                                                   element_rotation: List[float],
                                                   element_origin: Tuple[float, float, float],
                                                   model_center: List[float],
                                                   texture: str = None) -> Dict[str, Any]:
        """Creates head for subdivided cube with proper element-level rotation"""
        
        # 1. Calculer la position absolue du cube dans l'espace Blockbench
        cube_x = element_bottom_corner[0] + cube_pos[0]
        cube_y = element_bottom_corner[1] + cube_pos[1]
        cube_z = element_bottom_corner[2] + cube_pos[2]
        
        cube_width, cube_height, cube_depth = cube_size
        
        print(f"    Cube position absolue: ({cube_x:.6f}, {cube_y:.6f}, {cube_z:.6f})")
        print(f"    Élément origin: {element_origin}")
        print(f"    Élément rotation: {element_rotation}")
        
        # 2. Si pas de rotation, utiliser la méthode classique
        if element_rotation == [0, 0, 0]:
            return self.create_head_from_bottom_coords(
                cube_x, cube_y, cube_z, cube_width, cube_height, cube_depth,
                model_center, element_rotation, texture
            )
        
        # 3. Calculer le centre du cube avec plus de précision
        cube_center_x = cube_x + cube_width / 2.0
        cube_center_y = cube_y + cube_height / 2.0
        cube_center_z = cube_z + cube_depth / 2.0
        
        # 4. Appliquer la rotation de l'élément au centre du cube
        origin_x, origin_y, origin_z = element_origin
        
        # Translater vers l'origine de rotation avec précision
        translated_x = cube_center_x - origin_x
        translated_y = cube_center_y - origin_y
        translated_z = cube_center_z - origin_z
        
        print(f"    Centre cube avant rotation: ({cube_center_x:.6f}, {cube_center_y:.6f}, {cube_center_z:.6f})")
        print(f"    Position relative à l'origine: ({translated_x:.6f}, {translated_y:.6f}, {translated_z:.6f})")
        
        # Appliquer la rotation avec la fonction corrigée
        rotated_x, rotated_y, rotated_z = self.math_utils.apply_rotation_to_point(
            translated_x, translated_y, translated_z, element_rotation
        )
        
        # Translater de retour avec précision
        final_center_x = rotated_x + origin_x
        final_center_y = rotated_y + origin_y
        final_center_z = rotated_z + origin_z
        
        print(f"    Centre cube après rotation: ({final_center_x:.6f}, {final_center_y:.6f}, {final_center_z:.6f})")
        
        # 5. Calculer la nouvelle position bottom corner avec précision
        rotated_bottom_x = final_center_x - cube_width / 2.0
        rotated_bottom_y = final_center_y - cube_height / 2.0
        rotated_bottom_z = final_center_z - cube_depth / 2.0
        
        print(f"    Bottom corner après rotation: ({rotated_bottom_x:.6f}, {rotated_bottom_y:.6f}, {rotated_bottom_z:.6f})")
        
        # 6. Créer la tête avec la rotation et la position corrigée
        
        # Calculate scales
        scale_x = max(cube_width / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_y = max(cube_height / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_z = max(cube_depth / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        
        # Convert bottom corner position to head position
        pos_x, pos_y, pos_z = self.coord_converter.bottom_to_head_position(
            rotated_bottom_x, rotated_bottom_y, rotated_bottom_z, 
            cube_width, cube_height, cube_depth, model_center
        )
        
        # Create transformation matrix with element rotation using corrected rotation matrix
        transforms = self._create_transform_matrix(scale_x, scale_y, scale_z, 
                                                 pos_x, pos_y, pos_z, element_rotation)
        
        # Create head element
        head_element = self.config.get_head_base_structure()
        head_element["transforms"] = transforms
        
        if texture is not None:
            head_element["paintTexture"] = texture
        
        print(f"    Position finale BDEngine: ({pos_x:.6f}, {pos_y:.6f}, {pos_z:.6f})")
        
        return head_element
    
    def _create_transform_matrix(self, scale_x: float, scale_y: float, scale_z: float,
                               pos_x: float, pos_y: float, pos_z: float,
                               rotation: List[float]) -> List[float]:
        """Creates transformation matrix"""
        
        if rotation != [0, 0, 0]:
            rotation_matrix = self.math_utils.create_rotation_matrix(rotation)
            
            transforms = [
                rotation_matrix[0] * scale_x, rotation_matrix[1] * scale_y, rotation_matrix[2] * scale_z, pos_x,
                rotation_matrix[4] * scale_x, rotation_matrix[5] * scale_y, rotation_matrix[6] * scale_z, pos_y,
                rotation_matrix[8] * scale_x, rotation_matrix[9] * scale_y, rotation_matrix[10] * scale_z, pos_z,
                0, 0, 0, 1
            ]
        else:
            transforms = [
                scale_x, 0, 0, pos_x,
                0, scale_y, 0, pos_y,
                0, 0, scale_z, pos_z,
                0, 0, 0, 1
            ]
        
        return transforms
    
    def create_textured_head(self, bottom_x: float, bottom_y: float, bottom_z: float,
                           width: float, height: float, depth: float,
                           model_center: List[float], texture_path: str = None,
                           rotation: List[float] = None) -> Dict[str, Any]:
        """Creates head with texture from file path"""
        
        texture_data = None
        if texture_path:
            try:
                texture_data = self._load_texture_from_file(texture_path)
            except Exception as e:
                print(f"Warning: Could not load texture from {texture_path}: {e}")
                print("Using default texture")
        
        return self.create_head_from_bottom_coords(
            bottom_x, bottom_y, bottom_z, width, height, depth,
            model_center, rotation, texture_data
        )
    
    def _load_texture_from_file(self, texture_path: str) -> str:
        """Load texture from file and convert to base64"""
        import base64
        import io
        from PIL import Image
        
        image = Image.open(texture_path)
        
        # Convert to RGBA if not already
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Convert to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"