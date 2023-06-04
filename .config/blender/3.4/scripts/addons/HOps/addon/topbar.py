from bpy.utils import register_tool, unregister_tool

from . utility import addon
from . tools.hopstool import Hops, HopsEdit
from . tools.mirror import HopsMirror

def register():

    if addon.bc():
        register_tool(Hops, after={"BoxCutter"}, group=False)
        register_tool(HopsEdit, after={"BoxCutter"}, group=False)
        # register_tool(HopsMirror, after={"Hops"}, group=False)
    else:
        register_tool(Hops, group=False, separator=True)
        register_tool(HopsEdit, group=False, separator=True)
        # register_tool(HopsMirror, after={"Hops"}, group=False)


def unregister():

    # unregister_tool(HopsMirror)
    unregister_tool(HopsEdit)
    unregister_tool(Hops)
