# BBModel to BDEngine Converter

This project provides a toolset to convert [Blockbench](https://blockbench.net/) `.bbmodel` files into a format compatible with **Block Display Engine** using player heads for 3D rendering. It handles geometry translation, texture subdivision, and display optimization.

> ⚠️ **This project is a work in progress. Expect bugs and incomplete features. Contributions and issue reports are welcome!**

---

## 🧰 Features

* Conversion from `.bbmodel` to `.bdengine`
* Multi-texture support and UV-correct texture slicing
* Handling of flat and degenerate elements
* Rotation-aware positioning and transformation

---

## 🚀 How to Use

### 🔧 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

### ▶️ Run the Converter

Place your `.bbmodel` files in the project root directory, then run:

```bash
python main.py
```

You'll be prompted to select a `.bbmodel` file. The converter will output a `.bdengine` file.

---

## ⚙️ How It Works

1. **File Parsing**:

   * Loads the `.bbmodel` file
   * Extracts element geometry and textures

2. **Conversion Strategy**:

   * Two strategies implemented via `conversion_strategy.py`:

     * `StretchConversionStrategy`: fast, 1 head per element
     * `SmartCubeConversionStrategy`: precise, subdivides shapes and textures for better visual fidelity

3. **Texture Management**:

   * Textures are extracted, sliced, and resized to fit Minecraft head format (32x32)
   * Each visible cube face is mapped according to its UV coordinates

4. **Geometry to Heads**:

   * For each cube, a player head entity is generated with position, scale, rotation, and paintTexture
   * Rotations follow Blockbench's `Z * X * Y` order

5. **Output**:

   * A `.bdengine` file is created with all player head definitions for use in BDEngine

---

## ⚠️ Limitations & Known Issues

* 🔄 Rotation handling is sometimes off when stacking multiple transformed cubes
* 🖼️ Texture atlas construction for mixed-texture elements can fail in edge cases
* 🐞 This project is still under development please report issues or contribute fixes

---

## 📂 File Structure Overview

```
.
├── main.py                      # Entry point
├── converter.py                 # Conversion orchestration
├── config.py                    # Global constants and settings
├── conversion_strategy.py       # Conversion logic (stretch/smart)
├── element_analyzer.py          # Determines element shapes
├── head_factory.py              # Generates BDEngine head entries
├── math_utils.py                # Geometry and rotation math
├── texture_manager.py           # Texture loading and slicing
├── texture_subdivider.py       # Texture subdivision per cube
├── smart_cube_optimizer.py     # Smart cube decomposition logic
├── tool/                       # Utility scripts (e.g., texture decode)
├── textures/
│   └── default.png             # Default fallback texture
└── requirements.txt            # Python dependencies
```

---

## ❤️ Contributing

If you find bugs, want to improve the conversion accuracy, or add new features, feel free to open a pull request or issue. You can also contact me on discord xerneas02.

---

## 🧪 Status

This project is under **active development** and not yet production-ready.

Use with caution and always verify the output in a test environment.
