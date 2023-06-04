import bpy
from ... preferences import get_preferences


class HOPS_PT_dice_options(bpy.types.Panel):
    bl_label = "Dice Options"
    bl_category = "HardOps"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        preference = get_preferences().property
        
        self.layout.prop(preference, 'dice_version', text='Dice Version')
        self.layout.separator()
        self.layout.prop(preference, 'dice_method', text='Method')
        if preference.dice_version == 'V1':
            self.layout.prop(preference, 'dice_adjust', text='Adjust')
        self.layout.prop(preference, 'smart_apply_dice', text='Pre-Apply')
        self.layout.prop(preference, 'dice_show_mesh_wire', text='Fade mesh wire')
        self.layout.prop(preference, 'dice_wire_type', text='Display Type')

