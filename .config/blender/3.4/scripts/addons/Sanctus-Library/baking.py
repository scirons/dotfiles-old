import bpy
import bpy.types as bt
from typing import Union

from . import auto_load
from . import operators
from . import library_manager
from . import img_tools
from .override_handler import OverrideHandler

SOCKET_ENABLED_PROP_NAME: str = 'sl_bake_enabled'
TREE_SETTINGS_PROP_NAME: str = 'sl_bake_settings'
WM_IS_BAKING_PROP_NAME: str = 'sl_is_baking'

INVALID_SOCKET_TYPES: list[bt.NodeSocket] = [
    bt.NodeSocketShader,
]

@auto_load.blender_register
class TreeBakeResult(bt.PropertyGroup):

    image: bpy.props.PointerProperty(
        type=bt.Image,
        name='Image'
    )

    def get_image(self) -> bt.Image:
        return self.image

    def set_image(self, image: bt.Image) -> None:
        self.image = image

    def draw(self, layout: bt.UILayout) -> None:
        image = self.get_image()
        if image is None:
            return
        split = layout.split(factor= 2/3)
        op = operators.SL_OT_popup_image
        row = split.row(align=True)
        op_display_settings = dict(
            emboss=False,
            text='',
        )
        if image.preview is None:
            op_display_settings['icon'] = 'FILE_IMAGE'
        else:
            op_display_settings['icon_value'] = image.preview.icon_id
        row.operator(op.bl_idname, **op_display_settings).image_name = image.name
        
        row.label(text=image.name)
        split.context_pointer_set('edit_image', image)
        props = split.operator('image.save_as', text='Save', icon='DISC')
        props.save_as_render = False
        props.relative_path = False

resolution_preset_items = {
    '512': (512, '512', '512 pixel resolution'),
    '1024': (1024, '1024', '1024 pixel resolution'),
    '2048': (2048, '2048', '2048 pixel resolution'),
    '4096': (4096, '4096', '4096 pixel resolution'),
    '8192': (8192, '8192', '8192 pixel resolution'),
    'CUSTOM': (0, 'Custom', 'Custom pixel resolution'),
}

