#!/usr/bin/env python3
"""
File Picker Utility for IceScriber
Supports both CLI and GUI file selection

Usage:
    # CLI mode (manual path entry)
    python file_picker.py --cli

    # GUI mode (file browser dialog)
    python file_picker.py --gui

    # As a library
    from file_picker import pick_files
    files = pick_files(mode='gui', filetype='audio')
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

# Try to import tkinter for GUI mode
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


class FilePicker:
    """Handle file selection for IceScriber."""

    AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.flac', '.ogg')
    JSON_EXTENSIONS = ('.json',)

    def __init__(self):
        self.selected_files: List[Path] = []

    def pick_gui(self, filetype: str = 'audio', multiple: bool = True) -> List[Path]:
        """
        Open GUI file picker dialog.

        Args:
            filetype: 'audio' or 'json'
            multiple: Allow selecting multiple files

        Returns:
            List of selected file paths
        """
        if not HAS_GUI:
            print("❌ GUI mode not available (tkinter not installed)")
            print("   Falling back to CLI mode...")
            return self.pick_cli(filetype)

        # Create invisible root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Set file type filters
        if filetype == 'audio':
            filetypes = [
                ('Audio Files', '*.mp3 *.m4a *.wav *.flac *.ogg'),
                ('MP3 Files', '*.mp3'),
                ('M4A Files', '*.m4a'),
                ('WAV Files', '*.wav'),
                ('All Files', '*.*')
            ]
            title = "Select Audio File(s)"
        elif filetype == 'json':
            filetypes = [
                ('JSON Files', '*.json'),
                ('All Files', '*.*')
            ]
            title = "Select JSON File(s)"
        else:
            filetypes = [('All Files', '*.*')]
            title = "Select File(s)"

        # Open dialog
        if multiple:
            files = filedialog.askopenfilenames(
                title=title,
                filetypes=filetypes
            )
            selected = [Path(f) for f in files] if files else []
        else:
            file = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes
            )
            selected = [Path(file)] if file else []

        root.destroy()

        if selected:
            print(f"✓ Selected {len(selected)} file(s):")
            for f in selected:
                print(f"  • {f.name}")
        else:
            print("⚠️  No files selected")

        return selected

    def pick_folder_gui(self, title: str = "Select Folder") -> Optional[Path]:
        """
        Open GUI folder picker dialog.

        Returns:
            Selected folder path or None
        """
        if not HAS_GUI:
            print("❌ GUI mode not available")
            return self.pick_folder_cli()

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        folder = filedialog.askdirectory(title=title)
        root.destroy()

        if folder:
            selected = Path(folder)
            print(f"✓ Selected folder: {selected}")
            return selected
        else:
            print("⚠️  No folder selected")
            return None

    def pick_cli(self, filetype: str = 'audio') -> List[Path]:
        """
        CLI file picker (manual path entry).

        Args:
            filetype: 'audio' or 'json'

        Returns:
            List of selected file paths
        """
        print(f"\n📁 File Picker (CLI Mode)")
        print(f"File type: {filetype}")
        print()

        selected = []

        while True:
            path_str = input("Enter file path (or 'done' to finish): ").strip()

            if path_str.lower() in ['done', 'exit', 'quit', '']:
                break

            # Handle drag-and-drop (quoted paths)
            if path_str.startswith('"') and path_str.endswith('"'):
                path_str = path_str[1:-1]
            if path_str.startswith("'") and path_str.endswith("'"):
                path_str = path_str[1:-1]

            path = Path(path_str).expanduser().resolve()

            if not path.exists():
                print(f"  ❌ File not found: {path}")
                continue

            if not path.is_file():
                print(f"  ❌ Not a file: {path}")
                continue

            # Check extension
            if filetype == 'audio' and path.suffix.lower() not in self.AUDIO_EXTENSIONS:
                print(f"  ⚠️  Not an audio file: {path.suffix}")
                confirm = input("    Add anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue

            if filetype == 'json' and path.suffix.lower() != '.json':
                print(f"  ⚠️  Not a JSON file: {path.suffix}")
                confirm = input("    Add anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue

            selected.append(path)
            print(f"  ✓ Added: {path.name}")

        if selected:
            print(f"\n✓ Selected {len(selected)} file(s)")
        else:
            print("\n⚠️  No files selected")

        return selected

    def pick_folder_cli(self) -> Optional[Path]:
        """CLI folder picker."""
        print("\n📁 Folder Picker (CLI Mode)")
        path_str = input("Enter folder path: ").strip()

        if not path_str:
            return None

        # Handle quotes
        if path_str.startswith('"') and path_str.endswith('"'):
            path_str = path_str[1:-1]
        if path_str.startswith("'") and path_str.endswith("'"):
            path_str = path_str[1:-1]

        path = Path(path_str).expanduser().resolve()

        if not path.exists():
            print(f"❌ Folder not found: {path}")
            return None

        if not path.is_dir():
            print(f"❌ Not a folder: {path}")
            return None

        print(f"✓ Selected: {path}")
        return path

    def scan_folder(self, folder: Path, filetype: str = 'audio', recursive: bool = False) -> List[Path]:
        """
        Scan folder for files of given type.

        Args:
            folder: Folder to scan
            filetype: 'audio' or 'json'
            recursive: Scan subfolders

        Returns:
            List of found files
        """
        if filetype == 'audio':
            extensions = self.AUDIO_EXTENSIONS
        elif filetype == 'json':
            extensions = self.JSON_EXTENSIONS
        else:
            extensions = ('.*',)

        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'

        files = []
        for ext in extensions:
            files.extend(folder.glob(f"{pattern}{ext}"))

        files.sort()
        return files


# Convenience functions
def pick_files(mode: str = 'auto', filetype: str = 'audio', multiple: bool = True) -> List[Path]:
    """
    Pick files using GUI or CLI.

    Args:
        mode: 'auto', 'gui', or 'cli'
        filetype: 'audio' or 'json'
        multiple: Allow multiple files

    Returns:
        List of selected file paths
    """
    picker = FilePicker()

    if mode == 'auto':
        mode = 'gui' if HAS_GUI else 'cli'

    if mode == 'gui':
        return picker.pick_gui(filetype, multiple)
    else:
        return picker.pick_cli(filetype)


def pick_folder(mode: str = 'auto') -> Optional[Path]:
    """
    Pick folder using GUI or CLI.

    Args:
        mode: 'auto', 'gui', or 'cli'

    Returns:
        Selected folder path
    """
    picker = FilePicker()

    if mode == 'auto':
        mode = 'gui' if HAS_GUI else 'cli'

    if mode == 'gui':
        return picker.pick_folder_gui()
    else:
        return picker.pick_folder_cli()


def scan_folder(folder: Path, filetype: str = 'audio', recursive: bool = False) -> List[Path]:
    """
    Scan folder for files.

    Args:
        folder: Folder to scan
        filetype: 'audio' or 'json'
        recursive: Scan subfolders

    Returns:
        List of found files
    """
    picker = FilePicker()
    return picker.scan_folder(folder, filetype, recursive)


# CLI interface
def main():
    import argparse

    parser = argparse.ArgumentParser(description="IceScriber File Picker")
    parser.add_argument('--mode', choices=['gui', 'cli', 'auto'], default='auto',
                        help="Picker mode (default: auto)")
    parser.add_argument('--type', dest='filetype', choices=['audio', 'json', 'any'], default='audio',
                        help="File type filter (default: audio)")
    parser.add_argument('--single', action='store_true',
                        help="Select single file only")
    parser.add_argument('--folder', action='store_true',
                        help="Pick folder instead of files")
    parser.add_argument('--scan', type=str, metavar='FOLDER',
                        help="Scan folder for files")
    parser.add_argument('--recursive', action='store_true',
                        help="Scan subfolders (with --scan)")

    args = parser.parse_args()

    if args.scan:
        folder = Path(args.scan)
        if not folder.exists():
            print(f"❌ Folder not found: {folder}")
            sys.exit(1)

        files = scan_folder(folder, args.filetype, args.recursive)
        print(f"\n✓ Found {len(files)} file(s):")
        for f in files:
            print(f"  • {f}")

    elif args.folder:
        folder = pick_folder(args.mode)
        if folder:
            print(f"\nSelected: {folder}")
        else:
            print("\nNo folder selected")

    else:
        files = pick_files(args.mode, args.filetype, not args.single)
        if files:
            print(f"\nSelected files:")
            for f in files:
                print(f"  {f}")
        else:
            print("\nNo files selected")


if __name__ == "__main__":
    main()
