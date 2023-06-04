import bpy
import bpy.types as bt
from typing import Union

from . import auto_load
from . import library_manager as lm
from . import operators as ops
from . import developer_tools
from . import preferences
from . import baking

SANCTUS_CONTEXT_PROP_NAME: str = 'sl_context_switch'

@auto_load.blender_register
class SL_PT_togglable_ui(bt.Panel):
    bl_idname = 'SL_PT_togglable_ui'
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'
    bl_label = 'Sanctus Library'
    bl_category = 'Sanctus'

    @classmethod
    def poll(cls, context):
        try:
            return preferences.get_preferences(context).use_static_panel
        except:
            return False
    
    def draw(self, context): #function has to be defined to make this class registerable
        pass

    def draw_header_preset(self, context: bt.Context):
        self.layout.operator(ops.SL_OT_reload_library.bl_idname, text='', icon='FILE_REFRESH')

class SanctusPanelSection:
    context: str = 'test'
    name: str = 'Test'
    description: str = 'description of test'

    @classmethod
    def poll(cls, context: bt.Context) -> bool:
        return True

    @classmethod
    def get_library(cls) -> lm.Library:
        return lm.LIBRARY[cls.context]

    @staticmethod
    def get_item(context: bt.Context, lib: lm.Library) -> Union[lm.Library, lm.LibraryItem]:
        return  lib[getattr(context.window_manager, lib.get_enum_attr_name())]
    
    @classmethod
    def draw_ui(cls, layout: bt.UILayout, context: bt.Context) -> None:
        wm = context.window_manager
        library = cls.get_library()
        layout.prop(wm, library.get_enum_attr_name(), text='')
        active_sublib = cls.get_item(context, library)

        active_item = None
        if active_sublib:
            r = layout.row(align=True)
            r.scale_y = 8.0
            ops.SL_OT_switch_library_item.draw_ui(r, active_sublib, backwards=True)
            r.template_icon_view(wm, active_sublib.get_enum_attr_name(), show_labels=True, scale=1.0, scale_popup=4.0)
            ops.SL_OT_switch_library_item.draw_ui(r, active_sublib, backwards=False)
            active_item = cls.get_item(context, active_sublib)
            if active_item is not None:
                cls.draw_operator(context, layout, library_path=active_item.library_path)
        
        cls.draw_documentation_buttons(layout)

        if preferences.get_preferences(context).developer_mode:
            cls.draw_developer_tools(layout, context)
    
    @classmethod
    def draw_operator(cls, context: bt.Context, layout: bt.UILayout, **op_props) -> None:
        raise NotImplementedError()
    
    @classmethod
    def draw_documentation_buttons(cls, layout: bt.UILayout) -> None:
        r = layout.row(align=True)
        r.alignment = 'RIGHT'
        r.scale_y = 2.0
        r.scale_x = 2.0
        r.operator(ops.SL_OT_open_documentation.bl_idname, text='', icon_value=lm.LIBRARY['icons']['icon'].icon)
        r.operator(ops.SL_OT_open_video_guide.bl_idname, text='', icon='URL')
    
    @classmethod
    def draw_developer_tools(cls, layout: bt.UILayout, context: bt.Context):
        lib = cls.get_library()
        sublib = cls.get_item(context, lib)
        active_item = cls.get_item(context, sublib)

        if active_item is not None:
            developer_mode = preferences.get_preferences(context).developer_mode
            if developer_mode or not active_item.is_locked():
                props = layout.operator(ops.SL_OT_set_meta_data.bl_idname)
                props.library_path = active_item.library_path
            if developer_mode:
                developer_tools.draw_ui(layout, active_item)

class SanctusMaterialSection(SanctusPanelSection):
    context: str = 'materials'
    name: str = 'Materials'
    description: str = ''

    @classmethod
    def draw_operator(cls, context: bt.Context, layout: bt.UILayout, **op_props) -> None:
        c = layout.column(align=True)
        lib_path = op_props['library_path']
        c.operator(ops.SL_OT_apply_material.bl_idname).library_path = lib_path
        c.operator(ops.SL_OT_import_material.bl_idname).library_path = lib_path

class SanctusGNAssetsSection(SanctusPanelSection):
    context: str = 'gntools'
    name: str = 'GN Assets'
    description: str = ''

    @classmethod
    def draw_operator(cls, context: bt.Context, layout: bt.UILayout, **op_props) -> None:
        c = layout.column(align=True)
        lib_path = op_props['library_path']
        c.operator(ops.SL_OT_apply_geometry_nodes.bl_idname).library_path = lib_path
        c.operator(ops.SL_OT_add_geometry_nodes_object.bl_idname).library_path = lib_path

