"""Analyzer for Blockbench elements"""

from typing import List, Dict, Any, Tuple
from enum import Enum

class ElementType(Enum):
    """Detected element types"""
    PERFECT_CUBE = "perfect_cube"
    FLAT_SURFACE = "flat_surface" 
    STRETCHED_SHAPE = "stretched_shape"
    DEGENERATE_SHAPE = "degenerate_shape"
    INVALID_SHAPE = "invalid_shape"

class ElementAnalyzer:
    """Blockbench element analyzer"""
    
    def analyze_element(self, element: Dict[str, Any]) -> Tuple[ElementType, Dict[str, Any]]:
        """Analyzes element and returns type with information"""
        
        from_coords = element.get("from", [0, 0, 0])
        to_coords = element.get("to", [1, 1, 1])
        rotation = element.get("rotation", [0, 0, 0])
        
        width = abs(to_coords[0] - from_coords[0])
        height = abs(to_coords[1] - from_coords[1])
        depth = abs(to_coords[2] - from_coords[2])
        
        bottom_x = min(from_coords[0], to_coords[0])
        bottom_y = min(from_coords[1], to_coords[1])
        bottom_z = min(from_coords[2], to_coords[2])
        
        info = {
            "width": width,
            "height": height,
            "depth": depth,
            "bottom_x": bottom_x,
            "bottom_y": bottom_y,
            "bottom_z": bottom_z,
            "rotation": rotation,
            "name": element.get("name", "cube")
        }
        
        element_type = self._determine_element_type(width, height, depth)
        
        return element_type, info
    
    def _determine_element_type(self, width: float, height: float, depth: float) -> ElementType:
        """Determines element type based on dimensions"""
        
        zero_dimensions = sum([width == 0, height == 0, depth == 0])
        
        if width < 0 or height < 0 or depth < 0:
            return ElementType.INVALID_SHAPE
        
        if zero_dimensions == 1:
            return ElementType.FLAT_SURFACE
        
        if zero_dimensions >= 2:
            return ElementType.DEGENERATE_SHAPE
        
        if width == height == depth and width > 0:
            return ElementType.PERFECT_CUBE
        
        return ElementType.STRETCHED_SHAPE
    
    def get_flat_dimension(self, width: float, height: float, depth: float) -> str:
        """Returns flat dimension (the one that equals 0)"""
        if width == 0:
            return 'width'
        elif height == 0:
            return 'height'
        elif depth == 0:
            return 'depth'
        else:
            return None