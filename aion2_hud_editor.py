#!/usr/bin/env python
"""
AION2 HUD Editor
==================
Standalone application that decodes DeviceSetting.dat, provides a visual HUD
preview with editing capabilities, and re-encodes back to .dat format.

Flow:
    Launch  ->  Select .dat file  ->  Decode (with progress UI)  ->  Preview
    Preview ->  Edit / Copy / Import JSON  ->  Save back to .dat (with backup)

Default .dat path:
    C:\\Users\\{user}\\AppData\\Local\\AION2\\Saved\\PersistentDownloadDir\\UserSetting\\DeviceSetting.dat
"""

import sys
import tkinter as tk

from dialogs import StartupDialog
from preview import HudPreviewApp


def main():
    # Phase 1: Startup dialog
    startup = StartupDialog()
    result = startup.run()

    if not result:
        sys.exit(0)

    global_settings, characters, encode_ctx, dat_path = result

    # Phase 2: Preview window
    root = tk.Tk()
    app = HudPreviewApp(root, global_settings, characters, encode_ctx, dat_path)
    root.mainloop()


if __name__ == '__main__':
    main()
