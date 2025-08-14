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
    
    def _face_span_units(self, face_name: str, width: float, height: float, depth: float) -> Tuple[float, float]:
        if face_name == "north" or face_name == "south":
            return (width, height)
        if face_name == "east" or face_name == "west":
            return (depth, height)
        if face_name == "up" or face_name == "down":
            return (width, depth)
        return (1.0, 1.0)

    def _axis_density_hint(self, element: Dict[str, Any], all_textures) -> Dict[str, float]:
        """
        Return per-axis desired units-per-8px, derived from the largest pixel density seen on faces
        touching that axis. Example: if a north face uses 32px over 16 units in X => 2 px/unit,
        so a good step is ~ 8/2 = 4 units per head in X.
        """
        if not all_textures:
            return {}

        faces = element.get("faces", {})
        hints = {"x": None, "y": None, "z": None}

        def upd(axis, step):
            if step <= 0: return
            if hints[axis] is None or step < hints[axis]:
                hints[axis] = step

        for fname, fdata in faces.items():
            tid = fdata.get("texture")
            if tid is None: continue
            try:
                tid = int(tid)
            except Exception:
                continue
            tex = all_textures.get(tid)
            if tex is None: continue

            u1, v1, u2, v2 = fdata.get("uv", [0, 0, tex.width, tex.height])
            px_u = max(1, abs(int(u2 - u1)))
            px_v = max(1, abs(int(v2 - v1)))

            w, h, d = element.get("to", [16,16,16])
            fx, fy, fz = element.get("from", [0,0,0])
            width  = abs(w - fx); height = abs(h - fy); depth = abs(d - fz)

            span_u, span_v = self._face_span_units(fname, width, height, depth)
            ppu_u = px_u / max(span_u, 1e-6)
            ppu_v = px_v / max(span_v, 1e-6)

            step_u = max(1.0, 8.0 / max(ppu_u, 1e-6))
            step_v = max(1.0, 8.0 / max(ppu_v, 1e-6))

            if fname in ("north","south"):
                upd("x", step_u); upd("y", step_v)
            elif fname in ("east","west"):
                upd("x", step_u); upd("y", step_v)
            elif fname in ("up","down"):
                upd("x", step_u); upd("z", step_v)

        return {k:v for k,v in hints.items() if v is not None}

    def _refine_divisions(self, total: float, base_divs: List[float], step_hint: Optional[float]) -> List[float]:
        """
        Take existing divisions on one axis and, if we have a step hint (units per ~8px),
        split those chunks into near-multiples of that step to follow stretched UVs.
        Also coalesce into the hinted step if the total is close to an integer multiple.
        """
        if step_hint is None or step_hint <= 0:
            return base_divs

        cand = max(1.0, round(step_hint))

        m = max(1, round(total / cand))
        if abs(total - m * cand) < 0.15:
            return [cand] * m

        out = []
        for seg in base_divs:
            remaining = seg
            while remaining > 1e-6:
                step = min(cand, remaining)
                out.append(step)
                remaining -= step

        if abs(sum(out) - sum(base_divs)) > 1e-6:
            out[-1] += (sum(base_divs) - sum(out))
        return out


    
    def calculate_optimal_3d_decomposition(self, width: float, height: float, depth: float,
                                       element: Dict[str, Any], source_texture_size: Tuple[int, int] = None,
                                       all_textures: Optional[Dict[int, Any]] = None) -> List[Dict[str, Any]]:
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
        
        x_divs = self._get_divisions_from_analysis(x_analysis, width)
        y_divs = self._get_divisions_from_analysis(y_analysis, height)
        z_divs = self._get_divisions_from_analysis(z_analysis, depth)

        hints = self._axis_density_hint(element, all_textures)
        x_divs = self._refine_divisions(width,  x_divs, hints.get("x"))
        y_divs = self._refine_divisions(height, y_divs, hints.get("y"))
        z_divs = self._refine_divisions(depth,  z_divs, hints.get("z"))
        
        cubes = []
        x_pos = 0.0
        for dx in x_divs:
            y_pos = 0.0
            for dy in y_divs:
                z_pos = 0.0
                for dz in z_divs:
                    cubes.append({
                        "position": (x_pos, y_pos, z_pos),
                        "size": (dx, dy, dz),
                        "cube_size": min(dx, dy, dz),
                        "is_perfect_cube": (dx == dy == dz),
                        "texture_resolution": min(dx, dy, dz),
                        "requires_texture": True,
                        "source_element": element,
                    })
                    z_pos += dz
                y_pos += dy
            x_pos += dx

        print(f"Generating {len(cubes)} cubes (UV-aware)")
        return cubes

    
    def _handle_flat_surface(self, width: float, height: float, depth: float,
                         flat_dimensions: List[str], element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Subdivide a flat element into a grid along the two non-flat axes.
        Keep the flat axis at self.flat_thickness for BDEngine, so textures don't stretch."""
        cubes: List[Dict[str, Any]] = []

        if depth == 0:
            thick = self.flat_thickness
            x_analysis = self.analyze_dimension(width)
            y_analysis = self.analyze_dimension(height)
            x_divs = self._get_divisions_from_analysis(x_analysis, width)
            y_divs = self._get_divisions_from_analysis(y_analysis, height)

            x_pos = 0.0
            for x_size in x_divs:
                y_pos = 0.0
                for y_size in y_divs:
                    cubes.append({
                        "position": (x_pos, y_pos, 0.0),
                        "size": (x_size, y_size, thick),
                        "cube_size": min(x_size, y_size, thick),
                        "is_perfect_cube": (x_size == y_size == thick),
                        "texture_resolution": min(x_size, y_size),
                        "requires_texture": True,
                        "source_element": element,
                        "is_flat_surface": True,
                        "flat_dimensions": flat_dimensions,
                        "original_size": (width, height, depth),
                    })
                    y_pos += y_size
                x_pos += x_size

        elif width == 0:
            thick = self.flat_thickness
            y_analysis = self.analyze_dimension(height)
            z_analysis = self.analyze_dimension(depth)
            y_divs = self._get_divisions_from_analysis(y_analysis, height)
            z_divs = self._get_divisions_from_analysis(z_analysis, depth)

            y_pos = 0.0
            for y_size in y_divs:
                z_pos = 0.0
                for z_size in z_divs:
                    cubes.append({
                        "position": (0.0, y_pos, z_pos),
                        "size": (thick, y_size, z_size),
                        "cube_size": min(thick, y_size, z_size),
                        "is_perfect_cube": (thick == y_size == z_size),
                        "texture_resolution": min(y_size, z_size),
                        "requires_texture": True,
                        "source_element": element,
                        "is_flat_surface": True,
                        "flat_dimensions": flat_dimensions,
                        "original_size": (width, height, depth),
                    })
                    z_pos += z_size
                y_pos += y_size

        elif height == 0:
            thick = self.flat_thickness
            x_analysis = self.analyze_dimension(width)
            z_analysis = self.analyze_dimension(depth)
            x_divs = self._get_divisions_from_analysis(x_analysis, width)
            z_divs = self._get_divisions_from_analysis(z_analysis, depth)

            x_pos = 0.0
            for x_size in x_divs:
                z_pos = 0.0
                for z_size in z_divs:
                    cubes.append({
                        "position": (x_pos, 0.0, z_pos),
                        "size": (x_size, thick, z_size),
                        "cube_size": min(x_size, thick, z_size),
                        "is_perfect_cube": (x_size == thick == z_size),
                        "texture_resolution": min(x_size, z_size),
                        "requires_texture": True,
                        "source_element": element,
                        "is_flat_surface": True,
                        "flat_dimensions": flat_dimensions,
                        "original_size": (width, height, depth),
                    })
                    z_pos += z_size
                x_pos += x_size

        return cubes
    
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