import bpy, bmesh
from ... preferences import get_preferences


DESC = """Set edge length of selected edges;

Warning: Connected loops will interfere with eachother!
"""

class HOPS_OT_EDGE_LEN(bpy.types.Operator):
    bl_idname = 'hops.edge_len'
    bl_label = 'Set Edge Length'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    bl_description = DESC


    edge_length : bpy.props.FloatProperty(
    name='Length',
    description='Edge length',
    default=0.1,
    min=0
    )

    flip_dir : bpy.props.BoolProperty(
    name='Flip',
    description='Scale non-disconnected edges from different vert',
    default=False,
    )



    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        self.layout.prop(self, 'edge_length')
        self.layout.prop(self, 'flip_dir')

    def execute (self, context):
        self.edit_objects = [o for o in context.objects_in_mode_unique_data]
        self.notify = lambda val, sub='': bpy.ops.hops.display_notification(info=val, subtext=sub) if get_preferences().ui.Hops_extra_info else lambda val, sub=None: None

        counter = 0
        for obj in self.edit_objects:
            bm = bmesh.from_edit_mesh(obj.data)
            selected_edges = [(edge, edge.verts[0].co - edge.verts[1].co) for edge in bm.edges if edge.select]

            if not selected_edges: continue
            affected_verts = set()

            for edge, direction in selected_edges:
                linked_edges = [e for v in edge.verts for e in v.link_edges if e.select and e is not edge]

                if not linked_edges:
                    center = (edge.verts[0].co + edge.verts[1].co) / 2

                    for v in edge.verts:
                        d = v.co - center
                        d.length = self.edge_length /2
                        v.co = center + d

                    continue

                v1, v2 = edge.verts

                if self.flip_dir:
                    v2, v1 = edge.verts

                if v1 not in affected_verts:
                    direction.length = self.edge_length
                    v1.co = v2.co + direction

                elif v2 not in affected_verts:
                    direction.negate()
                    direction.length = self.edge_length
                    v2.co = v1.co + direction


                affected_verts.update(edge.verts)

            bmesh.update_edit_mesh(obj.data)
            counter += 1

        if not counter: self.notify('CANCELLED', 'No edges selected')

        self.notify(f'Edge Length: {self.edge_length:.3}', f'{get_redo_last(context)} for redo')

        return {'FINISHED'}



def get_redo_last(context):
    kmi = context.window_manager.keyconfigs.user.keymaps['Screen'].keymap_items.get('screen.redo_last', '')

    if not kmi: 'Redo Last is not bound; Click on the box'

    s = ''

    if kmi.ctrl: s += 'CTRL'
    if kmi.shift: s+= 'SHIFT'
    if kmi.alt: s+= 'ALT'
    if kmi.oskey: s+= 'OSKEY'
    if kmi.key_modifier != 'NONE': s += kmi.key_modifier


    s+= kmi.type

    return s

