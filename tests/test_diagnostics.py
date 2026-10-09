"""Diagnostics preserve schema location without copying private frame content."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from diagnostics import diagnostic
from protocol import V15_VALIDATOR

class DiagnosticsTests(unittest.TestCase):
    def test_mount_error_reports_exact_path_and_redacts_identifiers(self):
        mounts={name:[] for name in ['areas','anchors','bindings','placements','objects','placementZones','instances']}
        mounts.update(carriedSurfaceId=None,desktopWorkspaceId=None)
        instance={'surfaceId':'private-window-title','workspaceId':8,'areaId':'','anchorId':'private-anchor','status':'placed'}
        mounts['instances']=[instance]
        message={'jsonrpc':'2.0','method':'state.delta','params':{'sessionId':'session','subscriptionId':'sub','baseRevision':1,'revision':2,'changes':{'mounts':mounts}}}
        validator=V15_VALIDATOR.evolve(schema={'$ref':V15_VALIDATOR.schema['$id']+'#/$defs/state.delta.notification'})
        error=next(validator.iter_errors(message))
        result=diagnostic(V15_VALIDATOR,message,error,'state.delta')
        self.assertEqual(result['path'],'/params/changes/mounts/instances/0/areaId')
        self.assertNotIn('private-',json.dumps(result))
        del instance['areaId']
        validator.validate(message)

    def test_unknown_properties_and_tokens_are_not_logged(self):
        message={'private-package-name':{'token':'a'*64,'title':'private-window-title'}}
        error=next(V15_VALIDATOR.iter_errors(message))
        result=json.dumps(diagnostic(V15_VALIDATOR,message,error))
        for private in ['private-package-name','private-window-title','a'*64]:self.assertNotIn(private,result)
        self.assertLess(len(result),1000)
