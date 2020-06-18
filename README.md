Taichi THREE
============

Taichi THREE is an extension library of the [Taichi Programming Language](https://github.com/taichi-dev/taichi), that helps rendering your 3D scenes into nice-looking 2D images to display in GUI.


[Camera](https://github.com/taichi-dev/taichi_three/raw/master/examples/camera.png)


Installation
------------

Install Taichi THREE with `pip`:

```bash
# Python 3.6/3.7/3.8 (64-bit)
pip install taichi_three
```

This should also install its dependencies `taichi` and `taichi_glsl` as well.


How to play
-----------

First, import Taichi and Taichi THREE:
```py
import taichi as ti
import taichi_three as t3

ti.init(ti.gpu)
```

---

Then, create a scene using:
```py
scene = t3.Scene()
```

NOTE: scene creation should be put before any kernel invocation or host access,
i.e. before materialization, so that `Scene.__init__` could define its internal
tensors without an error.
TL;DR: Put this line as forward as possible! Ideally right below `ti.init()`.

---

After that, define your data tensors, physics info, and pass them to `scene`.

```py
pos = ti.Vector(3, ti.f32, n)
radius = ti.var(ti.f32, n)

scene.add_ball(pos, radius)      # pass the tensors directly, not pos[...]!
scene.set_light_dir([1, 2, -2])  # scene will do normalization for you :)
scene.set_camera([0, 0, -1])     # always set camera before rendering.
```

---

Finally, create a GUI. And here goes the main loop:

```py
gui = ti.GUI('Ball')

while gui.running:

    ... # Update ball pos, vel, etc.

    scene.render()  # update image according to the given tensors in add_ball
    gui.set_image(scene.img)  # to display the result image
    gui.show()
```

Example
-------

Running the following example code should gives you an moving ball:
```py
import taichi as ti
import taichi_three as t3
from math import cos, sin
from time import time
ti.init(ti.opengl)

scene = t3.Scene()
pos = ti.Vector(3, ti.f32, 1)
radius = ti.var(ti.f32, 1)

scene.add_ball(pos, radius)      # provide data tensor
scene.set_light_dir([1, 2, -2])  # parallel light direction
scene.set_camera([0, 0, -1])     # camera position, look towards Z+

radius[0] = 0.5

gui = ti.GUI('Ball')
while gui.running:
    pos[0] = [0.3 * sin(time()), 0.3 * cos(time()), 0]
    scene.render()
    gui.set_image(scene.img)
    gui.show()
```
