"""Optimiseur intelligent qui préserve la forme tout en gardant des pixels carrés"""

from typing import List, Tuple, Dict, Any, Optional
import math
from config import Config

class SmartCubeOptimizer:
    """Optimiseur qui décompose intelligemment en préservant la forme originale"""
    
    def __init__(self):
        self.config = Config()
        # Tailles de cubes disponibles (en ordre décroissant)
        self.available_cube_sizes = [16, 8, 4, 2, 1]
        # Facteurs d'étirement acceptables (pour garder des pixels carrés)
        self.acceptable_stretch_factors = [1, 2, 4, 8, 16]
        # Épaisseur minimale pour les surfaces plates dans BDEngine
        self.flat_thickness = 0.011
    
    def analyze_dimension(self, dimension: float) -> Dict[str, Any]:
        """Analyse une dimension pour déterminer la meilleure décomposition"""
        
        # NOUVEAU: Gérer les dimensions plates (= 0)
        if dimension == 0:
            return {
                'method': 'flat_surface',
                'original_size': 0,
                'bdengine_size': self.flat_thickness,
                'is_flat': True
            }
        
        # Essayer d'abord une décomposition exacte avec des cubes
        exact_decomposition = self._find_exact_cube_decomposition(dimension)
        
        if exact_decomposition['is_exact']:
            return {
                'method': 'exact_cubes',
                'decomposition': exact_decomposition['cubes'],
                'total_size': dimension,
                'stretch_factor': 1,
                'is_flat': False
            }
        
        # Si pas possible, essayer un étirement contrôlé
        stretch_decomposition = self._find_controlled_stretch_decomposition(dimension)
        stretch_decomposition['is_flat'] = False
        
        return stretch_decomposition
    
    def calculate_optimal_3d_decomposition(self, width: float, height: float, depth: float, 
                                         element: Dict[str, Any], source_texture_size: Tuple[int, int] = None) -> List[Dict[str, Any]]:
        """Calcule la décomposition 3D optimale avec support des surfaces plates"""
        
        print(f"\n=== Décomposition intelligente pour {width}x{height}x{depth} ===")
        
        # NOUVEAU: Détecter les surfaces plates
        flat_dimensions = []
        if width == 0:
            flat_dimensions.append('width')
        if height == 0:
            flat_dimensions.append('height')
        if depth == 0:
            flat_dimensions.append('depth')
        
        if flat_dimensions:
            print(f"🔷 Surface plate détectée: dimensions plates = {flat_dimensions}")
            return self._handle_flat_surface(width, height, depth, flat_dimensions, element)
        
        # Analyser chaque dimension normalement
        x_analysis = self.analyze_dimension(width)
        y_analysis = self.analyze_dimension(height)
        z_analysis = self.analyze_dimension(depth)
        
        print(f"Analyse X ({width}): {x_analysis}")
        print(f"Analyse Y ({height}): {y_analysis}")
        print(f"Analyse Z ({depth}): {z_analysis}")
        
        # Générer les cubes selon les analyses
        cubes = self._generate_cubes_from_analysis(x_analysis, y_analysis, z_analysis, element)
        
        print(f"Génération de {len(cubes)} cubes")
        
        return cubes
    
    def _handle_flat_surface(self, width: float, height: float, depth: float, 
                           flat_dimensions: List[str], element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gère les surfaces plates en convertissant les dimensions 0 en 0.011"""
        
        # Convertir les dimensions plates
        converted_width = self.flat_thickness if width == 0 else width
        converted_height = self.flat_thickness if height == 0 else height  
        converted_depth = self.flat_thickness if depth == 0 else depth
        
        print(f"🔷 Conversion surface plate: {width}x{height}x{depth} → {converted_width}x{converted_height}x{converted_depth}")
        
        # Analyser les dimensions non-plates pour la subdivision
        non_flat_dimensions = []
        if width > 0:
            non_flat_dimensions.append(('width', width))
        if height > 0:
            non_flat_dimensions.append(('height', height))
        if depth > 0:
            non_flat_dimensions.append(('depth', depth))
        
        if len(non_flat_dimensions) == 0:
            # Point dégénéré - créer un seul petit cube
            print("🔷 Point dégénéré - création d'un cube minimal")
            return [{
                "position": (0, 0, 0),
                "size": (self.flat_thickness, self.flat_thickness, self.flat_thickness),
                "is_perfect_cube": True,
                "is_flat_surface": True,
                "flat_dimensions": flat_dimensions,
                "original_size": (width, height, depth),
                "source_element": element
            }]
        
        elif len(non_flat_dimensions) == 1:
            # Ligne - subdivision selon la seule dimension non-plate
            dim_name, dim_value = non_flat_dimensions[0]
            print(f"🔷 Ligne détectée - subdivision selon {dim_name} ({dim_value})")
            
            # Analyser la dimension non-plate
            dim_analysis = self.analyze_dimension(dim_value)
            divisions = self._get_divisions_from_analysis(dim_analysis, dim_value)
            
            cubes = []
            position = 0
            for division_size in divisions:
                if dim_name == 'width':
                    cube_size = (division_size, converted_height, converted_depth)
                    cube_pos = (position, 0, 0)
                elif dim_name == 'height':
                    cube_size = (converted_width, division_size, converted_depth)
                    cube_pos = (0, position, 0)
                else:  # depth
                    cube_size = (converted_width, converted_height, division_size)
                    cube_pos = (0, 0, position)
                
                cubes.append({
                    "position": cube_pos,
                    "size": cube_size,
                    "is_perfect_cube": False,
                    "is_flat_surface": True,
                    "flat_dimensions": flat_dimensions,
                    "original_size": (width, height, depth),
                    "source_element": element
                })
                
                position += division_size
            
            return cubes
        
        else:
            # Surface 2D - subdivision selon les deux dimensions non-plates
            print(f"🔷 Surface 2D détectée - subdivision 2D")
            
            # Identifier les dimensions non-plates
            dim1_name, dim1_value = non_flat_dimensions[0]
            dim2_name, dim2_value = non_flat_dimensions[1]
            
            # Analyser les deux dimensions
            dim1_analysis = self.analyze_dimension(dim1_value)
            dim2_analysis = self.analyze_dimension(dim2_value)
            
            dim1_divisions = self._get_divisions_from_analysis(dim1_analysis, dim1_value)
            dim2_divisions = self._get_divisions_from_analysis(dim2_analysis, dim2_value)
            
            print(f"🔷 Divisions {dim1_name}: {dim1_divisions}")
            print(f"🔷 Divisions {dim2_name}: {dim2_divisions}")
            
            # Générer la grille 2D de cubes
            cubes = []
            
            pos1 = 0
            for div1 in dim1_divisions:
                pos2 = 0
                for div2 in dim2_divisions:
                    # Construire la position et taille selon les dimensions
                    if 'width' in flat_dimensions:
                        # Width est plat
                        if dim1_name == 'height':
                            cube_pos = (0, pos1, pos2)
                            cube_size = (converted_width, div1, div2)
                        else:  # dim1_name == 'depth'
                            cube_pos = (0, pos2, pos1)
                            cube_size = (converted_width, div2, div1)
                    elif 'height' in flat_dimensions:
                        # Height est plat
                        if dim1_name == 'width':
                            cube_pos = (pos1, 0, pos2)
                            cube_size = (div1, converted_height, div2)
                        else:  # dim1_name == 'depth'
                            cube_pos = (pos2, 0, pos1)
                            cube_size = (div2, converted_height, div1)
                    else:  # 'depth' in flat_dimensions
                        # Depth est plat
                        if dim1_name == 'width':
                            cube_pos = (pos1, pos2, 0)
                            cube_size = (div1, div2, converted_depth)
                        else:  # dim1_name == 'height'
                            cube_pos = (pos2, pos1, 0)
                            cube_size = (div2, div1, converted_depth)
                    
                    cubes.append({
                        "position": cube_pos,
                        "size": cube_size,
                        "is_perfect_cube": False,
                        "is_flat_surface": True,
                        "flat_dimensions": flat_dimensions,
                        "original_size": (width, height, depth),
                        "source_element": element
                    })
                    
                    pos2 += div2
                pos1 += div1
            
            return cubes
    
    def _get_divisions_from_analysis(self, analysis: Dict[str, Any], dimension: float) -> List[float]:
        """Extrait les divisions d'une analyse de dimension"""
        
        if analysis['method'] == 'exact_cubes':
            return analysis['decomposition']
        elif analysis['method'] == 'single_stretch':
            return [analysis['final_size']]
        elif analysis['method'] == 'multiple_stretch':
            return [analysis['cube_size']] * analysis['num_cubes']
        else:
            # Fallback
            return [dimension]
    
    def _find_exact_cube_decomposition(self, dimension: float) -> Dict[str, Any]:
        """Trouve une décomposition exacte avec des cubes de tailles standard"""
        
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
        """Trouve une décomposition avec étirement contrôlé pour garder des pixels carrés"""
        
        original_dim = int(dimension)
        
        # Essayer différents facteurs d'étirement
        best_solution = None
        min_waste = float('inf')
        
        for stretch_factor in self.acceptable_stretch_factors:
            for base_cube_size in self.available_cube_sizes:
                # Calculer combien de cubes de cette taille on aurait besoin
                stretched_cube_size = base_cube_size * stretch_factor
                
                if stretched_cube_size >= original_dim:
                    # Un seul cube étiré suffit
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
                
                # Essayer une combinaison de cubes étirés
                num_cubes = math.ceil(original_dim / stretched_cube_size)
                total_size = num_cubes * stretched_cube_size
                waste = total_size - original_dim
                
                if waste < min_waste and num_cubes <= 4:  # Limiter le nombre de cubes
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
            # Fallback : décomposition exacte même si elle ne couvre pas tout
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
        """Génère les cubes selon les analyses de dimensions"""
        
        cubes = []
        
        # Stratégie selon les méthodes trouvées
        if (x_analysis['method'] == 'exact_cubes' and 
            y_analysis['method'] == 'exact_cubes' and 
            z_analysis['method'] == 'exact_cubes'):
            # Cas idéal : décomposition exacte dans les 3 dimensions
            cubes = self._generate_exact_cubes(x_analysis, y_analysis, z_analysis, element)
            
        elif any(analysis['method'].startswith('single_stretch') or analysis['method'].startswith('multiple_stretch') 
                for analysis in [x_analysis, y_analysis, z_analysis]):
            # Cas avec étirement contrôlé
            cubes = self._generate_stretched_cubes(x_analysis, y_analysis, z_analysis, element)
            
        else:
            # Cas mixte ou fallback
            cubes = self._generate_mixed_cubes(x_analysis, y_analysis, z_analysis, element)
        
        return cubes
    
    def _generate_exact_cubes(self, x_analysis: Dict, y_analysis: Dict, z_analysis: Dict, 
                            element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Génère des cubes avec décomposition exacte"""
        
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
                    # Utiliser la plus petite dimension pour garder des cubes ou des formes cohérentes
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
        """Génère des cubes avec étirement contrôlé"""
        
        cubes = []
        
        # Déterminer les dimensions finales avec étirement
        final_x = x_analysis.get('final_size', x_analysis.get('total_size', 0))
        final_y = y_analysis.get('final_size', y_analysis.get('total_size', 0))
        final_z = z_analysis.get('final_size', z_analysis.get('total_size', 0))
        
        # Pour l'instant, créer un seul cube étiré de manière contrôlée
        # TODO: Implémenter la logique de multiple cubes étirés
        
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
        """Génère des cubes avec approche mixte"""
        
        # Pour l'instant, utiliser une approche simplifiée
        # TODO: Implémenter une logique plus sophistiquée
        
        return self._generate_exact_cubes(x_analysis, y_analysis, z_analysis, element)