"""Director tab names (dev hooks address tabs by name) follow the Director's tab list."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TabNames(unittest.TestCase):
    def test_names_match_director_tabs(self):
        state = (ROOT / 'qml/ShellState.qml').read_text()
        director = (ROOT / 'qml/components/Director.qml').read_text()
        keys = re.findall(r"'([a-z]+)'", re.search(r'tabKeys: \[([^\]]*)\]', state).group(1))
        count = int(re.search(r'tabCount: (\d+)', state).group(1))
        tabs = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", re.search(r'property var tabs: \[([^\]]*)\]', director).group(1))]
        self.assertEqual(len(keys), count)
        self.assertEqual(keys, [re.sub(r'[^a-z]', '', t.lower()) for t in tabs])
        self.assertEqual(keys.index('quests'), keys.index('map') + 1)


if __name__ == '__main__':
    unittest.main()
