"""Subdivide Minecraft head textures for multiple cubes with correct face mapping and orientation."""

import base64
import json
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional
import math

class TextureSubdivider:
    """Divide textures for multiple heads with correct face mapping and orientation"""
    
    def __init__(self):
        self.head_texture_size = 64
        self.head_active_area = 32
        
        self.head_face_mapping = {
            "up": {"region": (8, 0, 16, 8)},       # Top face (8x8)
            "down": {"region": (16, 0, 24, 8)},    # Bottom face (8x8)
            "north": {"region": (8, 8, 16, 16)},   # Front face (8x8)
            "south": {"region": (24, 8, 32, 16)},  # Back face (8x8)
            "east": {"region": (0, 8, 8, 16)},     # Right face (8x8)
            "west": {"region": (16, 8, 24, 16)}    # Left face (8x8)
        }
    
    def subdivide_texture_for_cubes(self, source_texture: Image.Image, source_element: Dict[str, Any], 
                                   cube_divisions: List[Dict[str, Any]]) -> List[Optional[str]]:
        """Subdivide texture for multiple cubes with correct face mapping and orientation"""
        
        print(f"\n### Subdivision for texture {len(cube_divisions)} cubes ###")
        
        source_faces = source_element.get("faces", {})
        
        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Original element: {total_width}x{total_height}x{total_depth}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nComputing cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube(
                source_texture, source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions
            )
            
            if cube_texture:
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                debug_filename = f"debug_cube_{i+1}_texture.png"
                cube_texture.save(debug_filename)
                print(f"Texture saved: {debug_filename}")
                
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube(self, source_texture: Image.Image, source_faces: Dict[str, Any], 
                                cube_division: Dict[str, Any], cube_index: int, 
                                total_element_size: Tuple[float, float, float], 
                                all_cube_divisions: List[Dict[str, Any]]) -> Optional[Image.Image]:
        """Create texture for a single cube with correct face mapping and orientation"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"Position: {cube_pos}, Size: {cube_size}")
        
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_texture = self._extract_face_texture_for_cube(
                        source_texture, source_faces[face_name], cube_pos, cube_size, face_name, total_element_size
                    )
                    
                    if face_texture:
                        face_texture = face_texture.resize((8, 8), Image.NEAREST)
                        
                        target_region = face_info["region"]
                        head_texture.paste(face_texture, target_region)
                        
                        print(f"Face {face_name}: ✅ visible")
                    else:
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"Face {face_name}: ⬛ (extraction error)")
                else:
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"Face {face_name}: ⬛ (hidden)")
            else:
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"Face {face_name}: ⬛ (undefined)")
        
        return head_texture
    
    def _extract_face_texture_for_cube(self, source_texture: Image.Image, face_data: Dict[str, Any], 
                                      cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                      face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extract the texture for a specific face of a cube with correct UV mapping"""
        
        try:
            original_uv = face_data.get("uv", [0, 0, 0, 0])
            
            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"Original UV {face_name}: ({left}, {top}, {right}, {bottom})")
            
            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, source_texture
            )
            
            if face_region is None:
                return None
            
            print(f"Region computed: {face_region}")
            
            face_texture = source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"Error extracting face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calculate which region of the original face corresponds to this cube with EXACT mapping and correct orientation"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv
        
        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":
            x_ratio_start = cube_x / total_w
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":
            z_ratio_start = cube_z / total_d
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None

        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, max(final_left + 1, int(round(new_right))))
        final_bottom = min(source_texture.height, max(final_top + 1, int(round(new_bottom))))

        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Invalid region: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Final mapping (corrected {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Determine if a face is visible for a cube (not hidden by another cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size

        if face_name == "north":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)
            
        elif face_name == "south":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)
            
        elif face_name == "west":
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)
            
        elif face_name == "east":
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)
            
        elif face_name == "down":
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)
            
        elif face_name == "up":
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0)
            
        else:
            return True
        
        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} blocked by cube at {other_pos}")
                return False
        
        return True
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Check if a cube blocks a face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal

        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d

        tolerance = 0.1
        
        if normal_x > 0:
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Create an entirely black texture for hidden faces"""

        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))

        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def subdivide_texture_for_cubes_with_individual_textures(self, source_element: Dict[str, Any], 
                                                          cube_divisions: List[Dict[str, Any]], 
                                                          all_textures: Dict[int, Image.Image]) -> List[Optional[str]]:
        """Subdivide textures with individual face textures handling"""
        
        print(f"\n### Subdivision texture for {len(cube_divisions)} cubes with individual textures ###")

        source_faces = source_element.get("faces", {})

        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Original element: {total_width}x{total_height}x{total_depth}")
        print(f"Available textures: {list(all_textures.keys())}")

        for face_name, face_data in source_faces.items():
            texture_id = face_data.get("texture")
            uv = face_data.get("uv", [0, 0, 16, 16])
            print(f"Face {face_name}: texture {texture_id}, UV {uv}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nProcessing cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube_with_individual_textures(
                source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions, all_textures
            )
            
            if cube_texture:
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                print(f"Texture generated for cube {i+1}")
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube_with_individual_textures(self, source_faces: Dict[str, Any], 
                                                        cube_division: Dict[str, Any], cube_index: int, 
                                                        total_element_size: Tuple[float, float, float], 
                                                        all_cube_divisions: List[Dict[str, Any]],
                                                        all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Create a head texture for a specific cube with individual face textures"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"Position: {cube_pos}, Size: {cube_size}")
        
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_data = source_faces[face_name]
                    texture_id = face_data.get("texture")
                    
                    if texture_id is not None and int(texture_id) in all_textures:
                        face_source_texture = all_textures[int(texture_id)]
                        
                        face_texture = self._extract_face_texture_for_cube_individual(
                            face_source_texture, face_data, cube_pos, cube_size, face_name, total_element_size
                        )
                        
                        if face_texture:
                            face_texture = face_texture.resize((8, 8), Image.NEAREST)
                            
                            target_region = face_info["region"]
                            head_texture.paste(face_texture, target_region)
                            
                            print(f"Face {face_name}: ✅ texture {texture_id}")
                        else:
                            black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                            target_region = face_info["region"]
                            head_texture.paste(black_face, target_region)
                            print(f"Face {face_name}: ⬛ (extraction error texture {texture_id})")
                    else:
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"Face {face_name}: ⬛ (texture {texture_id} not found)")
                else:
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"Face {face_name}: ⬛ (hidden)")
            else:
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"Face {face_name}: ⬛ (not defined)")
        
        return head_texture
    
    def _extract_face_texture_for_cube_individual(self, face_source_texture: Image.Image, face_data: Dict[str, Any], 
                                                cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                                face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extract the texture of a face for a specific cube with individual texture"""
        
        try:
            original_uv = face_data.get("uv", [0, 0, face_source_texture.width, face_source_texture.height])

            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"Original UVs {face_name}: ({left}, {top}, {right}, {bottom}) on texture {face_source_texture.size}")

            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, face_source_texture
            )
            
            if face_region is None:
                return None
            
            print(f"Region calculated: {face_region}")

            face_texture = face_source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"Error extracting face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calculate which region of the original face corresponds to this cube with EXACT mapping and correct orientation"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv

        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":
            x_ratio_start = cube_x / total_w
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":
            z_ratio_start = cube_z / total_d
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None

        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, max(final_left + 1, int(round(new_right))))
        final_bottom = min(source_texture.height, max(final_top + 1, int(round(new_bottom))))

        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Invalid region: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Final mapping (corrected {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Determine if a face is visible for a cube (not hidden by another cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size

        if face_name == "north":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)
            
        elif face_name == "south":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)
            
        elif face_name == "west":
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)
            
        elif face_name == "east":
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)
            
        elif face_name == "down":
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)
            
        elif face_name == "up":
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0)
            
        else:
            return True
        
        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} blocked by cube at {other_pos}")
                return False
        
        return True
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Check if a cube blocks a face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal
        
        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d
        
        tolerance = 0.1
        
        if normal_x > 0:
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Create an entirely black texture for hidden faces"""
        
        # Create a black head texture
        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))
        
        # Convert to base64
        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def subdivide_texture_for_cubes_with_individual_textures(self, source_element: Dict[str, Any], 
                                                          cube_divisions: List[Dict[str, Any]], 
                                                          all_textures: Dict[int, Image.Image]) -> List[Optional[str]]:
        """Subdivide textures with individual face textures handling"""
        
        print(f"\n### Subdivision texture for {len(cube_divisions)} cubes with individual textures ###")
        
        source_faces = source_element.get("faces", {})

        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Original element: {total_width}x{total_height}x{total_depth}")
        print(f"Available textures: {list(all_textures.keys())}")

        for face_name, face_data in source_faces.items():
            texture_id = face_data.get("texture")
            uv = face_data.get("uv", [0, 0, 16, 16])
            print(f"Face {face_name}: texture {texture_id}, UV {uv}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nProcessing cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube_with_individual_textures(
                source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions, all_textures
            )
            
            if cube_texture:
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                print(f"Texture generated for cube {i+1}")
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube_with_individual_textures(self, source_faces: Dict[str, Any], 
                                                        cube_division: Dict[str, Any], cube_index: int, 
                                                        total_element_size: Tuple[float, float, float], 
                                                        all_cube_divisions: List[Dict[str, Any]],
                                                        all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Create a head texture for a specific cube with individual face textures"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"Position: {cube_pos}, Size: {cube_size}")
        
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_data = source_faces[face_name]
                    texture_id = face_data.get("texture")
                    
                    if texture_id is not None and int(texture_id) in all_textures:
                        face_source_texture = all_textures[int(texture_id)]
                        
                        face_texture = self._extract_face_texture_for_cube_individual(
                            face_source_texture, face_data, cube_pos, cube_size, face_name, total_element_size
                        )
                        
                        if face_texture:
                            face_texture = face_texture.resize((8, 8), Image.NEAREST)

                            target_region = face_info["region"]
                            head_texture.paste(face_texture, target_region)
                            
                            print(f"Face {face_name}: ✅ texture {texture_id}")
                        else:
                            black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                            target_region = face_info["region"]
                            head_texture.paste(black_face, target_region)
                            print(f"Face {face_name}: ⬛ (extraction error texture {texture_id})")
                    else:
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"Face {face_name}: ⬛ (texture {texture_id} not found)")
                else:
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"Face {face_name}: ⬛ (hidden)")
            else:
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"Face {face_name}: ⬛ (not defined)")
        
        return head_texture
    
    def _extract_face_texture_for_cube_individual(self, face_source_texture: Image.Image, face_data: Dict[str, Any], 
                                                cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                                face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extract the texture of a face for a specific cube with individual texture"""
        
        try:
            original_uv = face_data.get("uv", [0, 0, face_source_texture.width, face_source_texture.height])

            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"Original UVs {face_name}: ({left}, {top}, {right}, {bottom}) on texture {face_source_texture.size}")

            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, face_source_texture
            )
            
            if face_region is None:
                return None
            
            print(f"Region calculated: {face_region}")

            face_texture = face_source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"Error extracting face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calculate which region of the original face corresponds to this cube with EXACT mapping and correct orientation"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv

        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":
            x_ratio_start = cube_x / total_w
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":
            z_ratio_start = cube_z / total_d
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None

        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, max(final_left + 1, int(round(new_right))))
        final_bottom = min(source_texture.height, max(final_top + 1, int(round(new_bottom))))

        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Invalid region: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Final mapping (corrected {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Determine if a face is visible for a cube (not hidden by another cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size

        if face_name == "north":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)
            
        elif face_name == "south":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)
            
        elif face_name == "west":
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)
            
        elif face_name == "east":
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)
            
        elif face_name == "down":
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)
            
        elif face_name == "up":
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0) 
            
        else:
            return True
        
        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} blocked by cube at {other_pos}")
                return False
        
        return True
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Check if a cube blocks a face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal
        
        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d
        
        tolerance = 0.1
        
        if normal_x > 0:
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Create an entirely black texture for hidden faces"""

        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))

        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def subdivide_texture_for_cubes_with_individual_textures(self, source_element: Dict[str, Any], 
                                                          cube_divisions: List[Dict[str, Any]], 
                                                          all_textures: Dict[int, Image.Image]) -> List[Optional[str]]:
        """Subdivide textures with individual face textures handling"""
        
        print(f"\n### Subdivision texture for {len(cube_divisions)} cubes with individual textures ###")

        source_faces = source_element.get("faces", {})

        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Original element: {total_width}x{total_height}x{total_depth}")
        print(f"Available textures: {list(all_textures.keys())}")

        for face_name, face_data in source_faces.items():
            texture_id = face_data.get("texture")
            uv = face_data.get("uv", [0, 0, 16, 16])
            print(f"Face {face_name}: texture {texture_id}, UV {uv}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nProcessing cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube_with_individual_textures(
                source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions, all_textures
            )
            
            if cube_texture:
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                print(f"Texture generated for cube {i+1}")
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube_with_individual_textures(self, source_faces: Dict[str, Any], 
                                                        cube_division: Dict[str, Any], cube_index: int, 
                                                        total_element_size: Tuple[float, float, float], 
                                                        all_cube_divisions: List[Dict[str, Any]],
                                                        all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Create a head texture for a specific cube with individual face textures"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"Position: {cube_pos}, Size: {cube_size}")
        
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_data = source_faces[face_name]
                    texture_id = face_data.get("texture")
                    
                    if texture_id is not None and int(texture_id) in all_textures:
                        face_source_texture = all_textures[int(texture_id)]
                        
                        face_texture = self._extract_face_texture_for_cube_individual(
                            face_source_texture, face_data, cube_pos, cube_size, face_name, total_element_size
                        )
                        
                        if face_texture:
                            face_texture = face_texture.resize((8, 8), Image.NEAREST)

                            target_region = face_info["region"]
                            head_texture.paste(face_texture, target_region)
                            
                            print(f"Face {face_name}: ✅ texture {texture_id}")
                        else:
                            black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                            target_region = face_info["region"]
                            head_texture.paste(black_face, target_region)
                            print(f"Face {face_name}: ⬛ (extraction error texture {texture_id})")
                    else:
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"Face {face_name}: ⬛ (texture {texture_id} not found)")
                else:
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"Face {face_name}: ⬛ (hidden)")
            else:
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"Face {face_name}: ⬛ (not defined)")
        
        return head_texture
    
    def _extract_face_texture_for_cube_individual(self, face_source_texture: Image.Image, face_data: Dict[str, Any], 
                                                cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                                face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extract the texture of a face for a specific cube with individual texture"""
        
        try:
            original_uv = face_data.get("uv", [0, 0, face_source_texture.width, face_source_texture.height])

            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"Original UVs {face_name}: ({left}, {top}, {right}, {bottom}) on texture {face_source_texture.size}")

            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, face_source_texture
            )
            
            if face_region is None:
                return None
            
            print(f"Region calculated: {face_region}")

            face_texture = face_source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"Error extracting face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calculate which region of the original face corresponds to this cube with EXACT mapping and correct orientation"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv

        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":
            x_ratio_start = cube_x / total_w
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":
            z_ratio_start = cube_z / total_d
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None

        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, max(final_left + 1, int(round(new_right))))
        final_bottom = min(source_texture.height, max(final_top + 1, int(round(new_bottom))))

        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Invalid region: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Final mapping (corrected {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Determine if a face is visible for a cube (not hidden by another cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size

        if face_name == "north":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)
            
        elif face_name == "south":
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)
            
        elif face_name == "west":
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)
            
        elif face_name == "east":
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)
            
        elif face_name == "down":
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)
            
        elif face_name == "up":
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0)
            
        else:
            return True

        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} blocked by cube at {other_pos}")
                return False
        
        return True
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Check if a cube blocks a face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal

        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d

        tolerance = 0.1
        
        if normal_x > 0:
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Create an entirely black texture for hidden faces"""

        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))

        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"