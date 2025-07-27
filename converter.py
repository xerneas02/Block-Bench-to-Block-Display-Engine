"""Main BBModel to BDEngine converter"""

import json
import base64
import gzip
import inspect
from typing import Dict, Any, List, Tuple, Optional
from config import Config
from math_utils import CoordinateConverter
from conversion_strategy import StretchConversionStrategy, SmartCubeConversionStrategy
from texture_manager import MultiTextureManager
from PIL import Image
import os

class BBModelConverter:
    """Main converter"""
    
    def __init__(self, mode: str = "stretch"):
        self.config = Config()
        self.coord_converter = CoordinateConverter()
        self.texture_manager = MultiTextureManager()
        self.set_conversion_mode(mode)
    
    def set_conversion_mode(self, mode: str) -> None:
        """Sets conversion mode"""
        if mode not in self.config.CONVERSION_MODES:
            raise ValueError(f"Invalid mode. Available modes: {list(self.config.CONVERSION_MODES.keys())}")
        
        self.mode = mode
        
        if mode == "stretch":
            self.strategy = StretchConversionStrategy()
        elif mode == "cube":
            self.strategy = SmartCubeConversionStrategy()
        
        print(f"Conversion mode set to: {mode} (with multiple texture manager)")
    
    def convert_file(self, bbmodel_file: str, output_file: str = None, texture_file: str = None) -> str:
        """Converts BBModel file to BDEngine format"""
        with open(bbmodel_file, 'r', encoding='utf-8') as f:
            bbmodel_data = json.load(f)
        
        if texture_file and os.path.exists(texture_file):
            try:
                external_texture = Image.open(texture_file)
                if (external_texture.mode != 'RGBA'):
                    external_texture = external_texture.convert('RGBA')
                self.texture_manager.textures_cache[0] = external_texture
                self.texture_manager.textures_cache[1] = external_texture
                print(f"Loaded external texture: {texture_file}")
            except Exception as e:
                print(f"Error loading external texture: {e}")
        
        all_textures = self.texture_manager.extract_all_textures(bbmodel_data)
        
        bdengine_structure = self._create_bdengine_structure(bbmodel_data)
        
        model_center = self.coord_converter.calculate_model_center(
            bbmodel_data.get("elements", [])
        )
        print(f"Model center: {model_center}")
        
        if not all_textures:
            print("⚠️ No textures found in the model. Using default texture.")
        
        total_heads = 0
        elements = bbmodel_data.get("elements", [])
        
        valid_elements = []
        for element in elements:
            if element.get("type", "cube") != "locator":
                valid_elements.append(element)
            else:
                print(f"Skipping locator element: {element.get('name', 'unnamed')}")
        
        print(f"\n### Converting {len(valid_elements)} elements to BDEngine heads (skipped {len(elements) - len(valid_elements)} locators) ###")
        
        for i, element in enumerate(valid_elements):
            element_name = element.get("name", f"element_{i}")
            print(f"\n--- Element {i+1}: {element_name} ---")
            
            converted_heads = self._convert_element_with_textures(element, model_center, all_textures)
            
            if self.group_mapping:
                parent_group = self._find_parent_group(element.get("uuid"))
                if parent_group:
                    parent_group["children"].extend(converted_heads)
                else:
                    bdengine_structure["children"].extend(converted_heads)
            else:
                bdengine_structure["children"].extend(converted_heads)
            
            total_heads += len(converted_heads)

        print(f"\n### Conversion successful: {len(valid_elements)} elements → {total_heads} heads ###")
        
        output_file = self._save_bdengine_file(bdengine_structure, bbmodel_file, output_file)
        
        return output_file
    
    def _create_bdengine_structure(self, bbmodel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates base BDEngine structure with nested groups"""
        structure = self.config.BDENGINE_BASE_STRUCTURE.copy()
        structure["name"] = bbmodel_data.get("name", "Converted Model")
        
        self.group_mapping = {}
        
        outliner = bbmodel_data.get("outliner", [])
        if outliner:
            structure["children"] = self._create_group_hierarchy(outliner)
        
        return structure

    def _create_group_hierarchy(self, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recursively creates nested group structure, ignoring locators"""
        result = []
        
        for group in groups:
            if isinstance(group, str):
                continue
                
            group_struct = {
                "isCollection": True,
                "isBackCollection": False,
                "name": group.get("name", "Group"),
                "nbt": "",
                "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "children": [],
                "defaultTransform": {
                    "position": [0, 0, 0],
                    "rotation": {"x": 0, "y": 0, "z": 0},
                    "scale": [1, 1, 1]
                }
            }
            
            if "uuid" in group:
                self.group_mapping[group["uuid"]] = group_struct
            
            if "children" in group:
                for child in group["children"]:
                    if isinstance(child, dict):
                        if child.get("type") == "locator":
                            print(f"Skipping locator in group {group.get('name')}: {child.get('name', 'unnamed')}")
                            continue
                        nested_groups = self._create_group_hierarchy([child])
                        group_struct["children"].extend(nested_groups)
                    else:
                        self.group_mapping[child] = group_struct
                        
            result.append(group_struct)
            
        return result

    def _find_parent_group(self, element_uuid: str) -> Optional[Dict[str, Any]]:
        """Finds parent group for an element"""
        return self.group_mapping.get(element_uuid)

    def _save_bdengine_file(self, bdengine_structure: Dict[str, Any], 
                           bbmodel_file: str, output_file: str = None) -> str:
        """Saves BDEngine file"""
        
        result = [bdengine_structure]
        
        json_string = json.dumps(result, separators=(',', ':'))
        compressed_data = gzip.compress(json_string.encode('utf-8'))
        encoded_data = base64.b64encode(compressed_data).decode('utf-8')
        
        if output_file is None:
            import os
            base_name = os.path.splitext(os.path.basename(bbmodel_file))[0]
            output_file = f"{base_name}.bdengine"
        
        with open(output_file, 'w') as f:
            f.write(encoded_data)
        
        print(f"File saved: {output_file}")
        return output_file

    def _convert_element_with_textures(self, element: Dict[str, Any], model_center: List[float], 
                                       all_textures: Dict[int, Image.Image]) -> List[Dict[str, Any]]:
        """Convert element with proper texture handling"""
        texture_ids = self.texture_manager.get_element_texture_ids(element)
        print(f" Texture use: {texture_ids}")
        
        element_texture = None
        if texture_ids and all_textures:
            element_texture = self.texture_manager.convert_element_texture_to_head(element, all_textures)
            if element_texture:
                print(f"  ✅ Texture generated for element: {element_texture}")
            else:
                print(f"  ⚠️ Error generating texture for element: {element.get('name', 'unknown')}")
    
        if isinstance(self.strategy, SmartCubeConversionStrategy):
            return self.strategy.convert_element(
                element, model_center, element_texture, None, None, all_textures
            )
        else:
            return self.strategy.convert_element(element, model_center, element_texture)