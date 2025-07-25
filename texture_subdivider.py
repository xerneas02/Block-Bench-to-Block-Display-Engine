"""Subdivise les textures pour s'adapter aux multiples têtes"""

import base64
import json
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional
import math

class TextureSubdivider:
    """Divise les textures source pour les appliquer sur multiples têtes"""
    
    def __init__(self):
        # Format de texture de tête Minecraft : 64x64 avec zone utile 32x32
        self.head_texture_size = 64
        self.head_active_area = 32
        
        # Mapping des faces dans la texture de tête (zone 32x32)
        self.head_face_mapping = {
            "up": {"region": (8, 0, 16, 8)},       # Top (8x8)
            "down": {"region": (16, 0, 24, 8)},    # Bottom (8x8)
            "north": {"region": (8, 8, 16, 16)},   # Front (8x8)
            "south": {"region": (24, 8, 32, 16)},  # Back (8x8)
            "east": {"region": (0, 8, 8, 16)},     # Right side
            "west": {"region": (16, 8, 24, 16)}    # Left side
        }
    
    def subdivide_texture_for_cubes(self, source_texture: Image.Image, source_element: Dict[str, Any], 
                                   cube_divisions: List[Dict[str, Any]]) -> List[Optional[str]]:
        """Subdivise la texture source pour chaque cube"""
        
        print(f"\n=== Subdivision texture pour {len(cube_divisions)} cubes ===")
        
        # Analyser les UVs de l'élément source
        source_faces = source_element.get("faces", {})
        
        # Calculer les dimensions totales de l'élément original
        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Élément original: {total_width}x{total_height}x{total_depth}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nTraitement cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube(
                source_texture, source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions
            )
            
            if cube_texture:
                # Convertir en base64
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                # Sauvegarder pour debug
                debug_filename = f"debug_cube_{i+1}_texture.png"
                cube_texture.save(debug_filename)
                print(f"  Texture sauvée: {debug_filename}")
                
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube(self, source_texture: Image.Image, source_faces: Dict[str, Any], 
                                cube_division: Dict[str, Any], cube_index: int, 
                                total_element_size: Tuple[float, float, float], 
                                all_cube_divisions: List[Dict[str, Any]]) -> Optional[Image.Image]:
        """Crée une texture de tête pour un cube spécifique"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"  Position: {cube_pos}, Taille: {cube_size}")
        
        # Créer une texture de tête vide (64x64)
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        # Pour chaque face de la tête, extraire la bonne partie de la texture source
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                # Vérifier si cette face est visible pour ce cube
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_texture = self._extract_face_texture_for_cube(
                        source_texture, source_faces[face_name], cube_pos, cube_size, face_name, total_element_size
                    )
                    
                    if face_texture:
                        # Redimensionner à 8x8 pour la tête SANS mirroring
                        face_texture = face_texture.resize((8, 8), Image.NEAREST)
                        
                        # CORRECTION: Ne pas flipper la texture
                        # face_texture = face_texture.transpose(Image.FLIP_LEFT_RIGHT)  # SUPPRIMÉ
                        
                        # Placer dans la texture de tête
                        target_region = face_info["region"]
                        head_texture.paste(face_texture, target_region)
                        
                        print(f"    Face {face_name}: ✅ visible (orientation correcte)")
                    else:
                        # Erreur d'extraction -> noir
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"    Face {face_name}: ⬛ (erreur extraction)")
                else:
                    # Face cachée -> noir
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"    Face {face_name}: ⬛ (cachée)")
            else:
                # Pas de face définie -> noir
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"    Face {face_name}: ⬛ (non définie)")
        
        return head_texture
    
    def _extract_face_texture_for_cube(self, source_texture: Image.Image, face_data: Dict[str, Any], 
                                      cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                      face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extrait la texture d'une face pour un cube spécifique avec mapping proportionnel EXACT"""
        
        try:
            # Récupérer les UVs originaux de la face
            original_uv = face_data.get("uv", [0, 0, 0, 0])
            
            # Normaliser les coordonnées UV
            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"    UV originaux {face_name}: ({left}, {top}, {right}, {bottom})")
            
            # Calculer quelle partie de cette face correspond à ce cube
            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, source_texture
            )
            
            if face_region is None:
                return None  # Face pas visible pour ce cube
            
            print(f"    Région calculée: {face_region}")
            
            # Extraire cette région de la texture source
            face_texture = source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"    Erreur extraction face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calcule quelle région de la face originale correspond à ce cube avec mapping EXACT et orientation correcte"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv
        
        # Calculer les dimensions UV originales
        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":  # Face avant (X, Y) - OK
            # Inverser X et Y pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":  # Face arrière (X, Y) - CORRECTION SPÉCIALE
            # CORRECTION: Pour south, utiliser les coordonnées normales (pas d'inversion)
            # car cette face regarde dans la direction opposée
            x_ratio_start = cube_x / total_w  # Pas d'inversion pour south
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h  # Garder inversion Y
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":  # Face droite (Z, Y) - OK
            # Inverser Z et Y pour corriger la rotation 180°
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":  # Face gauche (Z, Y) - CORRECTION SPÉCIALE
            # CORRECTION: Pour west, utiliser les coordonnées normales pour Z (pas d'inversion)
            # car cette face a son orientation inversée
            z_ratio_start = cube_z / total_d  # Pas d'inversion pour west
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h  # Garder inversion Y
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":  # Face haut (X, Z) - OK
            # Inverser X et Z pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":  # Face bas (X, Z) - OK
            # Inverser X et Z pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None
        
        # Convertir en coordonnées entières et s'assurer qu'elles sont valides
        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, int(new_right))
        final_bottom = min(source_texture.height, int(new_bottom))
        
        # Vérifier que la région est valide
        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Région invalide: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Mapping final (corrigé {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Détermine si une face est visible pour un cube (pas cachée par un autre cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        
        # Calculer la position de la face selon son orientation
        if face_name == "north":  # Face avant (Z minimum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)  # Normal vers l'avant
            
        elif face_name == "south":  # Face arrière (Z maximum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)  # Normal vers l'arrière
            
        elif face_name == "west":  # Face gauche (X minimum)
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)  # Normal vers la gauche
            
        elif face_name == "east":  # Face droite (X maximum)
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)  # Normal vers la droite
            
        elif face_name == "down":  # Face bas (Y minimum)
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)  # Normal vers le bas
            
        elif face_name == "up":  # Face haut (Y maximum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0)  # Normal vers le haut
            
        else:
            return True  # Face inconnue, considérer comme visible
        
        # Vérifier si un autre cube cache cette face
        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            # Ne pas comparer avec soi-même
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            # Vérifier si l'autre cube est adjacent et cache cette face
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} cachée par cube à {other_pos}")
                return False
        
        return True  # Face visible
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Vérifie si un cube bloque une face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal
        
        # Calculer les limites du cube bloquant
        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d
        
        # Tolérance pour les faces adjacentes
        tolerance = 0.1
        
        # Vérifier si le cube bloquant est dans la direction de la normale et adjacent
        if normal_x > 0:  # Face vers +X
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:  # Face vers -X
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:  # Face vers +Y
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:  # Face vers -Y
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:  # Face vers +Z
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:  # Face vers -Z
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Crée une texture entièrement noire pour les faces cachées"""
        
        # Créer une texture de tête noire
        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))
        
        # Convertir en base64
        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def subdivide_texture_for_cubes_with_individual_textures(self, source_element: Dict[str, Any], 
                                                          cube_divisions: List[Dict[str, Any]], 
                                                          all_textures: Dict[int, Image.Image]) -> List[Optional[str]]:
        """Subdivise les textures avec gestion des textures individuelles par face"""
        
        print(f"\n=== Subdivision texture pour {len(cube_divisions)} cubes avec textures individuelles ===")
        
        # Analyser les UVs et textures de l'élément source
        source_faces = source_element.get("faces", {})
        
        # Calculer les dimensions totales de l'élément original
        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])
        
        total_width = to_pos[0] - from_pos[0]
        total_height = to_pos[1] - from_pos[1]
        total_depth = to_pos[2] - from_pos[2]
        
        print(f"Élément original: {total_width}x{total_height}x{total_depth}")
        print(f"Textures disponibles: {list(all_textures.keys())}")
        
        # Afficher les textures utilisées par chaque face
        for face_name, face_data in source_faces.items():
            texture_id = face_data.get("texture")
            uv = face_data.get("uv", [0, 0, 16, 16])
            print(f"  Face {face_name}: texture {texture_id}, UV {uv}")
        
        textures = []
        for i, cube_division in enumerate(cube_divisions):
            print(f"\nTraitement cube {i+1}:")
            
            cube_texture = self._create_texture_for_cube_with_individual_textures(
                source_faces, cube_division, i, 
                (total_width, total_height, total_depth), cube_divisions, all_textures
            )
            
            if cube_texture:
                # Convertir en base64
                buffered = io.BytesIO()
                cube_texture.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                texture_data = f"data:image/png;base64,{img_str}"
                
                print(f"  Texture générée pour cube {i+1}")
                textures.append(texture_data)
            else:
                textures.append(None)
        
        return textures
    
    def _create_texture_for_cube_with_individual_textures(self, source_faces: Dict[str, Any], 
                                                        cube_division: Dict[str, Any], cube_index: int, 
                                                        total_element_size: Tuple[float, float, float], 
                                                        all_cube_divisions: List[Dict[str, Any]],
                                                        all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Crée une texture de tête pour un cube spécifique avec textures individuelles"""
        
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        
        print(f"  Position: {cube_pos}, Taille: {cube_size}")
        
        # Créer une texture de tête vide (64x64)
        head_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))
        
        # Pour chaque face de la tête, extraire la bonne partie de la texture correspondante
        for face_name, face_info in self.head_face_mapping.items():
            if face_name in source_faces:
                # Vérifier si cette face est visible pour ce cube
                is_visible = self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions)
                
                if is_visible:
                    face_data = source_faces[face_name]
                    texture_id = face_data.get("texture")
                    
                    if texture_id is not None and int(texture_id) in all_textures:
                        # Récupérer la texture spécifique à cette face
                        face_source_texture = all_textures[int(texture_id)]
                        
                        face_texture = self._extract_face_texture_for_cube_individual(
                            face_source_texture, face_data, cube_pos, cube_size, face_name, total_element_size
                        )
                        
                        if face_texture:
                            # Redimensionner à 8x8 pour la tête
                            face_texture = face_texture.resize((8, 8), Image.NEAREST)
                            
                            # Placer dans la texture de tête
                            target_region = face_info["region"]
                            head_texture.paste(face_texture, target_region)
                            
                            print(f"    Face {face_name}: ✅ texture {texture_id}")
                        else:
                            # Erreur d'extraction -> noir
                            black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                            target_region = face_info["region"]
                            head_texture.paste(black_face, target_region)
                            print(f"    Face {face_name}: ⬛ (erreur extraction texture {texture_id})")
                    else:
                        # Texture non trouvée -> noir
                        black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                        target_region = face_info["region"]
                        head_texture.paste(black_face, target_region)
                        print(f"    Face {face_name}: ⬛ (texture {texture_id} non trouvée)")
                else:
                    # Face cachée -> noir
                    black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                    target_region = face_info["region"]
                    head_texture.paste(black_face, target_region)
                    print(f"    Face {face_name}: ⬛ (cachée)")
            else:
                # Pas de face définie -> noir
                black_face = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
                target_region = face_info["region"]
                head_texture.paste(black_face, target_region)
                print(f"    Face {face_name}: ⬛ (non définie)")
        
        return head_texture
    
    def _extract_face_texture_for_cube_individual(self, face_source_texture: Image.Image, face_data: Dict[str, Any], 
                                                cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                                face_name: str, total_element_size: Tuple[float, float, float]) -> Optional[Image.Image]:
        """Extrait la texture d'une face pour un cube spécifique avec texture individuelle"""
        
        try:
            # Récupérer les UVs originaux de la face
            original_uv = face_data.get("uv", [0, 0, face_source_texture.width, face_source_texture.height])
            
            # Normaliser les coordonnées UV
            u1, v1, u2, v2 = original_uv
            left = min(u1, u2)
            right = max(u1, u2)
            top = min(v1, v2)
            bottom = max(v1, v2)
            
            print(f"    UV originaux {face_name}: ({left}, {top}, {right}, {bottom}) sur texture {face_source_texture.size}")
            
            # Calculer quelle partie de cette face correspond à ce cube
            face_region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, face_source_texture
            )
            
            if face_region is None:
                return None  # Face pas visible pour ce cube
            
            print(f"    Région calculée: {face_region}")
            
            # Extraire cette région de la texture source
            face_texture = face_source_texture.crop(face_region)
            
            return face_texture
            
        except Exception as e:
            print(f"    Erreur extraction face {face_name}: {e}")
            return None
    
    def _calculate_face_region_for_cube_exact(self, original_face_uv: Tuple[float, float, float, float], 
                                             cube_pos: Tuple[float, float, float], cube_size: Tuple[float, float, float], 
                                             face_name: str, total_element_size: Tuple[float, float, float],
                                             source_texture: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Calcule quelle région de la face originale correspond à ce cube avec mapping EXACT et orientation correcte"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size
        
        orig_left, orig_top, orig_right, orig_bottom = original_face_uv
        
        # Calculer les dimensions UV originales
        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top
        
        print(f"      Cube pos: {cube_pos}, size: {cube_size}")
        print(f"      Total size: {total_element_size}")
        print(f"      UV original: {uv_width}x{uv_height}")
        
        if face_name == "north":  # Face avant (X, Y) - OK
            # Inverser X et Y pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "south":  # Face arrière (X, Y) - CORRECTION SPÉCIALE
            # CORRECTION: Pour south, utiliser les coordonnées normales (pas d'inversion)
            # car cette face regarde dans la direction opposée
            x_ratio_start = cube_x / total_w  # Pas d'inversion pour south
            x_ratio_end = (cube_x + cube_w) / total_w
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h  # Garder inversion Y
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "east":  # Face droite (Z, Y) - OK
            # Inverser Z et Y pour corriger la rotation 180°
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "west":  # Face gauche (Z, Y) - CORRECTION SPÉCIALE
            # CORRECTION: Pour west, utiliser les coordonnées normales pour Z (pas d'inversion)
            # car cette face a son orientation inversée
            z_ratio_start = cube_z / total_d  # Pas d'inversion pour west
            z_ratio_end = (cube_z + cube_d) / total_d
            
            y_ratio_start = (total_h - cube_y - cube_h) / total_h  # Garder inversion Y
            y_ratio_end = (total_h - cube_y) / total_h
            
            # Appliquer aux UVs
            new_left = orig_left + (z_ratio_start * uv_width)
            new_right = orig_left + (z_ratio_end * uv_width)
            new_top = orig_top + (y_ratio_start * uv_height)
            new_bottom = orig_top + (y_ratio_end * uv_height)
            
        elif face_name == "up":  # Face haut (X, Z) - OK
            # Inverser X et Z pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        elif face_name == "down":  # Face bas (X, Z) - OK
            # Inverser X et Z pour corriger la rotation 180°
            x_ratio_start = (total_w - cube_x - cube_w) / total_w
            x_ratio_end = (total_w - cube_x) / total_w
            
            z_ratio_start = (total_d - cube_z - cube_d) / total_d
            z_ratio_end = (total_d - cube_z) / total_d
            
            # Appliquer aux UVs
            new_left = orig_left + (x_ratio_start * uv_width)
            new_right = orig_left + (x_ratio_end * uv_width)
            new_top = orig_top + (z_ratio_start * uv_height)
            new_bottom = orig_top + (z_ratio_end * uv_height)
            
        else:
            return None
        
        # Convertir en coordonnées entières et s'assurer qu'elles sont valides
        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, int(new_right))
        final_bottom = min(source_texture.height, int(new_bottom))
        
        # Vérifier que la région est valide
        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Région invalide: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None
        
        print(f"      Mapping final (corrigé {face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _is_face_visible_for_cube(self, face_name: str, cube_pos: Tuple[float, float, float], 
                                 cube_size: Tuple[float, float, float], all_cubes: List[Dict[str, Any]]) -> bool:
        """Détermine si une face est visible pour un cube (pas cachée par un autre cube)"""
        
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        
        # Calculer la position de la face selon son orientation
        if face_name == "north":  # Face avant (Z minimum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z)
            face_normal = (0, 0, -1)  # Normal vers l'avant
            
        elif face_name == "south":  # Face arrière (Z maximum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h/2, cube_z + cube_d)
            face_normal = (0, 0, 1)  # Normal vers l'arrière
            
        elif face_name == "west":  # Face gauche (X minimum)
            face_center = (cube_x, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (-1, 0, 0)  # Normal vers la gauche
            
        elif face_name == "east":  # Face droite (X maximum)
            face_center = (cube_x + cube_w, cube_y + cube_h/2, cube_z + cube_d/2)
            face_normal = (1, 0, 0)  # Normal vers la droite
            
        elif face_name == "down":  # Face bas (Y minimum)
            face_center = (cube_x + cube_w/2, cube_y, cube_z + cube_d/2)
            face_normal = (0, -1, 0)  # Normal vers le bas
            
        elif face_name == "up":  # Face haut (Y maximum)
            face_center = (cube_x + cube_w/2, cube_y + cube_h, cube_z + cube_d/2)
            face_normal = (0, 1, 0)  # Normal vers le haut
            
        else:
            return True  # Face inconnue, considérer comme visible
        
        # Vérifier si un autre cube cache cette face
        for other_cube in all_cubes:
            other_pos = other_cube["position"]
            other_size = other_cube["size"]
            
            # Ne pas comparer avec soi-même
            if other_pos == cube_pos and other_size == cube_size:
                continue
            
            # Vérifier si l'autre cube est adjacent et cache cette face
            if self._cube_blocks_face(face_center, face_normal, other_pos, other_size):
                print(f"      Face {face_name} cachée par cube à {other_pos}")
                return False
        
        return True  # Face visible
    
    def _cube_blocks_face(self, face_center: Tuple[float, float, float], face_normal: Tuple[float, float, float],
                         blocking_cube_pos: Tuple[float, float, float], blocking_cube_size: Tuple[float, float, float]) -> bool:
        """Vérifie si un cube bloque une face"""
        
        block_x, block_y, block_z = blocking_cube_pos
        block_w, block_h, block_d = blocking_cube_size
        
        face_x, face_y, face_z = face_center
        normal_x, normal_y, normal_z = face_normal
        
        # Calculer les limites du cube bloquant
        block_min_x = block_x
        block_max_x = block_x + block_w
        block_min_y = block_y
        block_max_y = block_y + block_h
        block_min_z = block_z
        block_max_z = block_z + block_d
        
        # Tolérance pour les faces adjacentes
        tolerance = 0.1
        
        # Vérifier si le cube bloquant est dans la direction de la normale et adjacent
        if normal_x > 0:  # Face vers +X
            if (block_min_x <= face_x + tolerance and block_max_x > face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_x < 0:  # Face vers -X
            if (block_max_x >= face_x - tolerance and block_min_x < face_x and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y > 0:  # Face vers +Y
            if (block_min_y <= face_y + tolerance and block_max_y > face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_y < 0:  # Face vers -Y
            if (block_max_y >= face_y - tolerance and block_min_y < face_y and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_z <= face_z + tolerance and block_max_z >= face_z - tolerance):
                return True
                
        elif normal_z > 0:  # Face vers +Z
            if (block_min_z <= face_z + tolerance and block_max_z > face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
                
        elif normal_z < 0:  # Face vers -Z
            if (block_max_z >= face_z - tolerance and block_min_z < face_z and
                block_min_x <= face_x + tolerance and block_max_x >= face_x - tolerance and
                block_min_y <= face_y + tolerance and block_max_y >= face_y - tolerance):
                return True
        
        return False
    
    def create_black_texture(self) -> str:
        """Crée une texture entièrement noire pour les faces cachées"""
        
        # Créer une texture de tête noire
        black_texture = Image.new('RGBA', (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))
        
        # Convertir en base64
        buffered = io.BytesIO()
        black_texture.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"