"""Main user interface"""

import os
from typing import List
from config import Config
from converter import BBModelConverter

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
        
        bbmodel_file = self._select_bbmodel_file()
        
        if bbmodel_file:
            print(f"Selected file: {bbmodel_file}")
            print(f"Mode used: {mode}")
            print()
            
            try:
                output_file = self.converter.convert_file(bbmodel_file)
                print()
                print(f"✅ Conversion successful! File created: {output_file}")
            except Exception as e:
                print(f"❌ Conversion error: {e}")
        else:
            print("No file selected.")
    
    def _select_bbmodel_file(self) -> str:
        """Allows user to select .bbmodel file"""
        
        bbmodel_files = self._find_bbmodel_files()
        
        if not bbmodel_files:
            print("No .bbmodel files found in current directory.")
            return None
        
        if len(bbmodel_files) == 1:
            return bbmodel_files[0]
        
        return self._choose_from_multiple_files(bbmodel_files)
    
    def _find_bbmodel_files(self) -> List[str]:
        """Finds all .bbmodel files in current directory"""
        return [f for f in os.listdir('.') if f.endswith('.bbmodel')]
    
    def _choose_from_multiple_files(self, bbmodel_files: List[str]) -> str:
        """Allows user to choose from multiple files"""
        
        print()
        print("Multiple .bbmodel files found:")
        
        for i, file in enumerate(bbmodel_files, 1):
            print(f"{i}. {file}")
        
        print()
        
        while True:
            try:
                choice = int(input("Choose a file (number): ")) - 1
                if 0 <= choice < len(bbmodel_files):
                    return bbmodel_files[choice]
                else:
                    print("Invalid number.")
            except ValueError:
                print("Please enter a valid number.")

def main():
    """Main entry point"""
    ui = UserInterface()
    ui.run()

if __name__ == "__main__":
    main()