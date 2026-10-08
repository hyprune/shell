"""Private SDK mock package fixture; never modify installed owner worlds."""
from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parent
folder=ROOT/'.run/style-world';folder.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'observatory.world.json').read_text());manifest.setdefault('extensions',{})['com.hyprune.hud-style']={'theme':'hud/theme.json'}
(folder/'world.json').write_text(json.dumps(manifest))
shutil.copytree(ROOT/'styles/signal-amber/hud',folder/'hud',dirs_exist_ok=True)
# Exercise package-only FontLoader with a local installed open-source font.
font=Path(subprocess.check_output(['fc-match','-f','%{file}','DejaVu Sans'],text=True))
(folder/'hud/fonts').mkdir(exist_ok=True);shutil.copyfile(font,folder/'hud/fonts/Display.ttf')
theme=json.loads((folder/'hud/theme.json').read_text());theme['font']='hud/fonts/Display.ttf';theme['corners']='bevel'
(folder/'hud/theme.json').write_text(json.dumps(theme))
