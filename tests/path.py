import taichi as ti
import numpy as np
import tina

ti.init(ti.gpu)

scene = tina.PTScene(smoothing=True, texturing=True)
#scene.lighting.skybox = tina.Atomsphere()

#material = tina.Phong(color=[0.25, 0.5, 0.5])
#scene.add_object(tina.PrimitiveMesh.sphere(), tina.Glass())
roughness = tina.Param(float)
scene.add_object(tina.MeshModel('assets/cube.obj'), tina.PBR(metallic=1.0, roughness=roughness))
#scene.add_object(tina.PrimitiveMesh.sphere(), tina.Mirror())
#scene.add_object(tina.MeshModel('assets/bunny.obj'), tina.Glass())
#scene.add_object(tina.MeshModel('assets/monkey.obj'), tina.Mirror())
#scene.add_object(tina.MeshModel('assets/cube.obj'), tina.Classic())
#scene.add_object(tina.MeshTransform(tina.MeshModel('assets/cube.obj'), tina.translate([0, -1.2, 0]) @ tina.scale([2, 0.05, 2])), tina.Lambert())

scene.add_object(tina.MeshTransform(tina.MeshModel('assets/plane.obj'),
        tina.translate([0, 0, 4]) @ tina.eularXYZ([ti.pi / 2, 0, 0])), tina.Emission())

gui = ti.GUI('path', scene.res)
roughness.make_slider(gui, 'roughness', 0, 1, 0.01)

scene.update()
while gui.running:
    if scene.input(gui):
        scene.clear()
    scene.render(nsteps=6)
    gui.set_image(scene.img)
    gui.show()

ti.imwrite(scene.img, 'output.png')
