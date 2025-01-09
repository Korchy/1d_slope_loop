# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_slope_loop

import bmesh
import bpy
import math
from mathutils import Vector
from bpy.props import EnumProperty, FloatProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Slope Loop",
    "description": "Modifies selected loop to create uniform slope",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 1, 3),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Slope Loop",
    "doc_url": "https://github.com/Korchy/1d_slope_loop",
    "tracker_url": "https://github.com/Korchy/1d_slope_loop",
    "category": "All"
}


# MAIN CLASS

class SlopeLoop:

    # 'FULL_SLOPE' for setting desired slope value from first to last point
    # 'EACH_SLOPE' for setting desired slope value for each edge of the loop
    _result_mode = 'EACH_SLOPE'

    @classmethod
    def make_slope_loop(cls, context, ob, slope_mode, value, op):
        # Make slope from selected loop
        ob = ob if ob else context.active_object
        # edit/object mode
        mode = ob.mode
        if ob.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # selection mode
        select_mode = 'VERT' if context.tool_settings.mesh_select_mode[0] \
            else ('EDGE' if context.tool_settings.mesh_select_mode[1] else None)
        # get data loop from source mesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # source vertices
        selected_vertices = [vert for vert in bm.verts if vert.select]
        if selected_vertices:
            # if selected only one edge - only print info to INFO output
            selected_edges = [edge for edge in bm.edges if edge.select]
            if len(selected_edges) == 1:
                # selected only one edge - print to INFO
                cls._info_angle_between_two_vertices(
                    v1=selected_edges[0].verts[0],
                    v2=selected_edges[0].verts[1],
                    mode=slope_mode,
                    op=op
                )
            elif len(selected_edges) > 1:
                # create slope - move all vertices starting from active vertically by slope value
                # find active vertex
                active_vertex = None
                if bm.select_history.active:
                    if select_mode == 'VERT':
                        # active vertex
                        active_vertex = bm.select_history.active
                    elif select_mode == 'EDGE':
                        # start vertex of active edge
                        active_edge = bm.select_history.active
                        active_vertex = active_edge.verts[0] \
                            if len([e for e in active_edge.verts[0].link_edges if e.select]) == 1 \
                            else active_edge.verts[1]
                if active_vertex:
                    # get sorted vertices loop starting from active vertex
                    vertices_loop = cls._vertices_loop_sorted(
                        bmesh_vertices_list=selected_vertices,
                        bmesh_first_vertex=active_vertex
                    )
                    if vertices_loop:
                        # get angle in radians by slope mode and value
                        radians = cls._mode_to_radians(value=value, mode=slope_mode)
                        if cls._result_mode == 'FULL_SLOPE':
                            # creates full slope (from first to last point) have the desired slope value
                            for vertex in vertices_loop[1:]:
                                # count height difference between first point and current point
                                diff = cls._slope_points_height_diff(
                                    v1=active_vertex,
                                    v2=vertex,
                                    radians=radians
                                )
                                # apply height difference for vertex
                                vertex.co.z = active_vertex.co.z + diff
                        elif cls._result_mode == 'EACH_SLOPE':
                            # each point should have the desired slope value
                            # split loop to vertices pairs
                            vertex_chunks = list(cls._chunks(
                                lst=vertices_loop,
                                n=2,
                                offset=1
                            ))[:-1]
                            for chunk in vertex_chunks:
                                # get height difference between current point and next point
                                diff = cls._slope_points_height_diff(
                                    v1=chunk[0],
                                    v2=chunk[1],
                                    radians=radians
                                )
                                # apply height difference for each next point
                                chunk[1].co.z = chunk[0].co.z + diff
                        # save changed data to mesh
                        bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @classmethod
    def q_slope_loop(cls, context, ob, op):
        # Make q-slope from selected loop
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
        selected_vertices = [vert for vert in bm.verts if vert.select]
        if selected_vertices:
            # if selected only 2 vertices - only print info to INFO output
            if len(selected_vertices) == 2:
                # selected only two vertices - print to INFO
                cls._info_angle_between_two_vertices(
                    v1=selected_vertices[0],
                    v2=selected_vertices[1],
                    mode=context.scene.slope_loop_prop_mode,
                    op=op
                )
            elif len(selected_vertices) > 2:
                # to enable multi-select - form list of selected loops, which needs to be processed by QSlope
                loops = cls._vertices_loops_sorted(vertices_list=selected_vertices)
                # process each loop of vertices
                for loop in loops:
                    # check to reverse loop, to guarantee that the first vertex is upper than the last
                    if loop[0].co.z < loop[-1].co.z:
                        loop.reverse()
                    # get loop length
                    #   calculating with real length - not valid. Why???
                    #   better way - calculating through projection on XY plane (Paul)
                    loop_proj_length = sum(
                        [(Vector((chunk[1].co.x, chunk[1].co.y)) - Vector((chunk[0].co.x, chunk[0].co.y))).length
                         for chunk in cls._chunks(lst=loop, n=2, offset=1) if len(chunk) > 1]
                    )
                    # vertical diff between first and last vertices
                    diff = (loop[0].co - loop[-1].co).z
                    # get angle by loop_length and diff
                    # maybe error in calculating math.assin ?
                    # radians = round(math.asin(diff / loop_length), 4)
                    # better way - calculating with atan by projection on XY plane
                    radians = round(math.atan(diff / loop_proj_length), 4)
                    # output radians to INFO in 'Make Slope' format
                    op.report(
                        type={'INFO'},
                        message='QSlope angle: '
                                + str(round(cls._slope_to_mode(radians=radians, mode=context.scene.slope_loop_prop_mode), 4))
                                + ' ' + context.scene.slope_loop_prop_mode
                    )
                    # split loop to vertices pairs
                    vertex_chunks = list(cls._chunks(
                        lst=loop,
                        n=2,
                        offset=1
                    ))[:-1]
                    for chunk in vertex_chunks:
                        # get height difference between current point and next point
                        vertex_diff = cls._slope_points_height_diff(
                            v1=chunk[0],
                            v2=chunk[1],
                            radians=radians
                        )
                        # apply height difference for each next point
                        chunk[1].co.z = chunk[0].co.z - vertex_diff  # "-" because we always go from top to bottom
                # save changed data to mesh
                bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @classmethod
    def align_neighbour(cls, context, ob):
        # align neighbour vertices of selected loop
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
        # source vertices - selected, exclude first and last
        selected_vertices = [vert for vert in bm.verts
                             if vert.select and len([lnk_edge for lnk_edge in vert.link_edges if lnk_edge.select]) > 1
                             ]
        for vertex in selected_vertices:
            vertex_edges = [edge for edge in vertex.link_edges if not edge.select]
            for edge in vertex_edges:
                moving_vert = edge.other_vert(vertex)
                if moving_vert.hide is False:   # don't move hidden vertices
                    moving_vert.co.z = vertex.co.z
        # save changed data to mesh
        bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @staticmethod
    def _vertices_loop_sorted(bmesh_vertices_list, bmesh_first_vertex):
        # return list with vertices sorted by following each other in the loop, starting from first_vertex
        vertices_sorted = []
        if bmesh_vertices_list and bmesh_first_vertex:
            vertex = bmesh_first_vertex
            _l = len(bmesh_vertices_list)
            i = 0
            while vertex is not None:
                vertices_sorted.append(vertex)
                edge = next((_edge for _edge in vertex.link_edges
                             if _edge.select and _edge.other_vert(vertex) not in vertices_sorted), None)
                vertex = edge.other_vert(vertex) if edge else None
                # alarm break
                i += 1
                if i > _l:
                    print('_points_sorted() err exit')
                    break
        # return sorted sequence
        return vertices_sorted

    @staticmethod
    def _vertices_loops_sorted(vertices_list):
        # return list of selected loops
        # in each loop vertices sorted by following each other starting from first_vertex
        loops = []
        if vertices_list:
            # overflow error checking
            _i = 0
            _l = len(vertices_list)
            # get first boundary vertex (selected and has only one linked selected edge)
            boundary_vertex = next((vertex for vertex in vertices_list
                                    if vertex.select and len([e for e in vertex.link_edges if e.select]) == 1), None)
            while boundary_vertex is not None:
                loop = [boundary_vertex, ]
                # add loop to loops list
                loops.append(loop)
                vertices_list.remove(boundary_vertex)
                _i += 1
                # alarm break
                if _i > _l:
                    print('_points_sorted() err exit')
                    break
                # from loop starting from this boundary vertex
                next_vertex = next((_edge.other_vert(boundary_vertex) for _edge in boundary_vertex.link_edges
                                    if _edge.select and _edge.other_vert(boundary_vertex) not in loop), None)
                while next_vertex is not None:
                    # add vertex to the current loop
                    loop.append(next_vertex)
                    vertices_list.remove(next_vertex)
                    _i += 1
                    # alarm break
                    if _i > _l:
                        print('_points_sorted() err exit')
                        break
                    # continue to get next vertices for this loop
                    next_vertex = next((_edge.other_vert(next_vertex) for _edge in next_vertex.link_edges
                                        if _edge.select and _edge.other_vert(next_vertex) not in loop), None)
                # try to get next boundary vertex for finding and processing next loop
                boundary_vertex = next((vertex for vertex in vertices_list
                                        if vertex.select and len([e for e in vertex.link_edges if e.select]) == 1), None)
        # remove loops with just 1 or 2 vertices
        loops = [loop for loop in loops if len(loop) > 2]
        # return loops list
        return loops

    @staticmethod
    def _get_slope_by_verts(v1, v2):
        # get slope angle by two vertices (BMVerts) in radians
        v = v1.co - v2.co   # vector from v2 to v1
        v_z = Vector((v.x, v.y, 0.0))   # projection on XY plane
        return v.angle(v_z)

    @staticmethod
    def _slope_points_height_diff(v1, v2, radians):
        # count height difference between two points by angle
        v = v2.co - v1.co   # vector from v1 to v2
        v1 = Vector((v.x, v.y, 0.0))
        return v1.length / round(math.tan(math.radians(90) - radians), 4)

    @classmethod
    def _slope_to_mode(cls, radians, mode):
        # convert angle from radians to mode (percents, permilles, degrees)
        if mode == 'Degrees':
            return cls._rad2deg(radians=radians)
        elif mode == 'Permilles':
            return cls._rad2pm(radians=radians)
        elif mode == 'Percents':
            return cls._rad2pc(radians=radians)

    @classmethod
    def _mode_to_radians(cls, value, mode):
        # convert angle from mode (percents, permilles, degrees) to radians
        if mode == 'Degrees':
            return cls._deg2rad(degrees=value)
        elif mode == 'Permilles':
            return cls._pm2rad(permilles=value)
        elif mode == 'Percents':
            return cls._pc2rad(percents=value)

    @staticmethod
    def _rad2deg(radians):
        # convert radians to degrees
        return math.degrees(radians)

    @staticmethod
    def _deg2rad(degrees):
        # convert degrees to radians
        return math.radians(degrees)

    @staticmethod
    def _rad2pm(radians):
        # convert radians to permilles
        return round(math.tan(radians), 4) * 1000.0

    @staticmethod
    def _pm2rad(permilles):
        # convert permilles to radians
        return round(math.atan(permilles / 1000.0), 4)

    @staticmethod
    def _rad2pc(radians):
        # convert radians to percents
        return round(math.tan(radians), 4) * 100

    @staticmethod
    def _pc2rad(percents):
        # convert percents to radians
        return round(math.atan(percents / 100), 4)

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
        row = layout.row()
        row.prop(
            data=context.scene,
            property='slope_loop_prop_mode',
            expand=True
        )
        layout.prop(
            data=context.scene,
            property='slope_loop_prop_value',
            text=''
        )
        layout.operator(
            operator='slope_loop.align_neighbour',
            icon='GRIP'
        )
        layout.operator(
            operator='slope_loop.q_slope',
            icon='IPO_EASE_IN_OUT'
        )

    @staticmethod
    def _chunks(lst, n, offset=0):
        for i in range(0, len(lst), n - offset):
            yield lst[i:i + n]

    @classmethod
    def _info_angle_between_two_vertices(cls, v1, v2, mode, op):
        # print to INFO angle between two vertices
        edge_slope = cls._get_slope_by_verts(
            v1=v1,
            v2=v2
        )
        op.report(
            type={'INFO'},
            message='Active edge angle: '
                    + str(round(cls._slope_to_mode(radians=edge_slope, mode=mode), 4))
                    + ' ' + mode
        )


