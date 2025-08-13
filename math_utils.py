"""Math utilities for conversions"""

import math
import numpy as np
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

        Ry = np.array([
            [cos_y, 0, sin_y, 0],
            [0, 1, 0, 0],
            [-sin_y, 0, cos_y, 0],
            [0, 0, 0, 1]
        ])
        
        Rx = np.array([
            [1, 0, 0, 0],
            [0, cos_x, -sin_x, 0],
            [0, sin_x, cos_x, 0],
            [0, 0, 0, 1]
        ])
        
        Rz = np.array([
            [cos_z, -sin_z, 0, 0],
            [sin_z, cos_z, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        final_matrix = Rz @ Rx @ Ry
        
        return final_matrix.flatten().tolist()
    
    @staticmethod
    def apply_rotation_to_point(x: float, y: float, z: float, rotation: List[float]) -> Tuple[float, float, float]:
        """Apply rotation to a 3D point using Blockbench rotation order"""
        
        if rotation == [0, 0, 0]:
            return x, y, z
        
        rotation_matrix = np.array(MathUtils.create_rotation_matrix(rotation)).reshape(4, 4)
        point = np.array([x, y, z, 1])
        
        rotated_point = rotation_matrix @ point
        
        return rotated_point[0], rotated_point[1], rotated_point[2]
    
    @staticmethod
    def create_rotation_matrix_3x3(rotation: List[float]) -> List[float]:
        """
        3x3 (row-major) rotation using the same Blockbench order as create_rotation_matrix.
        """
        M4 = MathUtils.create_rotation_matrix(rotation)
        return [M4[0], M4[1], M4[2],
                M4[4], M4[5], M4[6],
                M4[8], M4[9], M4[10]]

    @staticmethod
    def mul33(a: List[float], b: List[float]) -> List[float]:
        """
        Multiply two 3x3 row-major matrices: returns (a · b) as row-major list length 9.
        """
        A = np.array(a, dtype=float).reshape(3, 3)
        B = np.array(b, dtype=float).reshape(3, 3)
        C = A @ B
        return C.reshape(-1).tolist()

    @staticmethod
    def apply_matrix(M: List[float], p: List[float]) -> List[float]:
        """
        Apply a 4x4 row-major matrix M to a 3D point p (homogeneous w=1).
        Returns a 3D list [x', y', z'].
        """
        mat = np.array(M, dtype=float).reshape(4, 4)
        v = np.array([p[0], p[1], p[2], 1.0], dtype=float)
        out = mat @ v
        return [float(out[0]), float(out[1]), float(out[2])]


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