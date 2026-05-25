import importlib.util, sys, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'Import_BOE_to_Tally_GST_Entry.py')
spec = importlib.util.spec_from_file_location("boe_module", _path)
_mod = importlib.util.module_from_spec(spec)
sys.modules["boe_module"] = _mod
spec.loader.exec_module(_mod)
app = _mod.app
