#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({k:os.environ.get(k) for k in ['HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY']}))
