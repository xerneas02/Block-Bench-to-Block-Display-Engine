"""Gestionnaire de textures multiples pour les modèles Blockbench"""

import base64
import io
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional

class MultiTextureManager:
    """Gère les textures multiples d'un modèle Blockbench"""
    
    def __init__(self):
        self.textures_cache = {}  # Cache des textures par ID
    
    def extract_all_textures(self, bbmodel_data: Dict[str, Any]) -> Dict[int, Image.Image]:
        """Extrait toutes les textures du modèle"""
        
        textures = bbmodel_data.get("textures", [])
        extracted_textures = {}
        
        print(f"=== Extraction de {len(textures)} textures ===")
        
        for texture_data in textures:
            texture_id = texture_data.get("id")
            texture_name = texture_data.get("name", f"texture_{texture_id}")
            
            if texture_id is None:
                continue
            
            # Convertir l'ID en entier
            try:
                texture_id = int(texture_id)
            except (ValueError, TypeError):
                print(f"ID de texture invalide: {texture_id}")
                continue
            
            # Extraire l'image
            texture_image = self._extract_texture_image(texture_data)
            if texture_image:
                extracted_textures[texture_id] = texture_image
                print(f"  Texture {texture_id} ({texture_name}): {texture_image.size}")
            else:
                print(f"  Échec extraction texture {texture_id} ({texture_name})")
        
        print(f"=== {len(extracted_textures)} textures extraites avec succès ===")
        return extracted_textures
    
    def _extract_texture_image(self, texture_data: Dict[str, Any]) -> Optional[Image.Image]:
        """Extrait une image de texture depuis les données"""
        
        try:
            source = texture_data.get("source", "")
            if not source or not source.startswith("data:image"):
                return None
            
            # Décoder le base64
            header, encoded = source.split(',', 1)
            image_data = base64.b64decode(encoded)
            
            # Créer l'image PIL
            texture_image = Image.open(io.BytesIO(image_data))
            
            # Convertir en RGBA si nécessaire
            if texture_image.mode != 'RGBA':
                texture_image = texture_image.convert('RGBA')
            
            return texture_image
            
        except Exception as e:
            print(f"Erreur extraction texture: {e}")
            return None
    
    def get_element_texture_ids(self, element: Dict[str, Any]) -> List[int]:
        """Récupère les IDs de textures utilisées par un élément"""
        
        texture_ids = set()
        faces = element.get("faces", {})
        
        for face_name, face_data in faces.items():
            texture_id = face_data.get("texture")
            if texture_id is not None:
                try:
                    texture_id = int(texture_id)
                    texture_ids.add(texture_id)
                except (ValueError, TypeError):
                    pass
        
        return list(texture_ids)
    
    def create_element_texture_atlas(self, element: Dict[str, Any], 
                                   all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Crée un atlas de texture pour un élément spécifique"""
        
        # Récupérer les IDs de textures utilisées
        texture_ids = self.get_element_texture_ids(element)
        
        if not texture_ids:
            print("  Aucune texture trouvée pour cet élément")
            return None
        
        if len(texture_ids) == 1:
            # Une seule texture - utiliser directement
            texture_id = texture_ids[0]
            if texture_id in all_textures:
                print(f"  Texture unique: ID {texture_id}")
                return all_textures[texture_id]
        
        # Multiples textures - créer un atlas
        print(f"  Création atlas pour textures: {texture_ids}")
        return self._create_texture_atlas(texture_ids, all_textures, element)
    
    def _create_texture_atlas(self, texture_ids: List[int], 
                            all_textures: Dict[int, Image.Image], 
                            element: Dict[str, Any]) -> Optional[Image.Image]:
        """Crée un atlas combinant plusieurs textures selon les UVs de l'élément"""
        
        faces = element.get("faces", {})
        if not faces:
            return None
        
        # Analyser les UVs de chaque face pour déterminer l'espace nécessaire
        uv_regions = {}  # texture_id -> list of (left, top, right, bottom)
        
        for face_name, face_data in faces.items():
            texture_id = face_data.get("texture")
            if texture_id is None:
                continue
            
            try:
                texture_id = int(texture_id)
            except (ValueError, TypeError):
                continue
            
            if texture_id not in all_textures:
                continue
            
            uv = face_data.get("uv", [0, 0, 16, 16])  # Défaut Blockbench 16x16
            
            # Normaliser les UVs (s'assurer que left < right et top < bottom)
            left, top, right, bottom = uv
            if left > right:
                left, right = right, left
            if top > bottom:
                top, bottom = bottom, top
            
            if texture_id not in uv_regions:
                uv_regions[texture_id] = []
            
            uv_regions[texture_id].append((left, top, right, bottom))
        
        if not uv_regions:
            print("    Aucune région UV valide trouvée")
            return None
        
        # Calculer les dimensions nécessaires pour chaque texture
        texture_bounds = {}  # texture_id -> (min_x, min_y, max_x, max_y)
        
        for texture_id, regions in uv_regions.items():
            min_x = min(region[0] for region in regions)
            min_y = min(region[1] for region in regions)
            max_x = max(region[2] for region in regions)
            max_y = max(region[3] for region in regions)
            
            texture_bounds[texture_id] = (min_x, min_y, max_x, max_y)
            print(f"    Texture {texture_id}: UV bounds ({min_x}, {min_y}, {max_x}, {max_y})")
        
        # Déterminer la stratégie d'atlas selon le nombre de textures
        if len(texture_bounds) == 1:
            # Une seule texture - extraire seulement la région utilisée
            texture_id = list(texture_bounds.keys())[0]
            texture = all_textures[texture_id]
            min_x, min_y, max_x, max_y = texture_bounds[texture_id]
            
            # Convertir en coordonnées de pixels et valider
            pixel_left = max(0, int(min_x))
            pixel_top = max(0, int(min_y))
            pixel_right = min(texture.width, int(max_x))
            pixel_bottom = min(texture.height, int(max_y))
            
            if pixel_right > pixel_left and pixel_bottom > pixel_top:
                cropped = texture.crop((pixel_left, pixel_top, pixel_right, pixel_bottom))
                print(f"    Texture {texture_id} recadrée: {cropped.size}")
                return cropped
            else:
                print(f"    Région invalide pour texture {texture_id}, utilisation complète")
                return texture
        
        # Multiples textures - créer un atlas optimisé
        return self._create_multi_texture_atlas(texture_bounds, all_textures)
    
    def _create_multi_texture_atlas(self, texture_bounds: Dict[int, Tuple[float, float, float, float]], 
                                   all_textures: Dict[int, Image.Image]) -> Optional[Image.Image]:
        """Crée un atlas pour multiples textures avec placement optimisé"""
        
        # Extraire les régions de chaque texture
        texture_regions = {}
        max_region_width = 0
        max_region_height = 0
        
        for texture_id, (min_x, min_y, max_x, max_y) in texture_bounds.items():
            if texture_id not in all_textures:
                continue
            
            texture = all_textures[texture_id]
            
            # Convertir en coordonnées de pixels
            pixel_left = max(0, int(min_x))
            pixel_top = max(0, int(min_y))
            pixel_right = min(texture.width, int(max_x))
            pixel_bottom = min(texture.height, int(max_y))
            
            if pixel_right > pixel_left and pixel_bottom > pixel_top:
                region = texture.crop((pixel_left, pixel_top, pixel_right, pixel_bottom))
                texture_regions[texture_id] = region
                
                max_region_width = max(max_region_width, region.width)
                max_region_height = max(max_region_height, region.height)
                
                print(f"    Région texture {texture_id}: {region.size}")
        
        if not texture_regions:
            print("    Aucune région de texture valide")
            return None
        
        # Calculer la disposition de l'atlas
        num_textures = len(texture_regions)
        
        if num_textures <= 2:
            # Disposition horizontale pour 2 textures ou moins
            atlas_width = max_region_width * num_textures
            atlas_height = max_region_height
            layout = "horizontal"
        elif num_textures <= 4:
            # Disposition en grille 2x2 pour 3-4 textures
            cols = 2
            rows = (num_textures + 1) // 2
            atlas_width = max_region_width * cols
            atlas_height = max_region_height * rows
            layout = "grid"
        else:
            # Disposition en grille carrée pour 5+ textures
            side_length = int(num_textures ** 0.5) + 1
            atlas_width = max_region_width * side_length
            atlas_height = max_region_height * side_length
            layout = "square_grid"
        
        print(f"    Atlas {layout}: {atlas_width}x{atlas_height} pour {num_textures} textures")
        
        # Créer l'atlas
        atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        
        # Placer les textures selon la disposition
        texture_items = list(texture_regions.items())
        
        for i, (texture_id, region) in enumerate(texture_items):
            if layout == "horizontal":
                x = i * max_region_width
                y = 0
            elif layout == "grid":
                x = (i % 2) * max_region_width
                y = (i // 2) * max_region_height
            else:  # square_grid
                side_length = int(len(texture_items) ** 0.5) + 1
                x = (i % side_length) * max_region_width
                y = (i // side_length) * max_region_height
            
            # Redimensionner la région si nécessaire
            if region.size != (max_region_width, max_region_height):
                region = region.resize((max_region_width, max_region_height), Image.NEAREST)
            
            atlas.paste(region, (x, y))
            print(f"    Texture {texture_id} placée à ({x}, {y})")
        
        return atlas
    
    def convert_element_texture_to_head(self, element: Dict[str, Any], 
                                      all_textures: Dict[int, Image.Image]) -> Optional[str]:
        """Convertit la texture d'un élément en texture de tête"""
        
        element_texture = self.create_element_texture_atlas(element, all_textures)
        
        if not element_texture:
            return None
        
        # Utiliser le converteur existant pour créer la texture de tête
        try:
            from tool.blockbench_texture_converter import BlockbenchTextureConverter
            converter = BlockbenchTextureConverter()
            
            # Créer une texture de tête depuis l'atlas de l'élément
            head_texture = converter.create_head_texture_for_element(element_texture, element)
            
            # Convertir en base64
            buffered = io.BytesIO()
            head_texture.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"Erreur conversion texture élément: {e}")
            return None