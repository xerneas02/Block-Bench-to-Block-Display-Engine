"""Conversion strategies for different modes"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from element_analyzer import ElementAnalyzer, ElementType
from head_factory import HeadFactory
from smart_cube_optimizer import SmartCubeOptimizer
from texture_subdivider import TextureSubdivider
from PIL import Image

class ConversionStrategy(ABC):
    """Interface for conversion strategies"""
    
    def __init__(self):
        self.element_analyzer = ElementAnalyzer()
        self.head_factory = HeadFactory()
    
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
        """Converts element with smart decomposition, shape preservation and texture subdivision"""
        
        element_type, info = self.element_analyzer.analyze_element(element)
        
        if element_type == ElementType.INVALID_SHAPE:
            print(f"Warning: invalid dimensions for element {info['name']}")
            return []
        
        print(f"\n### SMART Conversion with texture subdivision for {info['name']} ###")
        print(f"Original shape: {info['width']}x{info['height']}x{info['depth']}")
        
        cube_divisions = self.smart_optimizer.calculate_optimal_3d_decomposition(
            info['width'], info['height'], info['depth'],
            element, source_texture_size, all_textures
        )

        
        cube_textures = []
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
        
        heads = []
        for i, division in enumerate(cube_divisions):
            print(f"  Cube {i+1}: pos=({division['position'][0]:.1f}, {division['position'][1]:.1f}, {division['position'][2]:.1f}), size=({division['size'][0]}x{division['size'][1]}x{division['size'][2]})")
            
            if division.get('is_perfect_cube', False):
                print(f"    → Perfect cube")
            elif 'stretch_info' in division:
                stretch = division['stretch_info']
                print(f"    → Controlled stretching: {stretch['x_stretch']}x{stretch['y_stretch']}x{stretch['z_stretch']}")
            
            current_texture = cube_textures[i] if i < len(cube_textures) and cube_textures[i] else texture
            if current_texture != texture and current_texture is not None:
                print(f"    → Subdivided texture applied")
            
            if info['rotation'] != [0, 0, 0]:
                element_origin = element.get('origin', [info['bottom_x'] + info['width']/2, 
                                                       info['bottom_y'], 
                                                       info['bottom_z'] + info['depth']/2])
                
                head = self.head_factory.create_subdivided_head_with_element_rotation(
                    division['position'], division['size'],
                    (info['bottom_x'], info['bottom_y'], info['bottom_z']),
                    (info['width'], info['height'], info['depth']),
                    info['rotation'], element_origin, model_center, current_texture
                )
            else:
                cube_x = info['bottom_x'] + division['position'][0]
                cube_y = info['bottom_y'] + division['position'][1]
                cube_z = info['bottom_z'] + division['position'][2]
                
                head = self.head_factory.create_head_from_bottom_coords(
                    cube_x, cube_y, cube_z,
                    division['size'][0], division['size'][1], division['size'][2],
                    model_center, info['rotation'], current_texture
                )
            
            head["_smart_info"] = {
                "original_size": (info['width'], info['height'], info['depth']),
                "cube_info": division,
                "preserves_shape": True,
                "has_subdivided_texture": current_texture != texture and current_texture is not None,
                "element_rotation": info['rotation'],
                "uses_element_rotation": info['rotation'] != [0, 0, 0]
            }
            
            heads.append(head)
        
        total_volume = sum(d['size'][0] * d['size'][1] * d['size'][2] for d in cube_divisions)
        original_volume = info['width'] * info['height'] * info['depth']
        
        print(f"### Verification: original volume={original_volume:.1f}, total volume={total_volume:.1f} ###")
        print(f"### {len(heads)} cubes generated with subdivided textures ###\n")
        
        return heads


TextureAwareCubeConversionStrategy = SmartCubeConversionStrategy
CubeConversionStrategy = SmartCubeConversionStrategy