from ..advans import *
from ..util.stack import Stack


@ti.data_oriented
class PathEngine:
    def __init__(self, scene, lighting, mtltab, res=512):
        if isinstance(res, int): res = res, res
        self.res = ti.Vector(res)
        self.skybox = texture_as_field('assets/skybox.jpg')

        self.ro = ti.Vector.field(3, float, self.res)
        self.rd = ti.Vector.field(3, float, self.res)
        self.rc = ti.Vector.field(3, float, self.res)
        self.rl = ti.Vector.field(3, float, self.res)

        #self.rays = ti.root.dense(ti.ij, self.res)
        #self.rays.place(self.ro)
        #self.rays.place(self.rd)
        #self.rays.place(self.rc)

        self.img = ti.Vector.field(3, float, self.res)
        self.cnt = ti.field(int, self.res)

        self.scene = scene
        self.lighting = lighting
        self.mtltab = mtltab
        self.stack = Stack()

        self.W2V = ti.Matrix.field(4, 4, float, ())
        self.V2W = ti.Matrix.field(4, 4, float, ())

        @ti.materialize_callback
        @ti.kernel
        def init_engine():
            self.W2V[None] = ti.Matrix.identity(float, 4)
            self.W2V[None][2, 2] = -1
            self.V2W[None] = ti.Matrix.identity(float, 4)
            self.V2W[None][2, 2] = -1

    def clear_image(self):
        self.img.fill(0)
        self.cnt.fill(0)

    @ti.kernel
    def _get_image(self, out: ti.ext_arr()):
        for I in ti.grouped(self.img):
            val = lerp((I // 8).sum() % 2, V(.4, .4, .4), V(.9, .9, .9))
            if self.cnt[I] != 0:
                val = self.img[I] / self.cnt[I]
            val = film_tonemap(val)
            for k in ti.static(range(3)):
                out[I, k] = val[k]

    def get_image(self):
        img = np.zeros((*self.res, 3), dtype=np.float32)
        self._get_image(img)
        return img

    @ti.kernel
    def load_rays(self):
        for I in ti.grouped(ti.ndrange(*self.res)):
            bias = ti.Vector([ti.random(), ti.random()])
            uv = (I + bias) / self.res * 2 - 1
            # TODO: support customizing camera
            ro = mapply_pos(self.V2W[None], V(uv.x, uv.y, -1.0))
            ro1 = mapply_pos(self.V2W[None], V(uv.x, uv.y, +1.0))
            rd = (ro1 - ro).normalized()
            rc = ti.Vector([1.0, 1.0, 1.0])
            rl = ti.Vector([0.0, 0.0, 0.0])
            self.ro[I] = ro
            self.rd[I] = rd
            self.rc[I] = rc
            self.rl[I] = rl

    @ti.func
    def background(self, rd):
        if ti.static(hasattr(self, 'skybox')):
            return ce_untonemap(sample_cube(self.skybox, rd))
        else:
            return 0.0

    @ti.kernel
    def step_rays(self):
        for I, stack in ti.smart(self.stack.ndrange(self.res)):
            ro = self.ro[I]
            rd = self.rd[I]
            rc = self.rc[I]
            rl = self.rl[I]
            if not Vall(rc < eps):
                ro, rd, rc, rl = self.transmit(stack, ro, rd, rc, rl)
                self.ro[I] = ro
                self.rd[I] = rd
                self.rc[I] = rc
                self.rl[I] = rl

    @ti.kernel
    def update_image(self):
        for I in ti.grouped(ti.ndrange(*self.res)):
            rc = self.rc[I]
            rl = self.rl[I]
            if not Vall(rc < eps):
                continue
            self.img[I] += rl
            self.cnt[I] += 1

    def set_camera(self, view, proj):
        W2V = proj @ view
        V2W = np.linalg.inv(W2V)
        self.W2V.from_numpy(np.array(W2V, dtype=np.float32))
        self.V2W.from_numpy(np.array(V2W, dtype=np.float32))

    @ti.func
    def transmit(self, stack, ro, rd, rc, rl):
        near, ind, uv = self.scene.hit(stack, ro, rd)
        if ind == -1:
            # no hit
            rl += rc * self.background(rd)
            rc *= 0
        else:
            # hit object
            ro += near * rd
            nrm, tex = self.scene.geom.calc_geometry(near, ind, uv, ro, rd)
            if nrm.dot(rd) > 0:
                nrm = -nrm
            ro += nrm * eps * 8

            tina.Input.spec_g_pars({
                'pos': ro,
                'color': V(1., 1., 1.),
                'normal': nrm,
                'texcoord': tex,
            })

            mtlid = self.scene.geom.get_material_id(ind)
            material = self.mtltab.get(mtlid)

            li_clr = V(0., 0., 0.)
            for li_ind in range(self.lighting.get_nlights()):
                # cast shadow ray to lights
                new_rd, li_wei, li_dis = self.lighting.redirect(ro, li_ind)
                li_wei *= max(0, new_rd.dot(nrm))
                if Vall(li_wei <= 0):
                    continue
                occ_near, occ_ind, occ_uv = self.scene.hit(stack, ro, new_rd)
                if occ_near < li_dis:  # shadow occlusion
                    continue
                li_wei *= material.brdf(nrm, -rd, new_rd)
                li_clr += li_wei

            # sample indirect light
            rd, ir_wei = material.sample(-rd, nrm)

            tina.Input.clear_g_pars()

            rl += rc * li_clr
            rc *= ir_wei

        return ro, rd, rc, rl
