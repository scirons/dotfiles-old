import bpy
import bpy.types as bt
import time

from . import auto_load
from . import library_manager
from . import lib_tools
from .t3dn_bip import ops as preview_ops

def import_asset(file: str, name: str, asset_type: str, link: bool = False) -> bpy.types.ID:
    with bpy.data.libraries.load(file, link=link) as (f, t):
        if not name in getattr(f, asset_type):
            raise KeyError(f'Asset "{name}" not in "{asset_type}" of source file "{file}"')
        getattr(t, asset_type).append(name)
    return getattr(bpy.data, asset_type).get(name)

class SanctusOperator(bt.Operator):
    bl_idname = 'sl.dummy'
    bl_label = 'Sanctus Operator'
    bl_options = {'UNDO'}

def is_ID_derived_from(id_name: str, original_name: str) -> bool:
    if id_name == original_name:
        return True

    if not id_name.startswith(original_name): #has to start with original name
        return False
    stump = id_name.replace(original_name, '', 1)
    if not stump[0] == '.': #stump has to have the number signature ".001"
        return False
    if not stump[1:].isnumeric():
        return False
    return True

class SanctusAssetImportOperator(SanctusOperator):

    asset_type = 'materials'

    library_path: bpy.props.StringProperty()

    reimport_asset: bpy.props.BoolProperty(default=False)

    def get_lib_item(self):
        return library_manager.LIBRARY.path_resolve(self.library_path)

    def asset_exists(self) -> bool:
        return self.get_lib_item().item_name in getattr(bpy.data, self.asset_type).keys()
    
    def is_asset_incompatible(self, context: bt.Context) -> bool:
        return not context.scene.render.engine in self.get_lib_item().get_compatible_engines()

    def invoke(self, context: bt.Context, _event):
        if self.asset_exists() or self.is_asset_incompatible(context):
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
    
    def draw(self, context: bt.Context):
        layout = self.layout
        if self.asset_exists():
            layout.label(text='Asset found in Blend File. Re-Import?')
            r = layout.row(align=True)
            r.prop(self, 'reimport_asset', text='Use Existing', toggle=1, invert_checkbox=True)
            r.prop(self, 'reimport_asset', text='Reimport Asset', toggle=1, invert_checkbox=False)
        if self.is_asset_incompatible(context):
            engine = context.scene.render.engine
            c = layout.column()
            c.scale_y = 0.8
            c.label(text=f'This asset is not compatible with "{library_manager.get_render_engine_name(engine)}".')
            c.label(text=f'Switching to {self.get_lib_item().get_compatible_engines(as_string=True)} is recommended.')
    
    def get_asset(self) -> bt.ID:
        asset_collection: bt.bpy_prop_collection = getattr(bpy.data, self.asset_type)
        old_assets: list[bt.ID] = list(asset_collection.values())
        lib_item = self.get_lib_item()
        asset_name = lib_item.item_name
        if not asset_name in asset_collection.keys() or self.reimport_asset:
            self.report({'INFO'}, f'Import Asset "{asset_name}"')
            import_asset(str(lib_item.blend_file), asset_name, self.asset_type, link=False)
            asset = next(x for x in asset_collection.values() if not x in old_assets and is_ID_derived_from(x.name, asset_name))
        else:
            asset = asset_collection[asset_name]
        return asset