@auto_load.blender_register
class TreeBakeSettings(bt.PropertyGroup):
    al_dependencies = [TreeBakeResult,]

    custom_resolution: bpy.props.IntProperty(
        name='Custom',
        default=512,
        min=16,
        max=8192,
        options=set(),
    )
    resolution_preset: bpy.props.EnumProperty(
        items=[(k, v[1], v[2]) for k, v in resolution_preset_items.items()],
        name='Resolution',
        default=0,
        options=set(),
    )

    def get_resolution(self):
        return self.custom_resolution if self.resolution_preset == 'CUSTOM' else resolution_preset_items[self.resolution_preset][0]

    def draw_resolution_props(self, layout: bt.UILayout):
        c = layout.column(align=True)
        c.use_property_split = True
        c.prop(self, 'resolution_preset')
        if self.resolution_preset == 'CUSTOM':
            c.prop(self, 'custom_resolution')

    samples: bpy.props.IntProperty(
        name='Samples',
        default=4,
        min=1,
        options=set(),
    )

    use_auto_margin: bpy.props.BoolProperty(
        name='Auto Margin',
        default=True,
        options=set(),
    )

    override_textures: bpy.props.BoolProperty(
        name='Override Textures',
        default=False,
        options=set(),
    )

    results: bpy.props.CollectionProperty(
        type=TreeBakeResult,
        name='Results'
    )

    def add_result(self, image: bt.Image, check_existing: bool = True) -> bool:
        if check_existing and image in [x.image for x in self.get_results()]:
            return 0
        a: TreeBakeResult = self.results.add()
        a.image = image
        return 1
    def remove_result(self, result: TreeBakeResult) -> bool:
        try:
            self.results.remove(next(i for i, x in enumerate(self.results) if x == result))
            return 1
        except StopIteration:
            print(f'Bake Result {result} is not part of the collection {self.results}')
        return 0

    @property
    def node_tree(self) -> bt.ShaderNodeTree:
        return self.id_data
    
    @property
    def material(self) -> Union[bt.Material, None]:
        try:
            return next(x for x in bpy.data.materials.values() if x.node_tree == self.node_tree)
        except StopIteration:
            return None

    def get_bake_sockets(self) -> list[bt.NodeSocketStandard]:
        result = []
        for n in self.node_tree.nodes.values():
            result += [s for s in n.inputs.values() + n.outputs.values() if is_socket_enabled(s)]
        return result
    
    def get_results(self, valid_only: bool = False) -> list[TreeBakeResult]:
        if valid_only:
            return [x for x in self.results if x.image is not None]
        else:
            return [x for x in self.results]
    
    def clean_up_results(self):
        results = reversed([x for x in self.get_results() if x.image is None])
        for res in results:
            self.remove_result(res)

    def set_results(self, images: list[bt.Image], clear: bool = True):
        if clear:
            self.results.clear()
        else:
            self.clean_up_results()
        for img in images:
            self.add_result(img, check_existing=True)
    
    def clear_results(self) -> None:
        self.results.clear()
    
    def draw(self, layout: bt.UILayout, context: bt.Context):
        layout.use_property_split = True
        row = layout.row(align=True)
        row.operator(operators.SL_OT_bake.bl_idname, text='Baking...' if get_wm_baking(context.window_manager) else 'Bake')
        row.prop(self, 'override_textures', text='', icon='DOCUMENTS')
        self.draw_resolution_props(layout)
        layout.prop(self, 'samples')
        layout.prop(self, 'use_auto_margin')
        if not self.use_auto_margin:
            layout.prop(context.scene.render.bake, 'margin')
        col = layout.column()
        bake_sockets = self.get_bake_sockets()
        node_layouts = {}
        for socket in bake_sockets:
            node_name = socket.node.name
            if not node_name in node_layouts.keys():
                node_layouts[node_name] = c = col.box().column()
                c.label(text=f'- {node_name}:')
            self.draw_socket(node_layouts[node_name], socket)
        
        if len(self.get_results(valid_only=True)):
            layout.separator()
            row = layout.row()
            row.label(text='Latest Results:')
            row.operator(operators.SL_OT_clear_bake_results.bl_idname, text='Clear')
            self.draw_results(layout)
    
    def draw_results(self, layout: bt.UILayout):
        col = layout.column()
        for res in self.get_results():
            res.draw(col)
    
    def draw_socket(self, layout: bt.UILayout, socket: bt.NodeSocket):
        r = layout.row(align=True)
        r.label(text=socket.name)
        operators.SL_OT_set_bake_socket.draw_ui(r, socket, False, text='', icon='REMOVE')

    def get_bake_name(self, socket: bt.NodeSocketStandard) -> str:
        return f'{self.material.name}_{socket.name}'

    def bake(self, context: bt.Context) -> list[bt.Image]:
        oh = OverrideHandler()
        oh.override(context.scene.render, 'engine', 'CYCLES')
        oh.override(context.scene.cycles, 'samples', self.samples)

        output_socket = get_shader_output_socket(self.node_tree)
        restore_socket = None
        if len(output_socket.links):
            restore_socket = output_socket.links[0].from_socket
        restore_active_node = self.node_tree.nodes.active
        image_node = self.node_tree.nodes.new('ShaderNodeTexImage')
        self.node_tree.nodes.active = image_node
        image_node.select = True

        results = []
        sockets = self.get_bake_sockets()
        for i, s in enumerate(sockets):
            print(f'Bake Job {i + 1}: {s.name}')
            results.append(self.bake_socket(s, image_node))

        self.node_tree.nodes.remove(image_node)
        if restore_socket is not None:
            self.node_tree.links.new(output_socket, restore_socket)
        self.node_tree.nodes.active = restore_active_node

        oh.restore()
        return results
    
    def bake_socket(
        self, 
        socket: bt.NodeSocketStandard, 
        image_node: bt.ShaderNodeTexImage,
        ) -> bt.Image:
        tex_name = self.get_bake_name(socket)
        
        remap = self.override_textures and (old_tex := bpy.data.images.get(tex_name, None)) is not None
        res = self.get_resolution()
        image = bpy.data.images.new(tex_name, width=res, height=res, alpha=True, float_buffer=True)
        
        if remap:
            old_tex.user_remap(image)
            bpy.data.images.remove(old_tex)
            image.name = tex_name

        image_node.image = image
        colorspace = get_socket_colorspace(socket)

        try:
            connect_socket_to_output(socket)
            bake_args = dict(
                type='EMIT',
                width=res,
                height=res,
                use_clear=True,
                use_selected_to_active=False,
                target='IMAGE_TEXTURES',
                save_mode='INTERNAL',
                use_cage=False
            )
            if self.use_auto_margin:
                bake_args['margin'] = int(res/32)
            bpy.ops.object.bake(**{
                k: v 
                for k, v 
                in bake_args.items() 
                if k in bpy.ops.object.bake.get_rna_type().properties.keys()
            }) # Check properties of the function. Ensures no errors will occur when using Blender 3.0
        except Exception as e:
            bpy.data.images.remove(image)
            raise e
        image.pixels.update()
        image.update()
        if colorspace == 'sRGB':
            img_tools.convert_linear_to_srgb(image)
            image.update()
        image.pack()
        image.colorspace_settings.name = colorspace
        image.preview_ensure()
        image.preview.reload()
        return image
    
    @staticmethod
    def get_bake_settings(node_tree: bt.ShaderNodeTree) -> 'TreeBakeSettings':
        return getattr(node_tree, TREE_SETTINGS_PROP_NAME)