# OPERATORS

class SlopeLoop_OT_make_slope(Operator):
    bl_idname = 'slope_loop.make_slope'
    bl_label = 'Make Slope'
    bl_description = 'Reshape the selected loop to the desired slope starting from the active vertex'
    bl_options = {'REGISTER', 'UNDO'}

    value = FloatProperty(
        name='Value',
        default=10.0
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
            slope_mode=self.mode,
            value=self.value,
            op=self
        )
        return {'FINISHED'}


class SlopeLoop_OT_q_slope(Operator):
    bl_idname = 'slope_loop.q_slope'
    bl_label = 'QSlope'
    bl_description = 'QSlope'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        SlopeLoop.q_slope_loop(
            context=context,
            ob=context.active_object,
            op=self
        )
        return {'FINISHED'}


class SlopeLoop_OT_align_neighbour(Operator):
    bl_idname = 'slope_loop.align_neighbour'
    bl_label = 'Align Neighbour'
    bl_description = 'Inherit the height of vertices directly connected to the interior of the selected loop.'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        SlopeLoop.align_neighbour(
            context=context,
            ob=context.active_object
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
        default=10
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
    register_class(SlopeLoop_OT_q_slope)
    register_class(SlopeLoop_OT_align_neighbour)
    if ui:
        register_class(SlopeLoop_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(SlopeLoop_PT_panel)
    unregister_class(SlopeLoop_OT_align_neighbour)
    unregister_class(SlopeLoop_OT_q_slope)
    unregister_class(SlopeLoop_OT_make_slope)
    del Scene.slope_loop_prop_mode
    del Scene.slope_loop_prop_value


if __name__ == "__main__":
    register()