@auto_load.blender_operator
class SL_OT_apply_material(SanctusAssetImportOperator):
    bl_idname = 'sl.apply_material'
    bl_label = 'Apply Material'
    asset_type = 'materials'

    @classmethod
    def description(cls, context: bt.Context, properties) -> str:
        if cls.poll(context):
            return 'Add the selected Sanctus Library Material to the active object. Hold SHIFT to reimport the material'
        else:
            return 'INVALID OBJECT! Active Object has to be a Mesh or a Curve'

    @classmethod
    def poll(cls, context: bt.Context):
        try:
            return context.object.type in ['MESH', 'CURVE'] and context.object.data
        except:
            return False
    
    def execute(self, context: bt.Context):

        obj: bt.Object = context.object
        mat = self.get_asset()

        obj.active_material = mat
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_import_material(SanctusAssetImportOperator):
    bl_idname = 'sl.import_material'
    bl_label = 'Import Material'
    bl_description = 'Imports Material asset from library into file. Wont be used by default.'
    asset_type = 'materials'

    @classmethod
    def poll(cls, context: bt.Context):
        return True

    def execute(self, context: bt.Context):
        self.get_asset()
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_add_geometry_nodes_object(SanctusAssetImportOperator):
    bl_idname = 'sl.add_geometry_nodes_object'
    bl_label = 'Add Asset'
    bl_description = 'Add a New asset to Scene'
    asset_type = 'objects'

    def execute(self, context: bt.Context):
        obj = self.get_asset()
        context.collection.objects.link(obj)
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_apply_geometry_nodes(SanctusAssetImportOperator):
    bl_idname = 'sl.apply_geometry_nodes'
    bl_label = 'Apply Asset to Object'
    asset_type = 'node_groups'

    @classmethod
    def description(cls, context: bt.Context, properties: bt.OperatorProperties) -> str:
        if cls.poll(context):
            return 'Apply the selected ssset to the active object'
        else:
            return 'INVALID OBJECT! Active object has to be a Mesh or a Curve'

    @classmethod
    def poll(cls, context: bt.Context):
        try:
            return (context.object.type in ['MESH', 'CURVE'] and context.object.data)
        except:
            return False

    def execute(self, context: bt.Context):

        nt: bt.GeometryNodeTree = self.get_asset()
        obj: bt.Object = context.object
        mod: bt.NodesModifier = obj.modifiers.new(nt.name, 'NODES')
        mod.node_group = nt
        return {"FINISHED"}

@auto_load.blender_operator
class SL_OT_add_group_node(SanctusAssetImportOperator):
    bl_idname = 'sl.add_group_node'
    bl_label = 'Add Group Node'
    bl_description = 'Add a group node of the selected Sanctus Library asset to the active node tree. Hold SHIFT to reimport the group'
    asset_type = 'node_groups'

    @classmethod
    def poll(cls, context: bt.Context):
        try:
            return context.space_data.edit_tree.bl_idname == 'ShaderNodeTree'
        except:
            return False
    
    def execute(self, context: bt.Context):

        sd: bt.SpaceNodeEditor = context.space_data
        nt: bt.ShaderNodeTree = sd.edit_tree
        
        group = self.get_asset()

        node: bt.Node = nt.nodes.new('ShaderNodeGroup')
        node.location = sd.cursor_location
        node.node_tree = group
        for n in nt.nodes:
            n.select = n == node
        bpy.ops.node.translate_attach('INVOKE_DEFAULT')
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_switch_library_item(bt.Operator):
    bl_idname = 'sl.switch_library_item'
    bl_label = 'Switch Library Item'
    bl_description = 'Switches the enum for a given library in the given direction'

    library_path: bpy.props.StringProperty()
    backwards: bpy.props.BoolProperty()

    def execute(self, context: bt.Context):
        wm = context.window_manager
        sublib: library_manager.Library = library_manager.LIBRARY.path_resolve(self.library_path)
        items = sublib.get_enum_items()
        enum_name = sublib.get_enum_attr_name()
        current_active = getattr(wm, enum_name)
        index = next(i for i, t in enumerate(items) if t[0] == current_active)
        offset = -1 if self.backwards else +1
        setattr(wm, enum_name, items[(index + offset) % len(items)][0])
        return {'FINISHED'}
    
    @classmethod
    def draw_ui(cls, layout: bt.UILayout, library: library_manager.Library, backwards: bool = False, **button_props) -> None:
        icon = 'TRIA_LEFT' if backwards else 'TRIA_RIGHT'
        draw_props = dict(
            text='',
            icon=icon,
        )
        draw_props.update(button_props)
        props = layout.operator(cls.bl_idname, **draw_props)
        props.library_path = library.library_path
        props.backwards = backwards


@auto_load.blender_operator
class SL_OT_open_documentation(SanctusOperator):
    bl_idname = 'sl.open_documentation'
    bl_label = 'Open Documentation'
    bl_description = 'Open a weblink to the official Sanctus Library Documentation'

    def execute(self, context):
        bpy.ops.wm.url_open(url="http://sanctuslibrary.xyz")
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_open_video_guide(SanctusOperator):
    bl_idname = 'sl.open_video_guide'
    bl_label = 'Open Video Guide'
    bl_description = 'Open a weblink to the official Sanctus Library Video Guide'

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://www.youtube.com/watch?v=M1eyCqOondA")
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_reload_library(SanctusOperator):
    bl_idname = 'sl.reload_library'
    bl_label = 'Reload Library'
    bl_description = 'Reload the entire Sanctus Library'

    def execute(self, context):
        from . import library_manager
        library_manager.reload_library_full()
        return {'FINISHED'}

