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
        
        scale_x = max(width / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_y = max(height / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_z = max(depth / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        
        pos_x, pos_y, pos_z = self.coord_converter.bottom_to_head_position(
            bottom_x, bottom_y, bottom_z, width, height, depth, model_center
        )
        
        transforms = self._create_transform_matrix(scale_x, scale_y, scale_z, 
                                                 pos_x, pos_y, pos_z, rotation)
        
        head_element = self.config.get_head_base_structure()
        head_element["transforms"] = transforms

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
        """Create a head for a subdivided cube with correct element-level rotation.

        Key idea: BDEngine places a head by the center of its top face (top-center).
        So when rotation is present, rotate the cube's *top-center* around the
        Blockbench element origin, then use the rotated top-center directly to compute
        the BDEngine translation. Avoid reconstructing a bottom corner post-rotation,
        which assumes axis alignment and introduces drift.
        """

        cube_x = element_bottom_corner[0] + cube_pos[0]
        cube_y = element_bottom_corner[1] + cube_pos[1]
        cube_z = element_bottom_corner[2] + cube_pos[2]

        cube_width, cube_height, cube_depth = cube_size

        print(f"    Cube position absolue: ({cube_x:.6f}, {cube_y:.6f}, {cube_z:.6f})")
        print(f"    Élément origin: {element_origin}")
        print(f"    Élément rotation: {element_rotation}")

        if element_rotation == [0, 0, 0]:
            return self.create_head_from_bottom_coords(
                cube_x, cube_y, cube_z, cube_width, cube_height, cube_depth,
                model_center, element_rotation, texture
            )

        top_center_x = cube_x + cube_width  * 0.5
        top_center_y = cube_y + cube_height       
        top_center_z = cube_z + cube_depth  * 0.5

        origin_x, origin_y, origin_z = element_origin

        rel_x = top_center_x - origin_x
        rel_y = top_center_y - origin_y
        rel_z = top_center_z - origin_z

        print(f"    Top-center avant rotation: ({top_center_x:.6f}, {top_center_y:.6f}, {top_center_z:.6f})")
        print(f"    Top-center relatif à l'origine: ({rel_x:.6f}, {rel_y:.6f}, {rel_z:.6f})")

        rot_x, rot_y, rot_z = self.math_utils.apply_rotation_to_point(rel_x, rel_y, rel_z, element_rotation)

        final_top_center_x = rot_x + origin_x
        final_top_center_y = rot_y + origin_y
        final_top_center_z = rot_z + origin_z

        print(f"    Top-center après rotation: ({final_top_center_x:.6f}, {final_top_center_y:.6f}, {final_top_center_z:.6f})")

        pos_x = (final_top_center_x - model_center[0]) / 16.0
        pos_y = (final_top_center_y - model_center[1]) / 16.0
        pos_z = (final_top_center_z - model_center[2]) / 16.0

        scale_x = max(cube_width  / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_y = max(cube_height / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_z = max(cube_depth  / self.config.HEAD_SIZE, self.config.MIN_SCALE)

        transforms = self._create_transform_matrix(
            scale_x, scale_y, scale_z,
            pos_x, pos_y, pos_z,
            element_rotation
        )

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
    
    def create_local_head_in_element_frame(self, cube_pos, cube_size,
                                        element_bottom_corner, element_origin,
                                        texture=None):
        cx = element_bottom_corner[0] + cube_pos[0]
        cy = element_bottom_corner[1] + cube_pos[1]
        cz = element_bottom_corner[2] + cube_pos[2]
        w, h, d = cube_size
        # top-center relative to element origin, then → blocks
        pos_x = (cx + w*0.5 - element_origin[0]) / 16.0
        pos_y = (cy + h      - element_origin[1]) / 16.0
        pos_z = (cz + d*0.5 - element_origin[2]) / 16.0

        sx = max(w / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        sy = max(h / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        sz = max(d / self.config.HEAD_SIZE, self.config.MIN_SCALE)

        # identity rotation; column-scaled (basis vectors)
        transforms = [
            1*sx, 0*sx, 0*sx, pos_x,
            0*sy, 1*sy, 0*sy, pos_y,
            0*sz, 0*sz, 1*sz, pos_z,
            0,0,0,1
        ]
        head = self.config.get_head_base_structure()
        head["transforms"] = transforms
        if texture is not None:
            head["paintTexture"] = texture
        return head
    
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

        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def create_local_subcube_head(self,
                                  cube_pos: Tuple[float, float, float],
                                  cube_size: Tuple[float, float, float],
                                  element_bottom_corner: Tuple[float, float, float],
                                  element_origin: Tuple[float, float, float],
                                  texture: str = None) -> Dict[str, Any]:
        """
        Create a head for a subcube without applying element rotation or global translation.
        Translation is local (pre-rotation) relative to element origin.
        The local translation uses the same convention (top center) as standard heads,
        but measured in element-local (unrotated) space.
        """
        cube_x = element_bottom_corner[0] + cube_pos[0]
        cube_y = element_bottom_corner[1] + cube_pos[1]
        cube_z = element_bottom_corner[2] + cube_pos[2]

        cube_w, cube_h, cube_d = cube_size

        top_center_x = cube_x + cube_w * 0.5
        top_center_y = cube_y + cube_h
        top_center_z = cube_z + cube_d * 0.5

        # Local (pre-rotation) offset relative to origin, converted to head units (blocks)
        local_tx = (top_center_x - element_origin[0]) / 16.0
        local_ty = (top_center_y - element_origin[1]) / 16.0
        local_tz = (top_center_z - element_origin[2]) / 16.0

        scale_x = max(cube_w / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_y = max(cube_h / self.config.HEAD_SIZE, self.config.MIN_SCALE)
        scale_z = max(cube_d / self.config.HEAD_SIZE, self.config.MIN_SCALE)

        transforms = [
            scale_x, 0, 0, local_tx,
            0, scale_y, 0, local_ty,
            0, 0, scale_z, local_tz,
            0, 0, 0, 1
        ]

        head_element = self.config.get_head_base_structure()
        head_element["transforms"] = transforms
        if texture is not None:
            head_element["paintTexture"] = texture
        return head_element