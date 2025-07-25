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
        
        print(f"Conversion mode set to: {mode} (avec gestionnaire de textures multiples)")
    
    def convert_file(self, bbmodel_file: str, output_file: str = None) -> str:
        """Converts .bbmodel file to .bdengine with multiple texture support"""
        
        with open(bbmodel_file, 'r', encoding='utf-8') as f:
            bbmodel_data = json.load(f)
        
        bdengine_structure = self._create_bdengine_structure(bbmodel_data)
        
        model_center = self.coord_converter.calculate_model_center(
            bbmodel_data.get("elements", [])
        )
        print(f"Model center: {model_center}")
        
        all_textures = self.texture_manager.extract_all_textures(bbmodel_data)
        
        if not all_textures:
            print("⚠️ No textures found in the model. Using default texture.")
        
        total_heads = 0
        elements = bbmodel_data.get("elements", [])
        
        print(f"\n### Convertion of {len(elements)} elements to BDEngine heads ###")
        
        for i, element in enumerate(elements):
            element_name = element.get("name", f"element_{i}")
            print(f"\n--- Element {i+1}: {element_name} ---")
            
            texture_ids = self.texture_manager.get_element_texture_ids(element)
            print(f" Texture use: {texture_ids}")
            
            element_texture = None
            if texture_ids and all_textures:
                element_texture = self.texture_manager.convert_element_texture_to_head(element, all_textures)
                if element_texture:
                    print(f"  ✅ Texture generated for element: {element_texture}")
                else:
                    print(f"  ⚠️ Error generating texture for element: {element_name}")

            if isinstance(self.strategy, SmartCubeConversionStrategy):
                converted_heads = self.strategy.convert_element(
                    element, model_center, element_texture, None, None, all_textures
                )
            else:
                converted_heads = self.strategy.convert_element(element, model_center, element_texture)
            
            bdengine_structure["children"].extend(converted_heads)
            total_heads += len(converted_heads)
            
            rotation = element.get("rotation", [0, 0, 0])
            if rotation != [0, 0, 0]:
                print(f"Element '{element_name}' with rotation: {rotation}")
        
        print(f"\n### Conversion successfull : {len(elements)} elements → {total_heads} heads ###")
        
        output_file = self._save_bdengine_file(bdengine_structure, bbmodel_file, output_file)
        
        return output_file
    
    def _create_bdengine_structure(self, bbmodel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates base BDEngine structure"""
        structure = self.config.BDENGINE_BASE_STRUCTURE.copy()
        structure["name"] = bbmodel_data.get("name", "Converted Model")
        return structure
    
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