meta_engine_items = [
    ('A', 'Any', 'Use Any Engine'),
    ('C', 'Cycles', 'Use the Cycles Render Engine'),
    ('E', 'Eevee', 'Use the Eevee Render Engine')
]

meta_complexity_items = [
    ('0', 'Low', 'Low Complexity'),
    ('1', 'Medium', 'Medium Complexity'),
    ('2', 'High', 'High Complextiy')
]

@auto_load.blender_operator
class SL_OT_set_meta_data(SanctusOperator):
    bl_idname = 'sl.set_meta_data'
    bl_label = 'Set Meta Data'
    bl_description = 'Set Meta Data on the selected Sanctus Library Item'

    meta_engine: bpy.props.EnumProperty(name='Engine', items=meta_engine_items)
    meta_complexity: bpy.props.EnumProperty(name='Complexity', items=meta_complexity_items)
    meta_use_displacement: bpy.props.BoolProperty(name='Use Displacement')

    library_path: bpy.props.StringProperty()

    def invoke(self, context, event):
        if event.shift:
            return self.execute(context)
        else:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
    
    def get_item(self) -> library_manager.LibraryItem:
        return library_manager.LIBRARY.path_resolve(self.library_path)
    
    def draw(self, context):
        layout: bt.UILayout = self.layout
        item = self.get_item()
        layout.label(text=item.item_name)
        layout.use_property_split = True
        layout.prop(self, 'meta_engine')
        layout.prop(self, 'meta_complexity')
        layout.prop(self, 'meta_use_displacement')

    def execute(self, context):
        
        d = {
            'engine': self.meta_engine,
            'complexity': int(self.meta_complexity),
            'use_displacement': self.meta_use_displacement
        }

        item = self.get_item()
        lib_tools.write_meta_file(item.directory, item.item_name, d, force_update=True)
        item.update_meta()

        return {'FINISHED'}

def is_baking_context(context: bt.Context):
    return (
        context.area.type == 'NODE_EDITOR'
        and context.space_data.edit_tree.bl_idname == 'ShaderNodeTree'
    )

@auto_load.blender_operator
class SL_OT_set_bake_socket(SanctusOperator):
    bl_idname = 'sl.set_bake_socket'
    bl_label = 'Set Bake Socket'
    bl_description = 'Set the selected socket active for baking using the Sanctus Library'

    socket: bpy.props.StringProperty()
    enabled: bpy.props.BoolProperty(default=True)

    def get_socket(self) -> bt.NodeSocketStandard:
        return eval(self.socket)

    @classmethod
    def poll(cls, context):
        try:
            return is_baking_context(context)
        except:
            return False
    
    def execute(self, _context: bt.Context):
        from . import baking
        socket = self.get_socket()
        baking.set_socket_enabled(socket, self.enabled)
        return {'FINISHED'}
    
    @classmethod
    def draw_ui(cls, layout: bt.UILayout, socket: bt.NodeSocketStandard, enabled: bool, **op_args):
        props = layout.operator(cls.bl_idname, **op_args)
        props.socket = repr(socket)
        props.enabled = enabled

@auto_load.blender_operator
class SL_OT_set_bake_sockets_manager(SanctusOperator):
    bl_idname = 'sl.set_bake_sockets_manager'
    bl_label = 'Set Sanctus Bake Sockets'
    bl_description = 'Manage Bake Sockets on the active Node'

    @classmethod
    def node_has_sockets(cls, node: bt.Node) -> bool:
        return len(node.outputs)
    
    @classmethod
    def socket_is_exposed(cls, socket: bt.NodeSocket):
        return (
            socket.enabled
            and (not socket.hide or len(socket.links) > 0)
        )

    @classmethod
    def poll(cls, context):
        try:
            return (
                is_baking_context(context) 
                and context.active_node 
                and cls.node_has_sockets(context.active_node)
            )
        except:
            return False
    
    def invoke(self, context, event):
        print('invoke')
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        from . import baking
        layout = self.layout.column(align=True)
        node: bt.Node = context.active_node
        
        for s in [x for x in node.outputs.values() if self.socket_is_exposed(x)]:
            if baking.is_socket_valid(s):
                baking.draw_socket_enabled_ui(s, layout, text=s.name, toggle=1)
            else:
                layout.label(text=s.name)
    
    def execute(self, context: bt.Context):
        return {'FINISHED'} 


