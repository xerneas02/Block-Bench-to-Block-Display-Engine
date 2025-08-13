"""Conversion strategies for different modes"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from element_analyzer import ElementAnalyzer, ElementType
from head_factory import HeadFactory
from smart_cube_optimizer import SmartCubeOptimizer
from texture_subdivider import TextureSubdivider
from PIL import Image
from math_utils import MathUtils
import numpy as np

class ConversionStrategy(ABC):
    def __init__(self):
        self.element_analyzer = ElementAnalyzer()
        self.head_factory = HeadFactory()
        self.converter = None

    def set_converter(self, converter):
        self.converter = converter

    @abstractmethod
    def convert_element(self, element: Dict[str, Any], model_center: List[float], 
                       texture: Optional[str] = None) -> List[Dict[str, Any]]:
        """Converts element to heads"""
        pass

class StretchConversionStrategy(ConversionStrategy):
    """Stretch mode conversion strategy"""
    
    def convert_element(self, element: Dict[str, Any], model_center: List[float], 
                       texture: Optional[str] = None) -> List[Dict[str, Any]]:
        """Converts element to single stretched head"""
        
        element_type, info = self.element_analyzer.analyze_element(element)
        
        print(f"Stretch mode - {element_type.value}: corner=({info['bottom_x']:.1f}, {info['bottom_y']:.1f}, {info['bottom_z']:.1f}), size=({info['width']:.1f}x{info['height']:.1f}x{info['depth']:.1f})")
        
        if element_type == ElementType.INVALID_SHAPE:
            print(f"Warning: invalid dimensions for element {info['name']}")
            return []
        
        head = self.head_factory.create_head_from_bottom_coords(
            info['bottom_x'], info['bottom_y'], info['bottom_z'],
            info['width'], info['height'], info['depth'],
            model_center, info['rotation'], texture
        )
        
        return [head]

class SmartCubeConversionStrategy(ConversionStrategy):
    """Smart cube mode with shape preservation, square pixels and texture subdivision"""
    
    def __init__(self):
        super().__init__()
        self.smart_optimizer = SmartCubeOptimizer()
        self.texture_subdivider = TextureSubdivider()
    
    def convert_element(self, element: Dict[str, Any], model_center: List[float], 
                   texture: Optional[str] = None, source_texture_size: Optional[Tuple[int, int]] = None,
                   source_texture: Optional[Any] = None, all_textures: Optional[Dict[int, Image.Image]] = None) -> List[Dict[str, Any]]:
        """
        Smart conversion: one BDE collection per Blockbench element.
        The collection carries rotation + translation (parent chain * element rotation).
        All child heads are axis-aligned in the element's local frame, preserving brick integrity.
        """

        element_type, info = self.element_analyzer.analyze_element(element)
        if element_type == ElementType.INVALID_SHAPE:
            print(f"Warning: invalid dimensions for element {info['name']}")
            return []

        print(f"\n### SMART Conversion (group rotates) for {info['name']} ###")
        print(f"Original shape: {info['width']}x{info['height']}x{info['depth']}")

        cube_divisions = self.smart_optimizer.calculate_optimal_3d_decomposition(
            info['width'], info['height'], info['depth'],
            element, source_texture_size, all_textures
        )

        if all_textures is not None:
            print("🎨 Texture subdivision with individual textures")
            cube_textures = self.texture_subdivider.subdivide_texture_for_cubes_with_individual_textures(
                element, cube_divisions, all_textures
            )
        elif source_texture and len(cube_divisions) > 1:
            print("🎨 Texture subdivision for multiple cubes")
            cube_textures = self.texture_subdivider.subdivide_texture_for_cubes(
                source_texture, element, cube_divisions
            )
        else:
            cube_textures = [texture] * len(cube_divisions)

        element_bottom_corner = (info['bottom_x'], info['bottom_y'], info['bottom_z'])
        element_origin = element.get('origin', [
            info['bottom_x'] + info['width'] / 2,
            info['bottom_y'],
            info['bottom_z'] + info['depth'] / 2
        ])

        parent_M = self.converter._accumulate_parent_matrix(element.get("uuid")) if self.converter else [
            1,0,0,0,  0,1,0,0,  0,0,1,0,  0,0,0,1
        ]

        parent_R = [
            parent_M[0], parent_M[1], parent_M[2],
            parent_M[4], parent_M[5], parent_M[6],
            parent_M[8], parent_M[9], parent_M[10]
        ]

        elem_M4 = MathUtils.create_rotation_matrix(info['rotation'])
        elem_R = [
            elem_M4[0], elem_M4[1], elem_M4[2],
            elem_M4[4], elem_M4[5], elem_M4[6],
            elem_M4[8], elem_M4[9], elem_M4[10]
        ]

        R_group = self.head_factory.math_utils.mul33(parent_R, elem_R)

        origin_world = self.head_factory.math_utils.apply_matrix(parent_M, [element_origin[0], element_origin[1], element_origin[2]])
        pos_x = (origin_world[0] - model_center[0]) / 16.0
        pos_y = (origin_world[1] - model_center[1]) / 16.0
        pos_z = (origin_world[2] - model_center[2]) / 16.0

        r00,r01,r02, r10,r11,r12, r20,r21,r22 = R_group
        element_group = {
            "isCollection": True,
            "isBackCollection": False,
            "name": element.get("name", info.get("name","Grouped Element")),
            "nbt": "",
            "transforms": [r00,r01,r02,pos_x,  r10,r11,r12,pos_y,  r20,r21,r22,pos_z,  0,0,0,1],
            "children": [],
            "defaultTransform": {"position":[0,0,0], "rotation":{"x":0,"y":0,"z":0}, "scale":[1,1,1]},
            "_grouped_subdivision": True
        }

        for i, division in enumerate(cube_divisions):
            print(f"  Cube {i+1}: pos={division['position']}, size={division['size']}")
            current_texture = cube_textures[i] if i < len(cube_textures) and cube_textures[i] else texture

            head = self.head_factory.create_local_head_in_element_frame(
                division['position'], division['size'],
                element_bottom_corner, element_origin,
                texture=current_texture
            )

            head["_smart_info"] = {
                "original_size": (info['width'], info['height'], info['depth']),
                "cube_info": division,
                "preserves_shape": True,
                "has_subdivided_texture": current_texture != texture and current_texture is not None,
                "element_rotation": info['rotation'],
                "uses_element_rotation": False,
                "grouped": True
            }
            element_group["children"].append(head)

        total_volume = sum(d['size'][0] * d['size'][1] * d['size'][2] for d in cube_divisions)
        original_volume = info['width'] * info['height'] * info['depth']
        print(f"### Verification: original volume={original_volume:.1f}, total volume={total_volume:.1f} ###")
        print(f"### {len(element_group['children'])} child heads generated ###\n")

        return [element_group]



TextureAwareCubeConversionStrategy = SmartCubeConversionStrategy
CubeConversionStrategy = SmartCubeConversionStrategy