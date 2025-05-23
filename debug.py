import os
_is_debug_ = True if os.getenv('DEBUG') == '1' else False
def printD(*args, **kwargs):
    if _is_debug_:
        print("Dbg",*args, **kwargs)