class SanctusNodeSection(SanctusPanelSection):
    context: str = 'tools'
    name: str = 'Node Tools'
    description: str = ''

    @classmethod
    def draw_operator(cls, context: bt.Context, layout: bt.UILayout, **op_props) -> None:
        props = layout.operator(ops.SL_OT_add_group_node.bl_idname)
        props.library_path = op_props['library_path']

@auto_load.blender_register
class SL_PT_View3DPanel(bt.Panel):
    al_dependencies: list[type] = [SL_PT_togglable_ui]
    bl_idname = 'SL_PT_View3DPanel'
    bl_label = 'Viewport Panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id: str = SL_PT_togglable_ui.bl_idname

    def draw(self, context: bt.Context):
        l = self.layout
        SanctusContextSwitch.draw_ui(l, context)

@auto_load.blender_register
class SL_PT_NodeEditor(bt.Panel):
    bl_idname: str = 'SL_PT_NodeEditor'
    bl_label: str = 'Node Panel'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Sanctus'

    @classmethod
    def poll(cls, context: bt.Context):
        return True
    
    def draw(self, context: bt.Context):
        SanctusNodeSection.draw_ui(self.layout, context)

@auto_load.blender_register
class SanctusContextSwitch(bt.PropertyGroup):

    contexts: list[SanctusPanelSection] = [
        SanctusMaterialSection,
        SanctusGNAssetsSection
    ]
    
    context_items = [(x.context, x.name, x.description) for x in contexts]
    context: bpy.props.EnumProperty(
        name='Context',
        items=context_items,
        description='Controls the active Sanctus context'
    )

    @classmethod
    def get(cls, window_manager: bt.WindowManager) -> 'SanctusContextSwitch':
        return getattr(window_manager, SANCTUS_CONTEXT_PROP_NAME)
    
    @classmethod
    def get_section_from_context(cls, window_manager: bt.WindowManager) -> SanctusPanelSection:
        context_str = cls.get(window_manager).context
        return next(x for x in cls.contexts if x.context == context_str)

    @classmethod
    def draw_ui(cls, layout: bt.UILayout, context: bt.Context):
        wm = context.window_manager
        layout.prop(cls.get(wm), 'context', expand=True)
        cls.get_section_from_context(wm).draw_ui(layout, context)


@auto_load.blender_register
class SL_PT_baking(bt.Panel):
    bl_idname = 'SL_PT_baking'
    bl_label = 'Sanctus Baking'
    bl_description = 'Bake Settings for the Sanctus Library'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Sanctus'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        try:
            return context.space_data.edit_tree in [mat.node_tree for mat in bpy.data.materials.values()]
        except:
            return False
    
    def draw(self, context: bt.Context):
        sd: bt.SpaceNodeEditor = context.space_data
        baking.TreeBakeSettings.get_bake_settings(sd.edit_tree).draw(self.layout, context)

@auto_load.blender_register
def register_keymaps(register: bool):

    kc = bpy.context.window_manager.keyconfigs.addon

    def add_shortcut(
        keymap_name, 
        operator: Union[bt.Operator, str], 
        name: str, space_type: str, 
        region_type: str, 
        type: str, 
        value: str, 
        **keymap_item_settings 
        ) -> bt.KeyMapItem:

        if isinstance(operator, bt.Operator):
            operator = operator.bl_idname
        km = kc.keymaps.new(name, space_type=space_type, region_type=region_type)
        kmi = km.keymap_items.new(operator, type, value, **keymap_item_settings)
        preferences.KEYMAPS.append((km, kmi, keymap_name))
        return kmi

    if kc:
        if register:
            kmi = add_shortcut('Floating Panel Shortcut', 'wm.call_panel', '3D View', 'VIEW_3D', 'WINDOW', 'S', 'PRESS', ctrl=True, alt=True)
            kmi.properties.name = SL_PT_View3DPanel.bl_idname
        else:
            for km, kmi, _kmn in preferences.KEYMAPS:
                km.keymap_items.remove(kmi)
            preferences.KEYMAPS.clear()

@auto_load.blender_register
def register_context_switch(register: bool):
    clss = bt.WindowManager
    if register:
        setattr(
            clss,
            SANCTUS_CONTEXT_PROP_NAME,
            bpy.props.PointerProperty(
                type=SanctusContextSwitch,
                name='Sanctus Context Switch',
            )
        )
    else:
        delattr(clss, SANCTUS_CONTEXT_PROP_NAME)