from ..advans import *
from ..core.shader import calc_viewdir


@ti.data_oriented
class SSR:
    def __init__(self, res, norm, mtlid, mtltab, debug=False):
        self.res = tovector(res)
        self.img = ti.Vector.field(3, float, self.res)
        self.nsamples = ti.field(int, ())
        self.nsteps = ti.field(int, ())
        self.stepsize = ti.field(float, ())
        self.tolerance = ti.field(float, ())
        self.blurring = ti.field(int, ())
        self.norm = norm
        self.mtlid = mtlid
        self.mtltab = mtltab
        self.debug = debug

        @ti.materialize_callback
        def init_params():
            self.nsamples[None] = 32
            self.nsteps[None] = 32
            self.stepsize[None] = 2
            self.tolerance[None] = 15
            self.blurring[None] = 4

    @ti.kernel
    def apply(self, image: ti.template()):
        for i, j in self.img:
            if ti.static(self.debug):
                image[i, j] += self.img[i, j]
            else:
                rad = self.blurring[None]
                offs = rad // 2
                r = V(0., 0., 0.)
                for k, l in ti.ndrange(rad, rad):
                    r += self.img[i + k - offs, j + l - offs]
                image[i, j] += r / rad**2

    @ti.kernel
    def render(self, engine: ti.template(), image: ti.template()):
        for P in ti.grouped(image):
            if self.norm[P].norm_sqr() < eps:
                self.img[P] = 0
            else:
                self.render_at(engine, image, P)

    @ti.func
    def render_at(self, engine, image: ti.template(), P):
        normal = self.norm[P]
        mtlid = self.mtlid[P]

        p = P + engine.bias[None]
        vpos = V23(engine.from_viewport(p), engine.depth[P] / engine.maxdepth)
        pos = mapply_pos(engine.V2W[None], vpos)
        viewdir = calc_viewdir(engine, p)
        material = self.mtltab.get(mtlid)
        res = V(0., 0., 0.)

        tina.Input.spec_g_pars({
                'pos': pos,
                'color': V(1., 1., 1.),
                'normal': normal,
            })

        nsamples = self.nsamples[None]
        nsteps = self.nsteps[None]
        for i in range(nsamples):
            odir, wei = material.sample(viewdir, normal, 1)
            odir = -odir

            step = self.stepsize[None] / (
                    ti.sqrt(1 - odir.dot(viewdir)**2) * nsteps)
            vtol = self.tolerance[None] * (
                    mapply_pos(engine.W2V[None], pos - viewdir / nsteps
                    ).z - mapply_pos(engine.W2V[None], pos).z)

            ro = pos - (odir) * ti.random() * step
            for j in range(nsteps):
                ro -= odir * step
                vro = mapply_pos(engine.W2V[None], ro)
                if not all(-1 <= vro <= 1):
                    break
                D = engine.to_viewport(vro)
                depth = engine.depth[int(D)] / engine.maxdepth
                if vro.z - vtol < depth < vro.z:
                    res += bilerp(image, D) * wei
                    break

        tina.Input.clear_g_pars()

        self.img[P] = res / nsamples