class SanctusBakeOp(SanctusOperator):

    @staticmethod
    def get_bake_settings(context: bt.Context):
        from . import baking
        return baking.TreeBakeSettings.get_bake_settings(context.space_data.edit_tree)


_bake_description_poll_failed: str = """Baking requirements not met:
- Cycles render engine used
- Active object available and selected
- Shader Editor Material on active object
- At least 1 Bake Socket available
"""

@auto_load.blender_operator
class SL_OT_bake(SanctusBakeOp):
    bl_idname = 'sl.bake'
    bl_label = 'Bake'

    @classmethod
    def description(cls, context, properties):
        if cls.poll(context):
            settings = cls.get_bake_settings(context)
            return f'Bake {len(settings.get_bake_sockets())} textures at {settings.get_resolution()}p'
        else:
            return _bake_description_poll_failed

    @classmethod
    def poll(cls, context):
        try:
            obj: bt.Object = context.object
            materials = [x.material for x in obj.material_slots.values() if x.material is not None]
            settings = cls.get_bake_settings(context)
            return (
                obj is not None
                and obj in context.selected_objects
                and len(materials)
                and settings.material in materials
                and len(settings.get_bake_sockets()) > 0
                and context.scene.render.engine == 'CYCLES'
            )
        except:
            return False
        
    def invoke(self, context: bt.Context, _event):
        from . import baking
        baking.set_wm_baking(context.window_manager, True)
        context.area.tag_redraw()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        return self.execute(context)
    
    def execute(self, context: bt.Context):
        from . import baking
        sd: bt.SpaceNodeEditor = context.space_data
        nt: bt.ShaderNodeTree = sd.edit_tree
        settings = baking.TreeBakeSettings.get_bake_settings(nt)
        try:
            start_time = time.perf_counter()
            images = settings.bake(context)
            settings.set_results(images, clear=True)
            end_time = time.perf_counter()

            self.report({'INFO'}, f'Done Baking {len(images)} image{"s" if len(images) != 1 else ""} in {round(end_time - start_time, 2)} seconds!')
        except:
            import traceback
            self.report({'ERROR'}, traceback.format_exc())
        finally:
            baking.set_wm_baking(context.window_manager, False)
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_popup_image(bt.Operator):
    bl_idname = 'sl.popup_image'
    bl_label = 'Show Image'
    bl_description = 'Open the image in a new Blender Window'

    image_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context: bt.Context):
        image = bpy.data.images.get(self.image_name, None)
        if image is None:
            self.report({'ERROR'}, f'Image with name "{self.image_name}" could not be found.')
            return {'CANCELLED'}
        wm = context.window_manager
        old_windows = list(wm.windows.values())
        bpy.ops.wm.window_new()
        new_window: bt.Window = next(x for x in wm.windows.values() if not x in old_windows)
        area = new_window.screen.areas[0]
        area.ui_type = 'IMAGE_EDITOR'
        s: bt.SpaceImageEditor = area.spaces[0]
        s.image = image
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_clear_bake_results(SanctusBakeOp):
    bl_idname = 'sl.clear_bake_results'
    bl_label = 'Clear Bake Results'
    bl_description = 'Remove Bake Results from this interface. Generated Images will not be removed from this action'

    @classmethod
    def poll(cls, context):
        try:
            return len(cls.get_bake_settings(context).results)
        except:
            return False
    
    def execute(self, context: bt.Context):
        settings = self.get_bake_settings(context)
        settings.clear_results()
        return {'FINISHED'}

@auto_load.blender_operator
class SL_OT_install_pillow(preview_ops.InstallPillow, SanctusOperator):
    bl_idname = 'sl.install_pillow'
    bl_label = 'Install Pillow'
    bl_description = 'Install the Pillow python library. Makes loading the addon much faster'
    
    @staticmethod
    def pillow_installed() -> bool:
        try:
            from PIL import Image
            return True
        except:
            return False
    
    @classmethod
    def draw_ui(cls, layout: bt.UILayout):
        row = layout.row()
        pil_installed = cls.pillow_installed()
        row.label(text='Install Pillow to improve addon loading times' if not pil_installed else 'Pillow Installed!')
        row.operator(cls.bl_idname, text=cls.bl_label if not pil_installed else 'Update Pillow')