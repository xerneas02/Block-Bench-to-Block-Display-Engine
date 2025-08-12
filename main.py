"""Main user interface"""

import os
from typing import List
from config import Config
from converter import BBModelConverter
import traceback

class UserInterface:
    """User interface"""
    
    def __init__(self):
        self.config = Config()
        self.converter = BBModelConverter()
    
    def run(self) -> None:
        """Runs user interface"""
        
        print("=== BBModel to BDEngine Converter ===")
        print()
        
        mode = "cube"
        self.converter.set_conversion_mode(mode)
        
        bbmodel_selection = self._select_bbmodel_file()
        
        if not bbmodel_selection:
            print("No file selected.")
            return
        
        if isinstance(bbmodel_selection, list):
            # Convert all files in the list
            print(f"Converting {len(bbmodel_selection)} files in mode '{mode}'...")
            for file in bbmodel_selection:
                try:
                    print(f"→ {file}")
                    output_file = self.converter.convert_file(file)
                    print(f"   ✅ Conversion successful: {output_file}")
                except Exception as e:
                    traceback.print_exc()
                    print(f"   ❌ Conversion error for {file}: {e}")
        else:
            # Convert a single file
            print(f"Selected file: {bbmodel_selection}")
            print(f"Mode used: {mode}")
            print()
            try:
                output_file = self.converter.convert_file(bbmodel_selection)
                print()
                print(f"✅ Conversion successful! File created: {output_file}")
            except Exception as e:
                traceback.print_exc()
                print(f"❌ Conversion error: {e}")
    
    def _select_bbmodel_file(self):
        """Allows user to select one or all .bbmodel files"""
        
        bbmodel_files = self._find_bbmodel_files()
        
        if not bbmodel_files:
            print("No .bbmodel files found in current directory.")
            return None
        
        if len(bbmodel_files) == 1:
            return bbmodel_files[0]
        
        print()
        print("Multiple .bbmodel files found:")
        for i, file in enumerate(bbmodel_files, 1):
            print(f"{i}. {file}")
        print("0. Convert all files")
        
        print()
        
        while True:
            try:
                choice = int(input("Choose a file (number): "))
                if choice == 0:
                    return bbmodel_files  # return list to signal "convert all"
                elif 1 <= choice <= len(bbmodel_files):
                    return bbmodel_files[choice - 1]
                else:
                    print("Invalid number.")
            except ValueError:
                print("Please enter a valid number.")
    
    def _find_bbmodel_files(self) -> List[str]:
        """Finds all .bbmodel files in current directory"""
        return [f for f in os.listdir('.') if f.endswith('.bbmodel')]


def main():
    """Main entry point"""
    ui = UserInterface()
    ui.run()

if __name__ == "__main__":
    main()