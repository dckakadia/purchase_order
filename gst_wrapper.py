import importlib.util, sys, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'GST-Monthly-Purchase-Data_Compair-GSTN-Vs-Tally.py')
spec = importlib.util.spec_from_file_location("gst_module", _path)
_mod = importlib.util.module_from_spec(spec)
sys.modules["gst_module"] = _mod
spec.loader.exec_module(_mod)
app = _mod.app
