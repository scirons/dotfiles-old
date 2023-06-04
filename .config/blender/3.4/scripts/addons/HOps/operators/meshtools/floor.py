import bpy, mathutils, math, bmesh
from math import cos, sin
from mathutils import Vector, Matrix, Quaternion, geometry


DESC = """Floor \nMake sure to have and active face selected"""


class HOPS_OT_FLOOR(bpy.types.Operator):
    bl_idname = "hops.floor"
    bl_label = "Hops Floor"
    bl_description = DESC
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.active_object:
            if context.active_object.type == 'MESH':
                if context.active_object.mode == 'EDIT':
                    return True
        return False


    def execute(self, context):
        objs = context.selected_editable_objects[:]
        for obj in objs:
            solver_v3(obj)
        return {'FINISHED'}


def solver_v3(obj):

    obj.update_from_editmode()
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    face = bm.faces.active
    
    # Validate
    if not face:
        bpy.ops.hops.display_notification(info="No Active Face")
        return

    # convert everything into world space
    center = obj.matrix_world @ face.calc_center_bounds()
    verts_world = [obj.matrix_world @ v.co for v in face.verts]
    normal = face.normal
    normal = obj.matrix_world.inverted().transposed() @ normal
    normal.normalize() # if matrix has scale, the normal won't be unit length

    # flip normal for object to be above floor
    face_matrix = normal.to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    face_matrix.translation = center

    #2d version of vert coordinates in face space
    verts2d = [(face_matrix.inverted() @ v).to_2d() for v in verts_world]
    fit_angle = geometry.box_fit_2d(verts2d)
    face_matrix = face_matrix @ Matrix.Rotation(-fit_angle, 4,'Z')


    #  there is no scale to worry about
    loc = face_matrix.translation
    pivot = Matrix.Translation(loc)
    transform = face_matrix.copy()
    transform.translation = 0, 0, 0

    # undo transfromation of face plane to place it onto a floor
    transform_inv = transform.inverted()

    obj.matrix_world = pivot @ transform_inv @ pivot.inverted() @ obj.matrix_world

    # project object onto floor
    obj.matrix_world.translation -= Vector((0, 0, loc.z))

