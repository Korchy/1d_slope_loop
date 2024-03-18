# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_slope_loop

import bmesh
import bpy
from bpy.props import EnumProperty, FloatProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Slope Loop",
    "description": "Modifies selected loop to create uniform slope",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Slope Loop",
    "doc_url": "https://github.com/Korchy/1d_slope_loop",
    "tracker_url": "https://github.com/Korchy/1d_slope_loop",
    "category": "All"
}


# MAIN CLASS

class SlopeLoop:

    @classmethod
    def make_slope_loop(cls, context, ob, mode, value):
        print('make slope', mode, value)
        return

        # Make slope from selected loop
        ob = ob if ob else context.active_object
        # edit/object mode
        mode = ob.mode
        if ob.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # get data loop from source mesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # source vertices
        src_vertices = [vert for vert in bm.verts if vert.select]
        if src_vertices:
            top_vert = max([vert for vert in src_vertices], key=lambda vert: vert.co.z)
            first_vert = next((vert for vert in src_vertices
                               if len(vert.link_edges) == 1 and vert != top_vert), None)
            selection_loop_sorted = cls.vertices_loop_sorted(
                bmesh_vertices_list=src_vertices,
                bmesh_first_vertex=first_vert
            )

        # save changed data to stairs mesh
        bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @staticmethod
    def vertices_loop_sorted(bmesh_vertices_list, bmesh_first_vertex):
        # return list with vertices sorted by following each other in the loop
        vertices_sorted = []
        if bmesh_vertices_list and bmesh_first_vertex:
            vertex = bmesh_first_vertex
            _l = len(bmesh_vertices_list)
            i = 0
            while vertex is not None:
                vertices_sorted.append(vertex)
                edge = next((_edge for _edge in vertex.link_edges
                             if _edge.other_vert(vertex) not in vertices_sorted), None)
                vertex = edge.other_vert(vertex) if edge else None
                # alarm break
                i += 1
                if i > _l:
                    print('_points_sorted() err exit')
                    break
        # return sorted sequence
        return vertices_sorted

    @staticmethod
    def ui(layout, context):
        # ui panel
        op = layout.operator(
            operator='slope_loop.make_slope',
            icon='IPO'
        )
        op.mode = context.scene.slope_loop_prop_mode
        op.value = context.scene.slope_loop_prop_value
        # props
        layout.prop(
            data=context.scene,
            property='slope_loop_prop_mode',
            expand=True
        )
        layout.prop(
            data=context.scene,
            property='slope_loop_prop_value',
            text=''
        )


# OPERATORS

class SlopeLoop_OT_make_slope(Operator):
    bl_idname = 'slope_loop.make_slope'
    bl_label = 'Make Slope'
    bl_options = {'REGISTER', 'UNDO'}

    value = FloatProperty(
        name='Value',
        default=10.0,
        min=0.0
    )

    mode = EnumProperty(
        name='Mode',
        items=[
            ('Degrees', 'Degrees', 'Degrees', '', 0),
            ('Permilles', 'Permilles', 'Permilles', '', 1),
            ('Percents', 'Percents', 'Percents', '', 2)
        ],
        default='Percents',
        description='Value mode'
    )

    def execute(self, context):
        SlopeLoop.make_slope_loop(
            context=context,
            ob=context.active_object,
            mode=self.mode,
            value=self.value
        )
        return {'FINISHED'}


# PANELS

class SlopeLoop_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Slope Loop"
    bl_category = '1D'

    def draw(self, context):
        SlopeLoop.ui(
            layout=self.layout,
            context=context
        )


# REGISTER

def register(ui=True):
    Scene.slope_loop_prop_value = FloatProperty(
        name='Value',
        default=10,
        min=0.0
    )
    Scene.slope_loop_prop_mode = EnumProperty(
        name='Mode',
        items=[
            ('Degrees', 'Degrees', 'Degrees', '', 0),
            ('Permilles', 'Permilles', 'Permilles', '', 1),
            ('Percents', 'Percents', 'Percents', '', 2)
        ],
        default='Percents',
        description='Value mode'
    )
    register_class(SlopeLoop_OT_make_slope)
    if ui:
        register_class(SlopeLoop_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(SlopeLoop_PT_panel)
    unregister_class(SlopeLoop_OT_make_slope)
    del Scene.slope_loop_prop_mode
    del Scene.slope_loop_prop_value


if __name__ == "__main__":
    register()
