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
import io
from math_utils import MathUtils
import numpy as np

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

        self.strategy.set_converter(self)
        
        print(f"Conversion mode set to: {mode} (with multiple texture manager)")
    
    def convert_file(self, bbmodel_file: str, output_file: str = None, texture_file: str = None) -> str:
        """Converts BBModel file to BDEngine format"""
        try:
            with open(bbmodel_file, 'r', encoding='utf-8') as f:
                bbmodel_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"BBModel file not found: {bbmodel_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {bbmodel_file}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading {bbmodel_file}: {e}")
        
        if texture_file and os.path.exists(texture_file):
            pass
        
        try:
            all_textures = self.texture_manager.extract_all_textures(bbmodel_data)
        except Exception as e:
            print(f"Texture extraction failed: {e}")
            all_textures = {}
        
        try:
            bdengine_structure = self._create_bdengine_structure(bbmodel_data)
        except Exception as e:
            raise RuntimeError(f"Failed to create base structure: {e}")
        
        try:
            model_center = CoordinateConverter.calculate_model_center(bbmodel_data.get("elements", []))
        except Exception as e:
            raise RuntimeError(f"Failed to calculate model center: {e}")
            
        print(f"Model center: {model_center}")
        
        if not all_textures:
            print("Warning: no textures extracted (will use default head texture)")
        
        total_heads = 0
        total_groups = 0
        elements = bbmodel_data.get("elements", [])
        
        valid_elements = []
        for element in elements:
            if element.get("type") == "locator":
                continue
            valid_elements.append(element)
        
        print(f"\n### Converting {len(valid_elements)} elements to BDEngine heads (skipped {len(elements) - len(valid_elements)} locators) ###")
        
        for i, element in enumerate(valid_elements):
            print(f"\n[{i+1}/{len(valid_elements)}] Element: {element.get('name','(unnamed)')}")

            produced_nodes = self._convert_element_with_textures(
                element,
                model_center,
                all_textures
            )
            if not produced_nodes:
                continue
            
            parent_group = self._find_parent_group(element.get("uuid", ""))
            target_children = parent_group["children"] if parent_group else bdengine_structure["children"]
            target_children.extend(produced_nodes)
            
            for node in produced_nodes:
                if node.get("isCollection") and node.get("_grouped_subdivision"):
                    total_groups += 1

                    child_heads = sum(1 for c in node.get("children", []) if c.get("isItemDisplay"))
                    total_heads += child_heads
                elif node.get("isItemDisplay"):
                    total_heads += 1
        
        print(f"\n### Conversion successful: {len(valid_elements)} elements → {total_heads} heads"
              f"{' in ' + str(total_groups) + ' groups' if total_groups else ''} ###")
        
        output_file = self._save_bdengine_file(bdengine_structure, bbmodel_file, output_file)
        
        return output_file
    
    def _accumulate_parent_matrix(self, element_uuid: str):
        """
        Compose the Blockbench parent chain (root → leaf) for an element.
        Each group contributes T(O) · R · T(-O), with O=group origin, R=group rotation.
        Returns a flattened 4*4 row-major list. Never raises on missing data.
        """
        if (
            not element_uuid
            or not hasattr(self, "group_info")
            or not hasattr(self, "element_parent")
            or self.group_info is None
            or self.element_parent is None
        ):
            return np.eye(4).reshape(-1).tolist()

        chain = []
        visited = set()
        g = self.element_parent.get(element_uuid)
        depth = 0
        while g and g not in visited and depth < 512:
            chain.append(g)
            visited.add(g)
            parent = self.group_info.get(g, {}).get("parent")
            g = parent
            depth += 1

        M = np.eye(4)
        for u in reversed(chain):
            info = self.group_info.get(u)
            if not info:
                print(f"⚠️ Missing group in group_info for UUID {u}; skipping in parent chain.")
                continue

            origin   = np.array(info.get("origin")   or [0.0, 0.0, 0.0], dtype=float)
            rotation = np.array(
                MathUtils.create_rotation_matrix(info.get("rotation") or [0.0, 0.0, 0.0]),
                dtype=float
            ).reshape(4, 4)

            T_to   = np.eye(4); T_to[:3, 3] = origin
            T_from = np.eye(4); T_from[:3, 3] = -origin

            M = M @ T_to @ rotation @ T_from

        return M.reshape(-1).tolist()
        
    def _create_bdengine_structure(self, bbmodel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates base BDEngine structure with nested groups"""
        structure = self.config.BDENGINE_BASE_STRUCTURE.copy()
        structure["name"] = bbmodel_data.get("name", "Converted Model")

        self.group_mapping = {}
        self.group_info = {}
        self.element_parent = {}

        outliner = bbmodel_data.get("outliner", [])
        if outliner:
            structure["children"] = self._create_group_hierarchy(outliner)
        return structure

    def _create_group_hierarchy(self, groups):
        if not hasattr(self, "group_mapping"):
            self.group_mapping = {}
        if not hasattr(self, "group_info"):
            self.group_info = {}
        if not hasattr(self, "element_parent"):
            self.element_parent = {}


        result = []
        for group in groups:
            if isinstance(group, str):
                continue

            g_uuid   = group.get("uuid")
            g_origin = group.get("origin", [0,0,0])
            g_rot    = group.get("rotation", [0,0,0])

            group_struct = {
                "isCollection": True, "isBackCollection": False,
                "name": group.get("name","Group"), "nbt": "",
                "transforms": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1],
                "children": [],
                "defaultTransform": {"position":[0,0,0],"rotation":{"x":0,"y":0,"z":0},"scale":[1,1,1]},
                "uuid": g_uuid
            }

            if g_uuid:
                self.group_info[g_uuid] = {"origin": g_origin, "rotation": g_rot, "parent": None}
                self.group_mapping[g_uuid] = group_struct

            for child in group.get("children", []):
                if isinstance(child, dict):
                    if child.get("type") == "locator":
                        continue
                    nested = self._create_group_hierarchy([child])
                    group_struct["children"].extend(nested)
                    c_uuid = child.get("uuid")
                    if c_uuid in self.group_info:
                        self.group_info[c_uuid]["parent"] = g_uuid
                else:
                    elem_uuid = child
                    if g_uuid:
                        self.element_parent[elem_uuid] = g_uuid
                    self.group_mapping[elem_uuid] = group_struct

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

    def _convert_element_with_textures(
        self,
        element: Dict[str, Any],
        model_center: List[float],
        all_textures: Dict[int, Image.Image],
    ) -> List[Dict[str, Any]]:
        """Convert element with proper texture handling.
        - If any face UV contains transparent pixels, emulate transparency by emitting
            thin flat heads only over opaque regions (no UV stretch).
        - Otherwise, use the normal conversion strategy.
        """

        texture_ids = self.texture_manager.get_element_texture_ids(element)
        print(f" Texture use: {texture_ids}")

        element_texture = None
        if texture_ids and all_textures:
            element_texture = self.texture_manager.convert_element_texture_to_head(element, all_textures)
            if element_texture:
                print(f"  ✅ Texture generated for element: {element_texture}")
            else:
                print(f"  ⚠️ Error generating texture for element: {element.get('name', 'unknown')}")
                
        faces = element.get("faces", {})
        transparent_faces = []
        for face_name, face in faces.items():
            tid = face.get("texture")
            if tid is None:
                continue
            try:
                tid = int(tid)
            except Exception:
                continue
            tex = all_textures.get(tid)
            if tex is None or tex.mode != "RGBA":
                continue

            u1, v1, u2, v2 = face.get("uv", [0, 0, tex.width, tex.height])
            U1, V1 = int(min(u1, u2)), int(min(v1, v2))
            U2, V2 = int(max(u1, u2)), int(max(v1, v2))
            sub = tex.crop((U1, V1, U2, V2))
            if sub.mode != "RGBA":
                sub = sub.convert("RGBA")

            alpha_band = sub.split()[3]
            extrema = alpha_band.getextrema()
            if extrema is None:
                a_min, a_max = 255, 255
            else:
                a_min, a_max = extrema


            if a_min < 255:
                transparent_faces.append((face_name, face, tex))

        if transparent_faces:
            print("  ↳ Transparent faces detected; emitting flat heads per opaque region")

            from_pos = element.get("from", [0, 0, 0])
            to_pos   = element.get("to",   [16, 16, 16])
            total_size = (
                to_pos[0] - from_pos[0],
                to_pos[1] - from_pos[1],
                to_pos[2] - from_pos[2],
            )
            bottom_corner = (
                min(from_pos[0], to_pos[0]),
                min(from_pos[1], to_pos[1]),
                min(from_pos[2], to_pos[2]),
            )
            rotation = element.get("rotation", [0, 0, 0])
            origin   = element.get("origin", from_pos)

            from texture_subdivider import TextureSubdivider
            from head_factory import HeadFactory
            subdv = TextureSubdivider()
            hf = HeadFactory()

            heads: List[Dict[str, Any]] = []
            ALPHA_THRESHOLD = 8
            MIN_RECT_PX     = 1

            for face_name, face, tex in transparent_faces:
                uv = face.get("uv", [0, 0, tex.width, tex.height])
                rects = subdv._opaque_rects_from_uv(
                    tex, uv, alpha_threshold=ALPHA_THRESHOLD, min_side=MIN_RECT_PX
                )
                print(f"    {face_name}: {len(rects)} opaque rects")

                for r in rects:
                    res = subdv._subcube_from_uv_rect_on_face(
                        face_name, r, uv, total_size, flat_thickness=0.011
                    )

                    if not res:
                        continue

                    cube_pos, cube_size = res

                    face_data = dict(face)
                    face_tex = subdv._extract_face_texture(
                        tex, face_data, cube_pos, cube_size, face_name, total_size
                    )
                    if face_tex is None:
                        continue

                    face_tex = face_tex.resize((8, 8), Image.NEAREST)
                    head_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                    region = subdv.head_face_mapping[face_name]["region"]
                    head_img.paste(face_tex, region)

                    buf = io.BytesIO(); head_img.save(buf, format="PNG")
                    tex_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

                    head = hf.create_subdivided_head_with_element_rotation(
                        cube_pos, cube_size,
                        element_bottom_corner=bottom_corner,
                        element_size=total_size,
                        element_rotation=rotation,
                        element_origin=origin,
                        model_center=model_center,
                        texture=tex_data
                    )
                    heads.append(head)

            return heads

        if isinstance(self.strategy, SmartCubeConversionStrategy):
            return self.strategy.convert_element(
                element, model_center, element_texture, None, None, all_textures
            )
        else:
            return self.strategy.convert_element(element, model_center, element_texture)

