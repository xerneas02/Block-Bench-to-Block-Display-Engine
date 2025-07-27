"""Optimised for 3D cube decomposition with intelligent handling of flat surfaces and controlled stretching."""

from typing import List, Tuple, Dict, Any, Optional
import math
from config import Config

class SmartCubeOptimizer:
    """Optimised cube decomposition with intelligent handling of flat surfaces and controlled stretching."""
    
    def __init__(self):
        self.config = Config()
        self.available_cube_sizes = [16, 8, 4, 2, 1]
        self.acceptable_stretch_factors = [1, 2, 4, 8, 16]
        self.flat_thickness = 0.011
    
    def analyze_dimension(self, dimension: float) -> Dict[str, Any]:
        """Analyze a dimension and return decomposition strategy"""
        
        if dimension == 0:
            return {
                'method': 'flat_surface',
                'original_size': 0,
                'bdengine_size': self.flat_thickness,
                'is_flat': True
            }
        
        exact_decomposition = self._find_exact_cube_decomposition(dimension)
        
        if exact_decomposition['is_exact']:
            return {
                'method': 'exact_cubes',
                'decomposition': exact_decomposition['cubes'],
                'total_size': dimension,
                'stretch_factor': 1,
                'is_flat': False
            }
        
        stretch_decomposition = self._find_controlled_stretch_decomposition(dimension)
        stretch_decomposition['is_flat'] = False
        
        return stretch_decomposition
    
    def calculate_optimal_3d_decomposition(self, width: float, height: float, depth: float, 
                                         element: Dict[str, Any], source_texture_size: Tuple[int, int] = None) -> List[Dict[str, Any]]:
        """Compute the optimal 3D decomposition of a cube with intelligent handling of flat surfaces and controlled stretching."""
        
        print(f"\n=== Smart decomposition for {width}x{height}x{depth} ===")
        
        flat_dimensions = []
        if width == 0:
            flat_dimensions.append('width')
        if height == 0:
            flat_dimensions.append('height')
        if depth == 0:
            flat_dimensions.append('depth')
        
        if flat_dimensions:
            print(f"🔷 Flat surface detected: flat dimensions = {flat_dimensions}")
            return self._handle_flat_surface(width, height, depth, flat_dimensions, element)

        x_analysis = self.analyze_dimension(width)
        y_analysis = self.analyze_dimension(height)
        z_analysis = self.analyze_dimension(depth)
        
        print(f"Analysis X ({width}): {x_analysis}")
        print(f"Analysis Y ({height}): {y_analysis}")
        print(f"Analysis Z ({depth}): {z_analysis}")

        cubes = self._generate_cubes_from_analysis(x_analysis, y_analysis, z_analysis, element)
        
        print(f"Generating {len(cubes)} cubes")
        
        return cubes
    
    def _handle_flat_surface(self, width: float, height: float, depth: float, 
                           flat_dimensions: List[str], element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle flat surfaces by converting 0 dimensions to minimum thickness"""
        converted_width = self.flat_thickness if width == 0 else width
        converted_height = self.flat_thickness if height == 0 else height  
        converted_depth = self.flat_thickness if depth == 0 else depth

        return [{
            "position": (0, 0, 0),
            "size": (converted_width, converted_height, converted_depth),
            "is_perfect_cube": False,
            "is_flat_surface": True,
            "flat_dimensions": flat_dimensions,
            "original_size": (width, height, depth),
            "source_element": element,
            "requires_texture": True
        }]
    
    def _get_divisions_from_analysis(self, analysis: Dict[str, Any], dimension: float) -> List[float]:
        """Extract divisions from dimension analysis"""
        if analysis['method'] == 'flat_surface':
            return [analysis['bdengine_size']]
        elif analysis['method'] == 'exact_cubes':
            return analysis['decomposition']
        elif analysis['method'] == 'single_stretch':
            return [analysis['final_size']]
        elif analysis['method'] == 'multiple_stretch':
            return [analysis['cube_size']] * analysis['num_cubes']
        
        return [max(dimension, 1.0)] if dimension > 0 else [1.0]
    
    def _find_exact_cube_decomposition(self, dimension: float) -> Dict[str, Any]:
        """Find exact decomposition using standard cube sizes"""
        
        remaining = int(dimension)
        cubes = []
        
        for cube_size in self.available_cube_sizes:
            count = remaining // cube_size
            if count > 0:
                cubes.extend([cube_size] * count)
                remaining -= count * cube_size
        
        is_exact = (remaining == 0)
        
        return {
            'is_exact': is_exact,
            'cubes': cubes,
            'remaining': remaining
        }
    
    def _find_controlled_stretch_decomposition(self, dimension: float) -> Dict[str, Any]:
        """Find decomposition with controlled stretching to maintain square pixels"""
        
        original_dim = int(dimension)
        
        best_solution = None
        min_waste = float('inf')
        
        for stretch_factor in self.acceptable_stretch_factors:
            for base_cube_size in self.available_cube_sizes:
                stretched_cube_size = base_cube_size * stretch_factor
                
                if stretched_cube_size >= original_dim:
                    waste = stretched_cube_size - original_dim
                    if waste < min_waste:
                        best_solution = {
                            'method': 'single_stretch',
                            'base_cube_size': base_cube_size,
                            'stretch_factor': stretch_factor,
                            'final_size': stretched_cube_size,
                            'waste': waste
                        }
                        min_waste = waste
                
                num_cubes = math.ceil(original_dim / stretched_cube_size)
                total_size = num_cubes * stretched_cube_size
                waste = total_size - original_dim
                
                if waste < min_waste and num_cubes <= 4:
                    best_solution = {
                        'method': 'multiple_stretch',
                        'base_cube_size': base_cube_size,
                        'stretch_factor': stretch_factor,
                        'num_cubes': num_cubes,
                        'cube_size': stretched_cube_size,
                        'total_size': total_size,
                        'waste': waste
                    }
                    min_waste = waste
        
        if best_solution is None:
            exact = self._find_exact_cube_decomposition(dimension)
            return {
                'method': 'exact_partial',
                'decomposition': exact['cubes'],
                'total_size': sum(exact['cubes']),
                'missing': exact['remaining']
            }
        
        return best_solution
    
    def _generate_cubes_from_analysis(self, x_analysis: Dict, y_analysis: Dict, z_analysis: Dict, 
                                    element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cubes based on analysis of dimensions"""
        
        cubes = []
        
        if (x_analysis['method'] == 'exact_cubes' and 
            y_analysis['method'] == 'exact_cubes' and 
            z_analysis['method'] == 'exact_cubes'):
            
            cubes = self._generate_exact_cubes(x_analysis, y_analysis, z_analysis, element)
            
        elif any(analysis['method'].startswith('single_stretch') or analysis['method'].startswith('multiple_stretch') 
                for analysis in [x_analysis, y_analysis, z_analysis]):
            cubes = self._generate_stretched_cubes(x_analysis, y_analysis, z_analysis, element)
            
        else:
            cubes = self._generate_mixed_cubes(x_analysis, y_analysis, z_analysis, element)
        
        return cubes
    
    def _generate_exact_cubes(self, x_analysis: Dict, y_analysis: Dict, z_analysis: Dict, 
                            element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cubes with exact decomposition"""
        
        cubes = []
        x_cubes = x_analysis['decomposition']
        y_cubes = y_analysis['decomposition']
        z_cubes = z_analysis['decomposition']
        
        x_pos = 0
        for x_size in x_cubes:
            y_pos = 0
            for y_size in y_cubes:
                z_pos = 0
                for z_size in z_cubes:
                    cube_size = min(x_size, y_size, z_size)
                    
                    cubes.append({
                        "position": (x_pos, y_pos, z_pos),
                        "size": (x_size, y_size, z_size),
                        "cube_size": cube_size,
                        "is_perfect_cube": (x_size == y_size == z_size),
                        "texture_resolution": cube_size,
                        "requires_texture": True,
                        "source_element": element
                    })
                    
                    z_pos += z_size
                y_pos += y_size
            x_pos += x_size
        
        return cubes
    
    def _generate_stretched_cubes(self, x_analysis: Dict, y_analysis: Dict, z_analysis: Dict, 
                                element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cubes with controlled stretching"""
        
        cubes = []

        final_x = x_analysis.get('final_size', x_analysis.get('total_size', 0))
        final_y = y_analysis.get('final_size', y_analysis.get('total_size', 0))
        final_z = z_analysis.get('final_size', z_analysis.get('total_size', 0))
        
        base_size = min(
            x_analysis.get('base_cube_size', 8),
            y_analysis.get('base_cube_size', 8),
            z_analysis.get('base_cube_size', 8)
        )
        
        cubes.append({
            "position": (0, 0, 0),
            "size": (final_x, final_y, final_z),
            "cube_size": base_size,
            "is_perfect_cube": (final_x == final_y == final_z),
            "texture_resolution": base_size,
            "requires_texture": True,
            "source_element": element,
            "stretch_info": {
                "x_stretch": x_analysis.get('stretch_factor', 1),
                "y_stretch": y_analysis.get('stretch_factor', 1),
                "z_stretch": z_analysis.get('stretch_factor', 1)
            }
        })
        
        return cubes
    
    def _generate_mixed_cubes(self, x_analysis: Dict, y_analysis: Dict, z_analysis: Dict, 
                            element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cubes with mixed decomposition strategies"""
        
        return self._generate_exact_cubes(x_analysis, y_analysis, z_analysis, element)