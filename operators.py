import threading, struct, os

import bpy
from .mpm_solver import MPMSolver
import taichi as ti
import numpy as np

from . import node_types


def get_cache_folder(simulation_node):
    particles_socket = simulation_node.outputs['Simulation Data']
    if particles_socket.is_linked:
        for link in particles_socket.links:
            disk_cache_node = link.to_node
            folder = disk_cache_node.inputs['Folder'].get_value()
            folder = bpy.path.abspath(folder)
            return folder


def get_simulation_nodes(operator, node_tree):
    simulation_nodes = []
    for node in node_tree.nodes:
        if node.bl_idname == 'elements_simulation_node':
            simulation_nodes.append(node)
    if len(simulation_nodes) != 1:
        operator.report(
            {'WARNING'},
            'The node tree must not contain more than 1 "Simulation" node.'
        )
        return
    else:
        return simulation_nodes[0]


def print_simulation_info(simulation_class, offset):
    offset += ' '
    for i in dir(simulation_class):
        v = getattr(simulation_class, i, None)
        if v and i[0] != '_':
            if type(v) in (node_types.List, node_types.Merge):
                print(offset, i, type(v))
                offset += ' '
                for e in v.elements:
                    print(offset, i, type(e))
                    print_simulation_info(e, offset)
            elif type(v) in node_types.elements_types:
                print(offset, i, type(v))
                for key in dir(v):
                    if key[0] != '_':
                        print(offset, '  ', key, '=', getattr(v, key))
                print_simulation_info(v, offset)


class ELEMENTS_OT_SimulateParticles(bpy.types.Operator):
    bl_idname = "elements.simulate_particles"
    bl_label = "Simulate"

    thread = None

    def run_simulation(self):
        for frame in range(100):
            self.sim.step(1e-2)
            np_x, np_v, np_material = self.sim.particle_info()
            print(np_x)

            if not os.path.exists(self.cache_folder):
                os.makedirs(self.cache_folder)

            particles_file_path = os.path.join(
                self.cache_folder,
                'particles_{0:0>6}.bin'.format(frame)
            )
            data = bytearray()
            particles_count = len(np_x)
            data.extend(struct.pack('I', particles_count))
            print(particles_count)
            for particle_index in range(particles_count):
                data.extend(struct.pack('3f', *np_x[particle_index]))
                data.extend(struct.pack('3f', *np_v[particle_index]))

            with open(particles_file_path, 'wb') as file:
                file.write(data)

        self.thread = None


    def invoke(self, context, event):
        context.scene.elements_nodes.clear()
        self.node_tree = context.space_data.node_tree
        simulation_node = get_simulation_nodes(self, self.node_tree)
        if not simulation_node:
            return {'FINISHED'}

        simulation_node.get_class()
        self.cache_folder = get_cache_folder(simulation_node)

        for i, j in context.scene.elements_nodes.items():
            print(i, j)

        simulation_class = context.scene.elements_nodes[simulation_node.name]

        print(79 * '=')
        print('simulation_class', type(simulation_class))
        print_simulation_info(simulation_class, '')
        print(79 * '=')
        
        # TODO: list is not implemented
        
        res = simulation_class.solver.resolution
        size = simulation_class.solver.size
        ti.reset()
        print(f"Creating simulation of res {res}, size {size}")
        sim = MPMSolver((res, res, res), size=size)

        hub = simulation_class.hubs
        assert len(hub.forces) == 1, "Only one gravity supported"
        force = hub.forces[0].output_folder
        gravity = force[0], force[1], force[2]
        print('g =', gravity)
        sim.set_gravity(gravity)
        
        emitters = hub.emitters
        for emitter in emitters:
            source_geometry = emitter.source_geometry
            if not source_geometry:
                continue
            obj = emitter.source_geometry.bpy_object
            # Note: rotation is not supported
            center_x = obj.matrix_world[0][3]
            center_y = obj.matrix_world[1][3]
            center_z = obj.matrix_world[2][3]
            scale_x = obj.matrix_world[0][0]
            scale_y = obj.matrix_world[1][1]
            scale_z = obj.matrix_world[2][2]
            material = emitter.material.material_type
            if material == 'WATER':
                taichi_material = MPMSolver.material_water
            elif material == 'ELASTIC':
                taichi_material = MPMSolver.material_elastic
            elif material == 'SNOW':
                taichi_material = MPMSolver.material_snow
            else:
                assert False, material
            lower = (center_x - scale_x, center_y - scale_y, center_z - scale_z)
            cube_size = (2 * scale_x, 2 * scale_y, 2 * scale_z)
            print(lower)
            print(cube_size)
            sim.add_cube(lower_corner=lower, cube_size=cube_size, material=taichi_material)

        context.scene.frame_set(0)
        self.size = size
        self.sim = sim
        self.thread = threading.Thread(
                target=self.run_simulation, 
                args=()
        )
        self.thread.start()
        return {'RUNNING_MODAL'}


operator_classes = [
    ELEMENTS_OT_SimulateParticles,
]


def register():
    for operator_class in operator_classes:
        bpy.utils.register_class(operator_class)


def unregister():
    for operator_class in reversed(operator_classes):
        bpy.utils.unregister_class(operator_class)