def is_socket_enabled(socket: bt.NodeSocketStandard) -> bool:
    return getattr(socket, SOCKET_ENABLED_PROP_NAME) and is_socket_valid(socket)

def is_socket_valid(socket: bt.NodeSocketStandard):
    return (
        socket.is_output
        and not any(isinstance(socket, x) for x in INVALID_SOCKET_TYPES)
    )
        

def set_socket_enabled(socket: bt.NodeSocketStandard, enabled: bool) -> None:
    if is_socket_valid(socket):
        setattr(socket, SOCKET_ENABLED_PROP_NAME, enabled)

def draw_socket_enabled_ui(socket: bt.NodeSocketStandard, layout: bt.UILayout, **ui_args) -> None:
    layout.prop(socket, SOCKET_ENABLED_PROP_NAME, **ui_args)

def get_socket_colorspace(socket: bt.NodeSocketStandard) -> str:
    if 'color' in socket.bl_idname.lower():
        return 'sRGB'
    else:
        return 'Linear'

def get_shader_output_socket(node_tree: bt.ShaderNodeTree) -> Union[bt.NodeSocketStandard, None]:
    node = node_tree.get_output_node('CYCLES')
    if not node:
        return
    return node.inputs.get('Surface', None)

def connect_socket_to_output(socket: bt.NodeSocketStandard) -> bool:
    if not socket.is_output:
        return 0
    nt = socket.id_data
    output_socket = get_shader_output_socket(nt)
    if output_socket is None:
        return 0
    nt.links.new(output_socket, socket)
    return 1

def get_wm_baking(wm: bt.WindowManager) -> bool:
    return getattr(wm, WM_IS_BAKING_PROP_NAME)

def set_wm_baking(wm: bt.WindowManager, baking: bool) -> None:
    setattr(wm, WM_IS_BAKING_PROP_NAME, baking)

@auto_load.blender_register
def register_socket_properties(register: bool):
    clss = bt.NodeSocketStandard
    if register:
        setattr(
            clss, 
            SOCKET_ENABLED_PROP_NAME, bpy.props.BoolProperty(
                name='Sanctus Baking Enabled',
                default=False,
                description='Enabled sockets will be included in the baking routine of the Sanctus Library'
            ))
    else:
        delattr(clss, SOCKET_ENABLED_PROP_NAME)

@auto_load.blender_register
def register_tree_properties(register: bool):
    clss = bt.ShaderNodeTree
    if register:
        setattr(
            clss,
            TREE_SETTINGS_PROP_NAME,
            bpy.props.PointerProperty(
                type=TreeBakeSettings,
                name='Sanctus Bake Settings',
                description='Bake Manager for the current ShaderNodeTree'
            )
        )
    else:
        delattr(clss, TREE_SETTINGS_PROP_NAME)


@auto_load.blender_register
def register_wm_properties(register: bool):
    clss = bt.WindowManager
    if register:
        setattr(
            clss,
            WM_IS_BAKING_PROP_NAME,
            bpy.props.BoolProperty(
                name='Is Baking',
                default=False
            )
        )

@auto_load.register_draw_function(bt.NODE_MT_context_menu)
def draw_node_context_menu_ui(self: bt.Menu, context: bt.Context):
    op = operators.SL_OT_set_bake_sockets_manager
    if not op.poll(context):
        return
    l = self.layout
    l.operator_context = 'INVOKE_DEFAULT'
    l.operator(op.bl_idname, icon_value = library_manager.LIBRARY['icons']['icon'].icon)
