import bpy, math, bmesh
from enum import Enum
from ... preferences import get_preferences
from ... addon.utility.screen import dpi_factor
from ... utility.base_modal_controls import Base_Modal_Controls
from ... utility.collections import view_layer_unhide, hide_all_objects_in_collection, hops_col_get
from ... ui_framework.master import Master
from ... ui_framework.utils.mods_list import get_mods_list
from ... ui_framework.flow_ui.flow import Flow_Menu, Flow_Form
from ... ui_framework.graphics.draw import render_text
from ... utils.toggle_view3d_panels import collapse_3D_view_panels
from ... utils.modal_frame_drawing import draw_modal_frame
from ... utils.cursor_warp import mouse_warp
from ... addon.utility import method_handler


class State(Enum):
    OFFSET = 0
    INSET = 1
    EXTRUDE = 2

    @classmethod
    def states(cls):
        return [cls.OFFSET, cls.INSET, cls.EXTRUDE]


class HOPS_OT_Sel_To_Bool_V3(bpy.types.Operator):
    bl_idname = "hops.sel_to_bool_v3"
    bl_label = "Selection To Boolean V3"
    bl_description = """Selection to Boolean
    Convert active face(s) to boolean
    Press H for help
    """
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            if context.active_object and context.active_object.type == 'MESH':
                return True
        return False


    def invoke(self, context, event):

        # Target
        self.obj = context.active_object
        self.boolean_mod = None

        # Boolean
        self.bool_obj = None
        self.solidify_mod = None
        self.bm = None
        self.bool_mesh_backup = None

        # Setup
        if not self.selection_valid(): return {'CANCELLED'}
        self.create_boolean(context)

        # State
        self.state = State.INSET
        self.apply_mods = False
        self.use_as_boolean = True
        self.og_xray = context.space_data.shading.show_xray
        self.og_shading = context.space_data.shading.type

        # Controls
        self.accumulation = 0
        self.offset_value = 0.035 if bpy.app.version >= (2, 90, 0) else -0.035
        self.inset_value = 0
        self.extrude_value = 0

        # Drawing
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        cell_color = get_preferences().color.Hops_UI_cell_background_color
        self.color = ( cell_color[0], cell_color[1], cell_color[2], 1)

        # Flow menu
        self.flow = Flow_Menu()
        self.setup_flow_menu(context)

        # Base Systems
        self.master = Master(context=context)
        self.master.only_use_fast_ui = True
        self.base_controls = Base_Modal_Controls(context, event)
        self.original_tool_shelf, self.original_n_panel = collapse_3D_view_panels()
        self.draw_handle_2D = bpy.types.SpaceView3D.draw_handler_add(self.safe_draw_2D, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    # --- Flow Menu --- #
    def setup_flow_menu(self, context):
        flow_data = [
            Flow_Form(text="TOOLS"  , font_size=18, tip_box="Pick a tool"),
            Flow_Form(text="OFFSET" , font_size=14, func=self.flow_func, pos_args=(State.OFFSET,) , tip_box="Adjust the offset."),
            Flow_Form(text="INSET"  , font_size=14, func=self.flow_func, pos_args=(State.INSET,)  , tip_box="Adjust the inset of the face."),
            Flow_Form(text="EXTRUDE", font_size=14, func=self.flow_func, pos_args=(State.EXTRUDE,), tip_box="Extrude the faces in.")]
        self.flow.setup_flow_data(flow_data)


    def flow_func(self, state):
        self.state = state
        self.set_viewport_shading()
        bpy.ops.hops.display_notification(info=f'Switched tool to: {state.name}')

    # --- Setup --- #
    def selection_valid(self):
        bm = bmesh.from_edit_mesh(self.obj.data)
        faces = [f for f in bm.faces if f.select]
        if len(faces) > 0: return True
        else: return False


    def create_boolean(self, context):

        # New mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = self.obj.data.copy()
        self.bool_obj = bpy.data.objects.new(mesh.name, mesh)
        self.bool_obj.hops.status = "BOOLSHAPE"

        # Collection
        col = hops_col_get(bpy.context)

        view_layer_unhide(col, enable=True)
        hide_all_objects_in_collection(coll=col)

        col.objects.link(self.bool_obj)

        # Solidify
        self.solidify_mod = self.bool_obj.modifiers.new('Solidify', type='SOLIDIFY')
        self.solidify_mod.use_even_offset = True
        self.solidify_mod.use_quality_normals = True
        self.solidify_mod.show_viewport = False

        # Boolean
        self.boolean_mod = self.obj.modifiers.new("HOPS Boolean", 'BOOLEAN')
        if hasattr(self.boolean_mod, 'solver'):
            self.boolean_mod.solver = 'FAST'
        self.boolean_mod.show_render = True
        self.boolean_mod.object = self.bool_obj
        self.boolean_mod.show_viewport = False
        self.simple_mod_sort()

        # Parent / Move / Display
        self.bool_obj.parent = self.obj
        self.bool_obj.matrix_world = self.obj.matrix_world
        self.bool_obj.display_type = 'WIRE'

        # Edit
        bpy.ops.object.select_all(action='DESELECT')
        self.bool_obj.select_set(True)
        context.view_layer.objects.active = self.bool_obj
        bpy.ops.object.mode_set(mode='EDIT')

        # Clean
        self.bm = bmesh.from_edit_mesh(self.bool_obj.data)
        verts = [v for v in self.bm.verts if not v.select]
        bmesh.ops.delete(self.bm, geom=verts, context='VERTS')
        faces = [f for f in self.bm.faces if not f.select]
        bmesh.ops.delete(self.bm, geom=faces, context='FACES')
        bmesh.update_edit_mesh(self.bool_obj.data)
        self.bool_obj.update_from_editmode()

        # Backup
        self.bool_mesh_backup = self.bool_obj.data.copy()


    def simple_mod_sort(self):
        '''Place the bool mod in the mod stack.'''

        moves = 0
        for mod in reversed(self.obj.modifiers):
            if mod.type == 'BEVEL': break
            moves += 1

        while moves != 0:
            moves -= 1
            bpy.ops.object.modifier_move_up(modifier=self.boolean_mod.name)

    # --- Controler -- #
    def modal(self, context, event):

        # --- Systems --- #
        self.master.receive_event(event=event)
        self.base_controls.update(context, event)
        mouse_warp(context, event)
        self.flow.run_updates(context, event, enable_tab_open=True)
        self.accumulation += self.base_controls.mouse
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        # --- Controls ---#
        if self.base_controls.pass_through:
            return {'PASS_THROUGH'}

        elif self.base_controls.cancel:
            self.shut_down(context)
            self.cancelled(context)
            return {'CANCELLED'}

        elif self.base_controls.confirm and self.state not in {State.OFFSET, State.INSET}:
            if self.flow.is_open == False:
                self.shut_down(context)
                self.confirmed(context)
                return {'FINISHED'}

        elif self.base_controls.scroll:
            self.set_viewport_shading()
            self.cycle_state(forward=bool(self.base_controls.scroll))

        # Cycle
        if event.type == 'X' and event.value == 'PRESS':
            self.set_viewport_shading()
            self.cycle_state(forward=event.shift)

        # Continue operations
        elif self.base_controls.confirm and self.state in {State.OFFSET, State.INSET}:
            if self.state == State.OFFSET:
                self.state = State.INSET
            elif self.state == State.INSET:
                self.state = State.EXTRUDE

        # Flip extrude
        elif event.type == 'F' and event.value == 'PRESS':
            self.extrude_value *= -1
            self.accumulation = self.extrude_value

        # Toggle Bool
        elif event.type == 'S' and event.value == 'PRESS':
            self.use_as_boolean = not self.use_as_boolean

            if self.use_as_boolean:
                self.boolean_mod.show_viewport = True
                self.boolean_mod.object = self.bool_obj
                self.bool_obj.display_type = 'WIRE'
            else:
                self.boolean_mod.show_viewport = False
                self.boolean_mod.object = None
                self.bool_obj.display_type = 'SOLID'

        # Apply mods on exit
        elif event.type == 'A' and event.value == 'PRESS':
            self.apply_mods = not self.apply_mods

        # --- Update --- #
        if event.type != 'TIMER' and self.flow.is_open == False:
            self.update_mesh(context, event)
            self.interface(context=context)

        context.area.tag_redraw()
        return {"RUNNING_MODAL"}


    def update_mesh(self, context, event):

        bmesh.ops.delete(self.bm, geom=self.bm.verts, context='VERTS')
        self.bm.from_mesh(self.bool_mesh_backup)

        if self.state == State.OFFSET:
            self.set_mod_visibility(on=False)
            self.offset_value = self.accumulation
            self.offset()
        elif self.state == State.INSET:
            self.set_mod_visibility(on=False)
            self.inset_value = self.accumulation
            self.offset()
            self.inset()
        elif self.state == State.EXTRUDE:
            self.set_mod_visibility(on=True)
            self.extrude_value = self.accumulation
            self.offset()
            self.inset()
            self.extrude()

        bmesh.update_edit_mesh(self.bool_obj.data)


    def offset(self):
        bpy.ops.transform.shrink_fatten(value=self.offset_value, use_even_offset=True)


    def inset(self):
        result = bmesh.ops.inset_region(
            self.bm,
            faces=self.bm.faces,
            use_boundary=True,
            use_even_offset=True,
            use_interpolate=True,
            use_relative_offset=False,
            use_edge_rail=True,
            thickness=self.inset_value,
            depth=0,
            use_outset=False)
        bmesh.ops.delete(self.bm, geom=result['faces'], context='FACES')


    def extrude(self):
        self.solidify_mod.thickness = self.extrude_value


    def interface(self, context):
        self.master.setup()
        #---  Fast UI ---#
        if self.master.should_build_fast_ui():
            help_items = {"GLOBAL" : [], "STANDARD" : []}
            help_items["GLOBAL"] = [
                ("M", "Toggle mods list"),
                ("H", "Toggle help"),
                ("~", "Toggle UI Display Type"),
                ("O", "Toggle viewport rendering"),
                ("Z", "Toggle Wireframe / Solid")]

            help_items["STANDARD"] = [
                ("A"     , "Apply modifiers"),
                ("S"     , "Toggle use as bool"),
                ("F"     , "Flip Extrude"),
                ("X"     , "Cycle Operation"),
                ("Scroll", "Cycle Operation"),
                ("TAB"   , "Open Flow Menu")]

            win_list = []
            if self.state == State.OFFSET:
                win_list.append("Mode: Offset")
                win_list.append(f"{self.offset_value:.3f}")
            elif self.state == State.INSET:
                win_list.append("Mode: Inset")
                win_list.append(f"{self.inset_value:.3f}")
            elif self.state == State.EXTRUDE:
                win_list.append("Mode: Extrude")
                win_list.append(f"{self.extrude_value:.3f}")

            win_list.append(f"Apply: {self.apply_mods}")

            self.master.receive_fast_ui(win_list=win_list, help_list=help_items, image="Booleans", mods_list=get_mods_list(mods=self.obj.modifiers))
        self.master.finished()

    # --- Utils --- #
    def set_viewport_shading(self):
        if self.state == State.OFFSET:
            bpy.context.space_data.shading.show_xray = False
        elif self.state == State.INSET:
            bpy.context.space_data.shading.show_xray = False
        elif self.state == State.EXTRUDE:
            bpy.context.space_data.shading.show_xray = True


    def set_mod_visibility(self, on=True):
        self.solidify_mod.show_viewport = on
        self.boolean_mod.show_viewport = on


    def cycle_state(self, forward=True):
        step = 1 if forward else -1
        types = State.states()
        index = types.index(self.state) + step
        self.state = types[index % len(types)]

    # --- Exit --- #
    def shut_down(self, context):
        collapse_3D_view_panels(self.original_tool_shelf, self.original_n_panel)
        self.flow.shut_down()
        self.master.run_fade()
        self.remove_shaders()
        context.space_data.shading.show_xray = self.og_xray
        context.space_data.shading.type = self.og_shading
        bpy.data.meshes.remove(self.bool_mesh_backup)


    def cancelled(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = self.bool_obj.data
        bpy.data.objects.remove(self.bool_obj)
        bpy.data.meshes.remove(mesh)

        bpy.ops.object.select_all(action='DESELECT')
        self.obj.select_set(True)
        context.view_layer.objects.active = self.obj
        bpy.ops.object.mode_set(mode='EDIT')

        self.obj.modifiers.remove(self.boolean_mod)


    def confirmed(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        self.obj.select_set(True)
        context.view_layer.objects.active = self.obj
        bpy.ops.object.mode_set(mode='EDIT')

        if self.boolean_mod.object == None:
            self.obj.modifiers.remove(self.boolean_mod)
            # Unlink
            for coll in self.bool_obj.users_collection:
                coll.objects.unlink(self.bool_obj)
            # Link
            coll = None
            if self.obj.users_collection: coll = self.obj.users_collection[0]
            else: coll = context.collection
            coll.objects.link(self.bool_obj)
            # Apply
            if self.apply_mods:
                bpy.ops.object.mode_set(mode='OBJECT')
                context.view_layer.objects.active = self.bool_obj
                bpy.ops.object.modifier_apply(modifier=self.solidify_mod.name)
                context.view_layer.objects.active = self.obj
                bpy.ops.object.mode_set(mode='EDIT')

        # Show bool in edit mode
        else:
            if hasattr(self.boolean_mod, 'show_in_editmode'):
                self.boolean_mod.show_in_editmode = True
            # Apply
            if self.apply_mods:
                bpy.ops.object.mode_set(mode='OBJECT')
                context.view_layer.objects.active = self.bool_obj
                bpy.ops.object.modifier_apply(modifier=self.solidify_mod.name)
                context.view_layer.objects.active = self.obj
                bpy.ops.object.modifier_apply(modifier=self.boolean_mod.name)

                # Remove bool object
                mesh = self.bool_obj.data
                bpy.data.objects.remove(self.bool_obj)
                bpy.data.meshes.remove(mesh)

                bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.object.mode_set(mode='OBJECT')

        # Select bool object
        if self.bool_obj:
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = self.bool_obj
            self.bool_obj.select_set(True)

    # --- Shaders --- #
    def remove_shaders(self):
        if self.draw_handle_2D:
            self.draw_handle_2D = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_2D, "WINDOW")


    def safe_draw_2D(self, context):
        method_handler(self.draw_shader_2D, arguments=(context,), identifier='Modal Shader 2D', exit_method=self.remove_shaders)


    def draw_shader_2D(self, context):
        '''Draw shader handle.'''

        self.flow.draw_2D()
        draw_modal_frame(context)

        factor = dpi_factor()
        up = 40 * factor
        right = 40 * factor
        font_size = 16
        text_pos = (self.mouse_pos[0] + up, self.mouse_pos[1] + right)

        if self.state == State.OFFSET:
            text = "Click to Inset"
            render_text(text=text, position=text_pos, size=font_size, color=self.color)

        elif self.state == State.INSET:
            text = "Click to Extrude"
            render_text(text=text, position=text_pos, size=font_size, color=self.color)

        elif self.state == State.EXTRUDE:
            text = "Click to Finish"
            render_text(text=text, position=text_pos, size=font_size, color=self.color)