"""Bounded, live world-ink edits; normal world.control, never camera.author."""
import copy
import math


class OutlineController:
    def __init__(self, client):
        self.client = client
        self.world = None
        self.loaded_colour = None

    async def update(self, world_id, patch=None):
        def current():
            return ((self.client.state or {}).get('world') or {}).get('id')
        if not world_id or current() != world_id:
            raise ValueError('World changed; refresh the ink controls')
        result = await self.client.call('atmosphere.get', {})
        profile = result['profile']
        ink = profile.get('outline') if profile else None
        if self.world != world_id:
            self.world, self.loaded_colour = world_id, None
        if ink and self.loaded_colour is None:
            self.loaded_colour = list(ink['colour'])
        if patch is not None:
            if not ink or not patch or set(patch) - {'widthPx','colour'}:
                raise ValueError('This world has no editable ink style')
            patch = copy.deepcopy(patch)
            if 'widthPx' in patch:
                v = patch['widthPx']
                if type(v) not in [int,float] or not math.isfinite(v) or not 1 <= v <= 4:
                    raise ValueError('Ink width must be 1–4 logical pixels')
            if 'colour' in patch:
                if patch['colour'] is None: patch['colour'] = self.loaded_colour
                v = patch['colour']
                if not isinstance(v,list) or len(v)!=3 or any(type(c) not in [int,float] or not math.isfinite(c) or not 0<=c<=1 for c in v):
                    raise ValueError('Ink colour must be display RGB in 0–1')
            # Merge into a fresh profile; retain current sky, thresholds and all
            # unrelated settings. Never reuse a stale QML copy of the atmosphere.
            profile = copy.deepcopy(profile)
            profile['outline'].update(patch)
            if current() != world_id: raise ValueError('World changed; ink edit cancelled')
            await self.client.call('atmosphere.set', {'profile':profile})
            ink = profile['outline']
        if current() != world_id: raise ValueError('World changed; refresh the ink controls')
        return {'worldId':world_id,'style':ink,'loadedColour':self.loaded_colour}
