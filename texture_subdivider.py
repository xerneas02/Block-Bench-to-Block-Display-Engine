"""Subdivide Minecraft head textures for multiple cubes with correct face mapping and orientation."""

import base64
import io
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image


class TextureSubdivider:
    """Divide textures for multiple heads with correct face mapping and orientation"""

    # ---- Debug ----
    debug = True

    def _dbg(self, msg: str):
        if getattr(self, "debug", False):
            print(msg)

    # ---- Init / layout ----
    def __init__(self):
        self.head_texture_size = 64
        self.head_active_area = 32
        # Java head layout
        self.head_face_mapping = {
            "up": {"region": (8, 0, 16, 8)},       # Top
            "down": {"region": (16, 0, 24, 8)},    # Bottom
            "north": {"region": (8, 8, 16, 16)},   # Front
            "south": {"region": (24, 8, 32, 16)},  # Back
            "east": {"region": (0, 8, 8, 16)},     # Right
            "west": {"region": (16, 8, 24, 16)},   # Left
        }

    def _opaque_rects_from_uv(
        self, tex: Image.Image, uv: List[int],
        alpha_threshold: int = 8, min_side: int = 1
    ) -> List[Tuple[int, int, int, int]]:
        """Return a list of opaque sub-rectangles (in UV coordinates) for a given texture face."""
        u1, v1, u2, v2 = uv
        umin, vmin = int(min(u1, u2)), int(min(v1, v2))
        umax, vmax = int(max(u1, u2)), int(max(v1, v2))
        sub_img = tex.crop((umin, vmin, umax, vmax))
        if sub_img.mode != "RGBA":
            return [(umin, vmin, umax, vmax)]

        alpha = sub_img.split()[3]
        opaque_rects = []
        pixels = alpha.load()
        width, height = sub_img.size

        visited = [[False] * height for _ in range(width)]

        def flood_fill(x, y):
            stack = [(x, y)]
            minx, miny, maxx, maxy = x, y, x, y
            while stack:
                cx, cy = stack.pop()
                if visited[cx][cy]:
                    continue
                visited[cx][cy] = True
                if pixels[cx, cy] >= alpha_threshold:
                    minx = min(minx, cx)
                    miny = min(miny, cy)
                    maxx = max(maxx, cx)
                    maxy = max(maxy, cy)
                    for nx, ny in [(cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)]:
                        if 0 <= nx < width and 0 <= ny < height and not visited[nx][ny]:
                            stack.append((nx, ny))
            return minx, miny, maxx+1, maxy+1

        for x in range(width):
            for y in range(height):
                if not visited[x][y] and pixels[x, y] >= alpha_threshold:
                    rect = flood_fill(x, y)
                    if rect[2]-rect[0] >= min_side and rect[3]-rect[1] >= min_side:
                        # Convert local rect to global UV coords
                        global_rect = (
                            umin + rect[0], vmin + rect[1],
                            umin + rect[2], vmin + rect[3]
                        )
                        opaque_rects.append(global_rect)
        return opaque_rects

    # ---- Public APIs ----
    def subdivide_texture_for_cubes(
        self,
        source_texture: Image.Image,
        source_element: Dict[str, Any],
        cube_divisions: List[Dict[str, Any]],
    ) -> List[Optional[str]]:
        """Single texture for the element; split among cubes."""
        print(f"\n### Subdivision for texture {len(cube_divisions)} cubes ###")

        source_faces = source_element.get("faces", {})
        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])

        total_w = to_pos[0] - from_pos[0]
        total_h = to_pos[1] - from_pos[1]
        total_d = to_pos[2] - from_pos[2]
        total_element_size = (total_w, total_h, total_d)

        print(f"Original element: {total_w}x{total_h}x{total_d}")

        out: List[Optional[str]] = []
        for i, cube_div in enumerate(cube_divisions):
            print(f"\nComputing cube {i+1}:")
            tex = self._create_texture_for_cube(
                source_texture,
                source_faces,
                cube_div,
                i,
                total_element_size,
                cube_divisions,
            )
            if tex:
                buf = io.BytesIO()
                tex.save(buf, format="PNG")
                out.append(f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}")
            else:
                out.append(None)
        return out
    
    def _subcube_from_uv_rect_on_face(
        self,
        face_name: str,
        uv_rect: Tuple[int, int, int, int],
        face_uv: Tuple[float, float, float, float],
        total_element_size: Tuple[float, float, float],
        flat_thickness: float = 0.011,
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        total_w, total_h, total_d = total_element_size
        u1, v1, u2, v2 = face_uv
        U1, V1 = min(u1, u2), min(v1, v2)
        U2, V2 = max(u1, u2), max(v1, v2)

        ru1, rv1, ru2, rv2 = uv_rect  # <-- tuple unpack
        nx1 = (ru1 - U1) / (U2 - U1 + 1e-9)
        ny1 = (rv1 - V1) / (V2 - V1 + 1e-9)
        nx2 = (ru2 - U1) / (U2 - U1 + 1e-9)
        ny2 = (rv2 - V1) / (V2 - V1 + 1e-9)

        if face_name == "north":
            x0, x1 = (1-nx2)*total_w, (1-nx1)*total_w
            y0, y1 = (1-ny2)*total_h, (1-ny1)*total_h
            pos  = (x0, y0, 0.0)
            size = (max(x1-x0, 1e-6), max(y1-y0, 1e-6), flat_thickness)
        elif face_name == "south":
            x0, x1 = nx1*total_w, nx2*total_w
            y0, y1 = (1-ny2)*total_h, (1-ny1)*total_h
            pos  = (x0, y0, total_d - flat_thickness)
            size = (max(x1-x0, 1e-6), max(y1-y0, 1e-6), flat_thickness)
        elif face_name == "west":
            z0, z1 = nx1*total_d, nx2*total_d
            y0, y1 = (1-ny2)*total_h, (1-ny1)*total_h
            pos  = (0.0, y0, z0)
            size = (flat_thickness, max(y1-y0, 1e-6), max(z1-z0, 1e-6))
        elif face_name == "east":
            z0, z1 = (1-nx2)*total_d, (1-nx1)*total_d
            y0, y1 = (1-ny2)*total_h, (1-ny1)*total_h
            pos  = (total_w - flat_thickness, y0, z0)
            size = (flat_thickness, max(y1-y0, 1e-6), max(z1-z0, 1e-6))
        elif face_name == "down":
            x0, x1 = (1-nx2)*total_w, (1-nx1)*total_w
            z0, z1 = (1-ny2)*total_d, (1-ny1)*total_d
            pos  = (x0, 0.0, z0)
            size = (max(x1-x0, 1e-6), flat_thickness, max(z1-z0, 1e-6))
        elif face_name == "up":
            x0, x1 = (1-nx2)*total_w, (1-nx1)*total_w
            z0, z1 = ny1*total_d, ny2*total_d
            pos  = (x0, total_h - flat_thickness, z0)
            size = (max(x1-x0, 1e-6), flat_thickness, max(z1-z0, 1e-6))
        else:
            pos, size = (0, 0, 0), (0, 0, 0)

        return pos, size


    def subdivide_texture_for_cubes_with_individual_textures(
        self,
        source_element: Dict[str, Any],
        cube_divisions: List[Dict[str, Any]],
        all_textures: Dict[int, Image.Image],
    ) -> List[Optional[str]]:
        """Each face may reference its own texture; split among cubes."""
        print(f"\n### Subdivision texture for {len(cube_divisions)} cubes with individual textures ###")

        source_faces = source_element.get("faces", {})
        from_pos = source_element.get("from", [0, 0, 0])
        to_pos = source_element.get("to", [16, 16, 16])

        total_w = to_pos[0] - from_pos[0]
        total_h = to_pos[1] - from_pos[1]
        total_d = to_pos[2] - from_pos[2]
        total_element_size = (total_w, total_h, total_d)

        print(f"Original element: {total_w}x{total_h}x{total_d}")
        print(f"Available textures: {list(all_textures.keys())}")
        for face_name, face_data in source_faces.items():
            print(f"Face {face_name}: texture {face_data.get('texture')}, UV {face_data.get('uv', [0,0,16,16])}")

        out: List[Optional[str]] = []
        for i, cube_div in enumerate(cube_divisions):
            print(f"\nProcessing cube {i+1}:")
            tex = self._create_texture_for_cube_with_individual_textures(
                source_faces,
                cube_div,
                i,
                total_element_size,
                cube_divisions,
                all_textures,
            )
            if tex:
                buf = io.BytesIO()
                tex.save(buf, format="PNG")
                out.append(f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}")
                print(f"Texture generated for cube {i+1}")
            else:
                out.append(None)
        return out

    # ---- Core creators ----
    def _create_texture_for_cube(
        self,
        source_texture: Image.Image,
        source_faces: Dict[str, Any],
        cube_division: Dict[str, Any],
        cube_index: int,
        total_element_size: Tuple[float, float, float],
        all_cube_divisions: List[Dict[str, Any]],
    ) -> Optional[Image.Image]:
        """Single source texture path."""
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        print(f"Position: {cube_pos}, Size: {cube_size} Cube")

        head = Image.new("RGBA", (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))

        for face_name, face_info in self.head_face_mapping.items():
            if face_name not in source_faces:
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (undefined)")
                continue

            if not self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions):
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (hidden)")
                continue

            # Extract and paste
            tex = self._extract_face_texture(
                source_texture, source_faces[face_name], cube_pos, cube_size, face_name, total_element_size
            )
            if tex:
                head.paste(tex.resize((8, 8), Image.NEAREST), face_info["region"])
                print(f"Face {face_name}: ✅ visible")
            else:
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (extraction error)")
        return head

    def _create_texture_for_cube_with_individual_textures(
        self,
        source_faces: Dict[str, Any],
        cube_division: Dict[str, Any],
        cube_index: int,
        total_element_size: Tuple[float, float, float],
        all_cube_divisions: List[Dict[str, Any]],
        all_textures: Dict[int, Image.Image],
    ) -> Optional[Image.Image]:
        """Per-face texture path with flat-side blending."""
        cube_pos = cube_division["position"]
        cube_size = cube_division["size"]
        print(f"Position: {cube_pos}, Size: {cube_size} Individual")

        head = Image.new("RGBA", (self.head_texture_size, self.head_texture_size), (0, 0, 0, 0))

        flat_flags = self.get_flat_faces(total_element_size)  # [N,E,S,W,U,D]
        face_order = ["north", "east", "south", "west", "up", "down"]
        print(f"Flat flags: {flat_flags} (is_flat={any(flat_flags)})")

        for face_name, face_info in self.head_face_mapping.items():
            if face_name not in source_faces:
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (not defined)")
                continue

            if not self._is_face_visible_for_cube(face_name, cube_pos, cube_size, all_cube_divisions):
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (hidden)")
                continue

            face_data = source_faces[face_name]
            texture_id = face_data.get("texture")

            # First: if flat element and this face is a thin side → blended paint
            try:
                idx = face_order.index(face_name)
            except ValueError:
                idx = -1
            if idx >= 0 and any(flat_flags) and not flat_flags[idx]:
                blended = self._make_blended_side_face(face_name, source_faces, all_textures, total_element_size)
                if blended is not None:
                    head.paste(blended.resize((8, 8), Image.NEAREST), face_info["region"])
                    print(f"Face {face_name}: 🎨 blended from adjacent edges (flat element)")
                    continue  # skip normal extraction

            # Fallback: normal extraction
            if texture_id is None or int(texture_id) not in all_textures:
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (texture {texture_id} not found)")
                continue

            face_source_texture = all_textures[int(texture_id)]
            tex = self._extract_face_texture(
                face_source_texture, face_data, cube_pos, cube_size, face_name, total_element_size
            )
            if tex:
                head.paste(tex.resize((8, 8), Image.NEAREST), face_info["region"])
                print(f"Face {face_name}: ✅ texture {texture_id}")
            else:
                self._paste_black(head, face_info["region"], f"Face {face_name}: ⬛ (extraction error texture {texture_id})")
        return head

    # ---- Extraction helpers ----
    def _extract_face_texture(
        self,
        face_source_texture: Image.Image,
        face_data: Dict[str, Any],
        cube_pos: Tuple[float, float, float],
        cube_size: Tuple[float, float, float],
        face_name: str,
        total_element_size: Tuple[float, float, float],
    ) -> Optional[Image.Image]:
        """Shared extraction that crops from face_source_texture."""
        try:
            original_uv = face_data.get("uv", [0, 0, face_source_texture.width, face_source_texture.height])
            u1, v1, u2, v2 = original_uv
            left, right = min(u1, u2), max(u1, u2)
            top, bottom = min(v1, v2), max(v1, v2)

            self._dbg(f"Original UVs {face_name}: ({left}, {top}, {right}, {bottom}) on texture {face_source_texture.size}")

            region = self._calculate_face_region_for_cube_exact(
                (left, top, right, bottom), cube_pos, cube_size, face_name, total_element_size, face_source_texture
            )
            if region is None:
                return None

            self._dbg(f"Region calculated: {region}")
            return face_source_texture.crop(region)
        except Exception as e:
            print(f"Error extracting face {face_name}: {e}")
            return None

    def _safe_div(self, n: float, d: float, label: str) -> float:
        if d == 0:
            raise ZeroDivisionError(f"denominator 0 for {label}")
        return n / d

    def _calculate_face_region_for_cube_exact(
        self,
        original_face_uv: Tuple[float, float, float, float],
        cube_pos: Tuple[float, float, float],
        cube_size: Tuple[float, float, float],
        face_name: str,
        total_element_size: Tuple[float, float, float],
        source_texture: Image.Image,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Map sub-cube to sub-UV with explicit orientation and guarded divisions."""
        cube_x, cube_y, cube_z = cube_pos
        cube_w, cube_h, cube_d = cube_size
        total_w, total_h, total_d = total_element_size

        orig_left, orig_top, orig_right, orig_bottom = original_face_uv
        uv_width = orig_right - orig_left
        uv_height = orig_bottom - orig_top

        self._dbg(f"      Cube pos: {cube_pos}, size: {cube_size}")
        self._dbg(f"      Total size: {total_element_size}")
        self._dbg(f"      UV original: {uv_width}x{uv_height}")

        # Compute ratios safely
        if face_name == "north":
            x0 = self._safe_div((total_w - cube_x - cube_w), total_w, "total_w")
            x1 = self._safe_div((total_w - cube_x), total_w, "total_w")
            y0 = self._safe_div((total_h - cube_y - cube_h), total_h, "total_h")
            y1 = self._safe_div((total_h - cube_y), total_h, "total_h")

        elif face_name == "south":
            x0 = self._safe_div(cube_x, total_w, "total_w")
            x1 = self._safe_div((cube_x + cube_w), total_w, "total_w")
            y0 = self._safe_div((total_h - cube_y - cube_h), total_h, "total_h")
            y1 = self._safe_div((total_h - cube_y), total_h, "total_h")

        elif face_name == "east":
            x0 = self._safe_div((total_d - cube_z - cube_d), total_d, "total_d")
            x1 = self._safe_div((total_d - cube_z), total_d, "total_d")
            y0 = self._safe_div((total_h - cube_y - cube_h), total_h, "total_h")
            y1 = self._safe_div((total_h - cube_y), total_h, "total_h")

        elif face_name == "west":
            x0 = self._safe_div(cube_z, total_d, "total_d")
            x1 = self._safe_div((cube_z + cube_d), total_d, "total_d")
            y0 = self._safe_div((total_h - cube_y - cube_h), total_h, "total_h")
            y1 = self._safe_div((total_h - cube_y), total_h, "total_h")

        elif face_name == "up":
            x0 = self._safe_div((total_w - cube_x - cube_w), total_w, "total_w")
            x1 = self._safe_div((total_w - cube_x), total_w, "total_w")
            y0 = self._safe_div((total_d - cube_z - cube_d), total_d, "total_d")
            y1 = self._safe_div((total_d - cube_z), total_d, "total_d")

        elif face_name == "down":
            x0 = self._safe_div((total_w - cube_x - cube_w), total_w, "total_w")
            x1 = self._safe_div((total_w - cube_x), total_w, "total_w")
            y0 = self._safe_div((total_d - cube_z - cube_d), total_d, "total_d")
            y1 = self._safe_div((total_d - cube_z), total_d, "total_d")

        else:
            return None

        new_left = orig_left + (x0 * uv_width)
        new_right = orig_left + (x1 * uv_width)
        new_top = orig_top + (y0 * uv_height)
        new_bottom = orig_top + (y1 * uv_height)

        final_left = max(0, int(new_left))
        final_top = max(0, int(new_top))
        final_right = min(source_texture.width, max(final_left + 1, int(round(new_right))))
        final_bottom = min(source_texture.height, max(final_top + 1, int(round(new_bottom))))

        if final_right <= final_left or final_bottom <= final_top:
            print(f"      Invalid region: ({final_left}, {final_top}, {final_right}, {final_bottom})")
            return None

        self._dbg(f"      Final mapping ({face_name}): ({final_left}, {final_top}, {final_right}, {final_bottom})")
        return final_left, final_top, final_right, final_bottom

    def _orient_blended_canvas(self, canvas: Image.Image, face_name: str,
                           total_element_size: Tuple[float, float, float]) -> Image.Image:
        """
        Rotate/flip the 8x8 synthesized side face so it matches Minecraft head orientation.
        Only applies to thin sides of flat elements. We start with X-flat since that's your case.
        PIL .rotate() is counter-clockwise.
        """
        width, height, depth = total_element_size

        if width == 0:
            if face_name == "north":
                return canvas.rotate(180, expand=False)
            if face_name == "up":
                return canvas.rotate(270, expand=False)
            if face_name == "down":
                return canvas.rotate(270, expand=False)
            
            
        if depth == 0:
            if face_name == "east":
                return canvas.transpose(Image.FLIP_TOP_BOTTOM).rotate(180, expand=False)
            if face_name == "up":
                return canvas.transpose(Image.FLIP_LEFT_RIGHT).rotate(180, expand=False)
            if face_name == "down":
                return canvas.transpose(Image.FLIP_LEFT_RIGHT).rotate(180, expand=False)
            

        return canvas


    # ---- Blended sides for flat elements ----
    def _make_blended_side_face(
        self,
        face_name: str,
        source_faces: Dict[str, Any],
        all_textures: Dict[int, Image.Image],
        total_element_size: Tuple[float, float, float],
    ) -> Optional[Image.Image]:
        """For flat elements, paint thin sides using adjacent faces' edge colours (half/half)."""
        width, height, depth = total_element_size
        mapping = None

        if depth == 0:
            if face_name in ("east", "west"):
                mapping = (
                    ("north", "left"  if face_name == "east" else "right"),
                    ("south", "left"  if face_name == "east" else "right"),
                    "vertical",
                )
            elif face_name in ("up", "down"):
                mapping = (
                    ("north", "top"    if face_name == "up" else "bottom"),
                    ("south", "top"    if face_name == "up" else "bottom"),
                    "horizontal",
        )


        elif width == 0:
            if face_name in ("north", "south"):
                mapping = (("west", "right"), ("east", "left"), "vertical")
            elif face_name in ("up", "down"):
                mapping = (("west", "top" if face_name == "up" else "bottom"),
                           ("east", "top" if face_name == "up" else "bottom"), "horizontal")

        elif height == 0:
            if face_name in ("north", "south"):
                mapping = (("up", "bottom"), ("down", "top"), "horizontal")
            elif face_name in ("east", "west"):
                mapping = (("up", "bottom"), ("down", "top"), "horizontal")

        if mapping is None:
            self._dbg(f"[blend] {face_name}: mapping not applicable for total={total_element_size}")
            return None

        (nbr1, edge1), (nbr2, edge2), axis = mapping
        self._dbg(f"[blend] {face_name}: using neighbours {nbr1}.{edge1} & {nbr2}.{edge2} ({axis})")

        def crop_edge_strip(nbr_face: str, edge: str) -> Optional[Image.Image]:
            if nbr_face not in source_faces:
                self._dbg(f"[blend] {face_name}: neighbour '{nbr_face}' missing")
                return None
            fdata = source_faces[nbr_face]
            tid = fdata.get("texture")
            if tid is None or int(tid) not in all_textures:
                self._dbg(f"[blend] {face_name}: neighbour '{nbr_face}' texture {tid} not found")
                return None

            tex = all_textures[int(tid)]
            u1, v1, u2, v2 = fdata.get("uv", [0, 0, tex.width, tex.height])
            L, R = min(u1, u2), max(u1, u2)
            T, B = min(v1, v2), max(v1, v2)
            L = max(0, int(L)); R = min(tex.width, max(L + 1, int(round(R))))
            T = max(0, int(T)); B = min(tex.height, max(T + 1, int(round(B))))

            if edge == "left":
                box = (L, T, L + 1, B)
            elif edge == "right":
                box = (R - 1, T, R, B)
            elif edge == "top":
                box = (L, T, R, T + 1)
            elif edge == "bottom":
                box = (L, B - 1, R, B)
            else:
                return None

            if box[2] <= box[0] or box[3] <= box[1]:
                self._dbg(f"[blend] {face_name}: invalid crop box {box} from {nbr_face}")
                return None
            return tex.crop(box)

        s1 = crop_edge_strip(nbr1, edge1)
        s2 = crop_edge_strip(nbr2, edge2)
        if s1 is None and s2 is None:
            self._dbg(f"[blend] {face_name}: both neighbour strips missing; cannot blend")
            return None
        if s1 is None:
            s1 = s2.copy()
        if s2 is None:
            s2 = s1.copy()

        canvas = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        if axis == "vertical":
            canvas.paste(s1.resize((4, 8), Image.NEAREST), (0, 0))
            canvas.paste(s2.resize((4, 8), Image.NEAREST), (4, 0))
        else:
            canvas.paste(s1.resize((8, 4), Image.NEAREST), (0, 0))
            canvas.paste(s2.resize((8, 4), Image.NEAREST), (0, 4))

        canvas = self._orient_blended_canvas(canvas, face_name, total_element_size)
        return canvas

    # ---- Visibility & utility ----
    def _paste_black(self, head: Image.Image, region: Tuple[int, int, int, int], msg: str):
        head.paste(Image.new("RGBA", (8, 8), (0, 0, 0, 255)), region)
        print(msg)

    def _is_face_visible_for_cube(
        self,
        face_name: str,
        cube_pos: Tuple[float, float, float],
        cube_size: Tuple[float, float, float],
        all_cubes: List[Dict[str, Any]],
    ) -> bool:
        """Determine if a face is visible for a cube (not hidden by another cube)"""
        cx, cy, cz = cube_pos
        cw, ch, cd = cube_size

        if face_name == "north":
            center = (cx + cw / 2, cy + ch / 2, cz); normal = (0, 0, -1)
        elif face_name == "south":
            center = (cx + cw / 2, cy + ch / 2, cz + cd); normal = (0, 0, 1)
        elif face_name == "west":
            center = (cx, cy + ch / 2, cz + cd / 2); normal = (-1, 0, 0)
        elif face_name == "east":
            center = (cx + cw, cy + ch / 2, cz + cd / 2); normal = (1, 0, 0)
        elif face_name == "down":
            center = (cx + cw / 2, cy, cz + cd / 2); normal = (0, -1, 0)
        elif face_name == "up":
            center = (cx + cw / 2, cy + ch, cz + cd / 2); normal = (0, 1, 0)
        else:
            return True

        for other in all_cubes:
            if other["position"] == cube_pos and other["size"] == cube_size:
                continue
            if self._cube_blocks_face(center, normal, other["position"], other["size"]):
                print(f"      Face {face_name} blocked by cube at {other['position']}")
                return False
        return True

    def _cube_blocks_face(
        self,
        face_center: Tuple[float, float, float],
        face_normal: Tuple[float, float, float],
        blocking_cube_pos: Tuple[float, float, float],
        blocking_cube_size: Tuple[float, float, float],
    ) -> bool:
        bx, by, bz = blocking_cube_pos
        bw, bh, bd = blocking_cube_size

        fx, fy, fz = face_center
        nx, ny, nz = face_normal

        min_x, max_x = bx, bx + bw
        min_y, max_y = by, by + bh
        min_z, max_z = bz, bz + bd

        t = 0.1
        if nx > 0:
            return (min_x <= fx + t and max_x > fx and min_y <= fy + t and max_y >= fy - t and min_z <= fz + t and max_z >= fz - t)
        if nx < 0:
            return (max_x >= fx - t and min_x < fx and min_y <= fy + t and max_y >= fy - t and min_z <= fz + t and max_z >= fz - t)
        if ny > 0:
            return (min_y <= fy + t and max_y > fy and min_x <= fx + t and max_x >= fx - t and min_z <= fz + t and max_z >= fz - t)
        if ny < 0:
            return (max_y >= fy - t and min_y < fy and min_x <= fx + t and max_x >= fx - t and min_z <= fz + t and max_z >= fz - t)
        if nz > 0:
            return (min_z <= fz + t and max_z > fz and min_x <= fx + t and max_x >= fx - t and min_y <= fy + t and max_y >= fy - t)
        if nz < 0:
            return (max_z >= fz - t and min_z < fz and min_x <= fx + t and max_x >= fx - t and min_y <= fy + t and max_y >= fy - t)
        return False

    def create_black_texture(self) -> str:
        black = Image.new("RGBA", (self.head_texture_size, self.head_texture_size), (0, 0, 0, 255))
        buf = io.BytesIO()
        black.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

    # ---- Flat detection ----
    def get_flat_faces(self, total_element_size: Tuple[float, float, float]) -> List[bool]:
        """
        Return flags [north, east, south, west, up, down] that are flat (dimension == 0).
        Examples:
          (0,2,2) → [False, True, False, True,  False, False]
          (2,0,2) → [False, False, False, False, True,  True]
          (2,2,0) → [True,  False, True,  False, False, False]
        """
        w, h, d = total_element_size
        return [d == 0, w == 0, d == 0, w == 0, h == 0, h == 0]