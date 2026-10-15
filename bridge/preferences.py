"""Small, versioned shell-only presentation preferences; never core configuration."""
import json
import os
from pathlib import Path
import tempfile

DEFAULTS = dict(version=1, concept='Adventure', curvature=.8, curved=True, resource='gpu', worldStyles=True, theme='night')
# Concept names from earlier releases, still accepted in saved preferences and patches.
LEGACY_CONCEPTS = {'Vanguard': 'Adventure'}

def validate(patch):
    if not isinstance(patch, dict) or set(patch) - set(DEFAULTS):
        raise ValueError('Unknown presentation preference')
    patch = dict(patch)
    if patch.get('concept') in LEGACY_CONCEPTS: patch['concept'] = LEGACY_CONCEPTS[patch['concept']]
    for key, value in patch.items():
        if key == 'version' and value != 1: raise ValueError('Unsupported preferences version')
        if key == 'concept' and value not in ['Adventure','Instrument','Minimal']: raise ValueError('Unknown HUD concept')
        if key == 'resource' and value not in ['gpu','cpu','ram','tool']: raise ValueError('Unknown HUD resource')
        if key in ['curved','worldStyles'] and not isinstance(value, bool): raise ValueError('Curved must be boolean')
        if key == 'curvature' and (type(value) not in [int,float] or not 0 <= value <= 1): raise ValueError('Curvature must be 0–1')
        if key == 'theme' and value not in ['night','paper']: raise ValueError('Unknown theme')
    return patch

class Preferences:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('HYPRUNE_SHELL_PREFERENCES') or Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config'))) / 'hyprune/shell.json')
        self.value = dict(DEFAULTS)
        try:
            saved = json.loads(self.path.read_text())
            value = validate(saved)
            if saved.get('concept') in LEGACY_CONCEPTS: self.update(value)
            else: self.value.update(value)
        except (OSError, ValueError, TypeError): pass

    def update(self, patch):
        next_value = {**self.value, **validate(patch)}
        if next_value == self.value: return self.value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.shell-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(next_value, output, indent=2); output.write('\n')
                output.flush(); os.fsync(output.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)
        self.value = next_value
        return self.value
