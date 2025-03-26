import os
import subprocess
from streamlit_desktop_app import build_desktop

def main():
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the entry point (your main app file)
    entry_point = os.path.join(current_dir, "app.py")
    
    # Define the output directory
    output_dir = os.path.join(current_dir, "dist")
    
    # Build the desktop application
    build_desktop(
        entry_point=entry_point,
        output_dir=output_dir,
        app_name="DataViewer",
        icon_path=None,  # You can add an icon file path here if you have one
        requirements_file="requirements.txt"
    )

if __name__ == "__main__":
    main() 