import taichi as ti
import numpy as np
import os
import time
import utils
from engine.mpm_solver import MPMSolver

write_to_disk = True
if write_to_disk:
    output_dir = "/home/blatny/repos/taichi_elements/demo/output/sim_1/"
    os.makedirs(os.path.dirname(output_dir), exist_ok=True)

ti.init(arch=ti.cpu)

gui = ti.GUI("Taichi Elements", res=512, background_color=0x112F41)

mpm = MPMSolver(res=(32, 32, 32), size=10)

mpm.add_ellipsoid(center=[2, 4, 3],
                  radius=1,
                  material=MPMSolver.material_snow,
                  velocity=[0, -10, 0])

mpm.set_gravity((0, -50, 0))

start_t = time.time()
for frame in range(3):
    print(f'frame: {frame}')
    t = time.time()
    mpm.step(4e-3)

    # colors = np.array([0x068587, 0xED553B, 0xEEEEF0, 0xFFFF00],      dtype=np.uint32)
    # particles = mpm.particle_info()
    # np_x = particles['position'] / 10.0
    # simple camera transform
    # screen_x = ((np_x[:, 0] + np_x[:, 2]) / 2**0.5) - 0.2
    # screen_y = (np_x[:, 1])
    # screen_pos = np.stack([screen_x, screen_y], axis=-1)
    # gui.circles(screen_pos, radius=1.5, color=colors[particles['material']])
    # gui.show(f'{output_dir}/{frame:06d}.png' if write_to_disk else None)

    if write_to_disk:
        mpm.write_particles(f'{output_dir}/{frame:05d}.npz')
    print(f'Frame total time {time.time() - t:.3f}')
    print(f'Total running time {time.time() - start_t:.3f}')

# Retrieve data
# f = 2
# data = np.load(f'{output_dir}{f:05d}.npz')
# Jp = data['Jp']
# print(Jp)
