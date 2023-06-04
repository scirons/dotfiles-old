import bpy
import bpy.types as bt

from . import auto_load
from . import dev_info
from . import operators

KEYMAPS: list[tuple[bt.KeyMap, bt.KeyMapItem, str]] = []

@auto_load.blender_register
class SanctusLibraryPreferences(bt.AddonPreferences):
    bl_idname = __package__

    use_static_panel: bpy.props.BoolProperty(
        name='Use N-Panel', 
        default=True,
        description='Toggle the panel on the right side of the 3D View'
    )

    developer_mode: bpy.props.BoolProperty(
        name='Developer Mode',
        default=False,
        description='Enables Developer Options. Do not touch!'
    )

    def draw(self, context: bt.Context):
        layout: bt.UILayout = self.layout

        operators.SL_OT_install_pillow.draw_ui(layout)

        layout.prop(self, 'use_static_panel')

        for km, kmi, kmn in KEYMAPS:
            main_split = layout.split(factor=1/3)
            main_split.label(text=f'{kmn}:')

            user_km = context.window_manager.keyconfigs.user.keymaps[km.name]
            user_kmi = user_km.keymap_items[kmi.idname]

            main_split.context_pointer_set('keymap', user_km)
            
            prop_split = main_split.split(factor=1/2)
            prop_split.prop(user_kmi, 'type', text='', event=True)

            mod_layout = prop_split.row(align=True)
            mod_layout.prop(user_kmi, 'shift_ui', text='Shift', toggle=1)
            mod_layout.prop(user_kmi, 'ctrl_ui', text='Ctrl', toggle=1)
            mod_layout.prop(user_kmi, 'alt_ui', text='Alt', toggle=1)
        
        if dev_info.DEVELOPER_MODE:
            layout.separator()
            layout.prop(self, 'developer_mode')

def get_preferences(context: bt.Context) -> SanctusLibraryPreferences:
    return context.preferences.addons[__package__].preferences