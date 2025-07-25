"""Math utilities for conversions"""

import math
from typing import List, Tuple

class MathUtils:
    """Math utilities"""
    
    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        return degrees * math.pi / 180
    
    @staticmethod
    def create_rotation_matrix(rotation: List[float]) -> List[float]:
        """Creates 4x4 rotation matrix from X, Y, Z angles in degrees using Blockbench order"""
        rx, ry, rz = [MathUtils.degrees_to_radians(r) for r in rotation]
        
        cos_x, sin_x = math.cos(rx), math.sin(rx)
        cos_y, sin_y = math.cos(ry), math.sin(ry)
        cos_z, sin_z = math.cos(rz), math.sin(rz)
        
        # Blockbench rotation order: Z * X * Y (applied right to left)
        
        # Matrice rotation Y
        Ry = [
            cos_y, 0, sin_y, 0,
            0, 1, 0, 0,
            -sin_y, 0, cos_y, 0,
            0, 0, 0, 1
        ]
        
        # Matrice rotation X
        Rx = [
            1, 0, 0, 0,
            0, cos_x, -sin_x, 0,
            0, sin_x, cos_x, 0,
            0, 0, 0, 1
        ]
        
        # Matrice rotation Z
        Rz = [
            cos_z, -sin_z, 0, 0,
            sin_z, cos_z, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]
        
        # Rz * Rx * Ry
        temp = MathUtils._multiply_matrices_4x4(Rx, Ry)
        final = MathUtils._multiply_matrices_4x4(Rz, temp)
        
        return final
    
    @staticmethod
    def _multiply_matrices_4x4(a: List[float], b: List[float]) -> List[float]:
        """Multiplie deux matrices 4x4 représentées comme des listes"""
        result = [0] * 16
        
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    result[i * 4 + j] += a[i * 4 + k] * b[k * 4 + j]
        
        return result
    
    @staticmethod
    def apply_rotation_to_point(x: float, y: float, z: float, rotation: List[float]) -> Tuple[float, float, float]:
        """Apply rotation to a 3D point using Blockbench rotation order"""
        
        if rotation == [0, 0, 0]:
            return x, y, z
        
        rotation_matrix = MathUtils.create_rotation_matrix(rotation)
        
        x_new = rotation_matrix[0] * x + rotation_matrix[1] * y + rotation_matrix[2] * z
        y_new = rotation_matrix[4] * x + rotation_matrix[5] * y + rotation_matrix[6] * z
        z_new = rotation_matrix[8] * x + rotation_matrix[9] * y + rotation_matrix[10] * z
        
        return x_new, y_new, z_new

class CoordinateConverter:
    """Coordinate converter"""
    
    @staticmethod
    def bottom_to_head_position(bottom_x: float, bottom_y: float, bottom_z: float, 
                               width: float, height: float, depth: float, 
                               model_center: List[float]) -> Tuple[float, float, float]:
        """
        Converts bottom corner position to BDEngine head position
        Player heads are positioned by the center of their top face
        """
        center_x = bottom_x + width / 2
        center_z = bottom_z + depth / 2
        top_y = bottom_y + height 
        
        pos_x = (center_x - model_center[0]) / 16
        pos_y = (top_y - model_center[1]) / 16
        pos_z = (center_z - model_center[2]) / 16
        
        return pos_x, pos_y, pos_z
    
    @staticmethod
    def calculate_model_center(elements: List[dict]) -> List[float]:
        """Calculates model center with base at Y=0"""
        if not elements:
            return [0, 0, 0]
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for element in elements:
            from_coords = element.get("from", [0, 0, 0])
            to_coords = element.get("to", [1, 1, 1])
            
            min_x = min(min_x, from_coords[0])
            min_y = min(min_y, from_coords[1])
            min_z = min(min_z, from_coords[2])
            max_x = max(max_x, to_coords[0])
            max_y = max(max_y, to_coords[1])
            max_z = max(max_z, to_coords[2])
        
        center_x = (min_x + max_x) / 2
        center_y = min_y
        center_z = (min_z + max_z) / 2
        
        return [center_x, center_y, center_z]