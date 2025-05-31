import os

_is_debug_ = True if os.getenv('DEBUG') == '1' else False
def printD(*args, **kwargs):
    if _is_debug_:
        print("\t\033[0;31mDEBUG \033[0m",*args, **kwargs)


def isDebug():
    return _is_debug_