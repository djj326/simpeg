from __future__ import division, print_function
import unittest
import numpy as np
from SimPEG import Mesh, Maps, SolverLU, Tests
from SimPEG import EM
from scipy.interpolate import interp1d

try:
    from pymatsolver import PardisoSolver
    Solver = PardisoSolver
except ImportError:
    Solver = SolverLU

plotIt = False

testDeriv = True
testAdjoint = False

TOL = 1e-4
EPS = 1e-20
np.random.seed(4)


def setUp_TDEM(prbtype='b', rxcomp='bz'):

    cs = 5.
    ncx = 8
    ncy = 8
    ncz = 8
    npad = 4

    mesh = Mesh.TensorMesh(
        [
            [(cs, npad, -1.3), (cs, ncx), (cs, npad, 1.3)],
            [(cs, npad, -1.3), (cs, ncy), (cs, npad, 1.3)],
            [(cs, npad, -1.3), (cs, ncz), (cs, npad, 1.3)]
        ], 'CCC'
    )

    active = mesh.vectorCCz < 0.
    activeMap = Maps.InjectActiveCells(mesh, active, np.log(1e-8), nC=mesh.nCz)
    mapping = Maps.ExpMap(mesh) * Maps.SurjectVertical1D(mesh) * activeMap

    rxOffset = 15.

    prb = getattr(EM.TDEM, 'Problem3D_{}'.format(prbtype))(mesh, sigmaMap=mapping)

    prb.timeSteps = [(1e-3, 5), (1e-4, 5), (5e-5, 10), (5e-5, 10), (1e-4, 10)]
    out = EM.Utils.VTEMFun(prb.times, 0.00595, 0.006, 100)
    wavefun = interp1d(prb.times, out)
    t0 = 0.006
    waveform = EM.TDEM.Src.RawWaveform(offTime=t0, waveFct=wavefun)
    timerx = t0 + np.logspace(-5, -3, 20)
    rx = getattr(EM.TDEM.Rx, 'Point_{}'.format(rxcomp[:-1]))(
        np.array([[rxOffset, 0., 0.]]), timerx, rxcomp[-1])
    src = EM.TDEM.Src.MagDipole(
        [rx], waveform=waveform, loc=np.array([0., 0., 0.])
    )

    survey = EM.TDEM.Survey([src])

    prb.Solver = Solver

    m = np.log(1e-1)*np.ones(prb.sigmaMap.nP)
    # + 1e-2*np.random.randn(prb.sigmaMap.nP)

    prb.pair(survey)
    mesh = mesh

    return prb, m, mesh


class TDEM_DerivTests(unittest.TestCase):

# ====== TEST A ========== #

    def AderivTest(self, prbtype):
        prb, m0, mesh = setUp_TDEM(prbtype)
        tInd = 2
        if prbtype == 'b':
            nu = mesh.nF
        elif prbtype == 'e':
            nu = mesh.nE
        v = np.random.rand(nu)

        def AderivFun(m):
            prb.model = m
            A = prb.getAdiag(tInd)
            Av = A*v
            prb.model = m0

            def ADeriv_dm(dm):
                return prb.getAdiagDeriv(tInd, v, dm)

            return Av, ADeriv_dm

        print('\n Testing ADeriv {}'.format(prbtype))
        Tests.checkDerivative(AderivFun, m0, plotIt=False, num=4, eps=EPS)

    def A_adjointTest(self, prbtype):
        prb, m0, mesh = setUp_TDEM(prbtype)
        tInd = 2

        print('\n Testing A_adjoint')
        m = np.random.rand(prb.sigmaMap.nP)
        if prbtype == 'b':
            nu = prb.mesh.nF
        elif prbtype == 'e':
            nu = prb.mesh.nE

        v = np.random.rand(nu)
        u = np.random.rand(nu)
        prb.model = m0

        tInd = 2  # not actually used
        V1 = v.dot(prb.getAdiagDeriv(tInd, u, m))
        V2 = m.dot(prb.getAdiagDeriv(tInd, u, v, adjoint=True))
        passed = (
            np.abs(V1-V2) < TOL * (np.abs(V1) + np.abs(V2))/2. or
            np.abs(V1-V2) < EPS
        )
        print('AdjointTest {prbtype} {v1} {v2} {passed}'.format(
            prbtype=prbtype, v1=V1, v2=V2, passed=passed))
        self.assertTrue(passed)

    def test_Aderiv_b(self):
        self.AderivTest(prbtype='b')

    def test_Aderiv_e(self):
        self.AderivTest(prbtype='e')

    def test_Aadjoint_b(self):
        self.A_adjointTest(prbtype='b')

    def test_Aadjoint_e(self):
        self.A_adjointTest(prbtype='e')

# ====== TEST Fields Deriv Pieces ========== #

    def test_eDeriv_m_adjoint(self):
        prb, m0, mesh = setUp_TDEM()
        tInd = 0

        v = np.random.rand(mesh.nF)

        print('\n Testing eDeriv_m Adjoint')

        prb, m0, mesh = setUp_TDEM()
        f = prb.fields(m0)

        m = np.random.rand(prb.sigmaMap.nP)
        e = np.random.randn(prb.mesh.nE)
        V1 = e.dot(f._eDeriv_m(1, prb.survey.srcList[0], m))
        V2 = m.dot(f._eDeriv_m(1, prb.survey.srcList[0], e, adjoint=True))
        tol = TOL * (np.abs(V1) + np.abs(V2)) / 2.
        passed = np.abs(V1-V2) < tol

        print('     {v1}, {v2}, {diff}, {tol}, {passed}'.format(
              v1=V1, v2=V2, diff=np.abs(V1-V2), tol=tol, passed=passed))
        self.assertTrue(passed)

    def test_eDeriv_u_adjoint(self):
        print('\n Testing eDeriv_u Adjoint')

        prb, m0, mesh = setUp_TDEM()
        f = prb.fields(m0)

        b = np.random.rand(prb.mesh.nF)
        e = np.random.randn(prb.mesh.nE)
        V1 = e.dot(f._eDeriv_u(1, prb.survey.srcList[0], b))
        V2 = b.dot(f._eDeriv_u(1, prb.survey.srcList[0], e, adjoint=True))
        tol = TOL * (np.abs(V1) + np.abs(V2)) / 2.
        passed = np.abs(V1-V2) < tol

        print(
            '     {v1}, {v2}, {diff}, {tol}, {passed}'.format(
                v1=V1, v2=V2, diff=np.abs(V1-V2), tol=tol, passed=passed
            )
        )
        self.assertTrue(passed)


# ====== TEST Jvec ========== #

    if testDeriv:

        def JvecTest(self, prbtype, rxcomp):
            prb, m, mesh = setUp_TDEM(prbtype, rxcomp)

            def derChk(m):
                return [prb.survey.dpred(m), lambda mx: prb.Jvec(m, mx)]
            print('\ntest_Jvec_{}_{}'.format(prbtype, rxcomp))
            Tests.checkDerivative(derChk, m, plotIt=False, num=2, dx=m*2,
                                  eps=1e-20)

        def test_Jvec_b_bx(self):
            self.JvecTest(prbtype='b', rxcomp='bx')

        def test_Jvec_b_bz(self):
            self.JvecTest(prbtype='b', rxcomp='bz')

        def test_Jvec_b_dbxdt(self):
            self.JvecTest(prbtype='b', rxcomp='dbdtx')

        def test_Jvec_b_dbzdt(self):
            self.JvecTest(prbtype='b', rxcomp='dbdtx')

        def test_Jvec_b_ey(self):
            self.JvecTest(prbtype='b', rxcomp='ey')

        def test_Jvec_e_ey(self):
            self.JvecTest(prbtype='e', rxcomp='ey')

        def test_Jvec_e_dbdtx(self):
            self.JvecTest(prbtype='e', rxcomp='dbdtx')

        def test_Jvec_e_dbdtz(self):
            self.JvecTest(prbtype='e', rxcomp='dbdtz')

        def test_Jvec_h_hx(self):
            self.JvecTest(prbtype='h', rxcomp='hx')

        def test_Jvec_h_hz(self):
            self.JvecTest(prbtype='h', rxcomp='hz')

        def test_Jvec_h_dhdtx(self):
            self.JvecTest(prbtype='h', rxcomp='dhdtx')

        def test_Jvec_h_dhdtz(self):
            self.JvecTest(prbtype='h', rxcomp='dhdtz')

        def test_Jvec_h_jy(self):
            self.JvecTest(prbtype='h', rxcomp='jy')

        def test_Jvec_j_jy(self):
            self.JvecTest(prbtype='j', rxcomp='jy')

        def test_Jvec_j_dhdtx(self):
            self.JvecTest(prbtype='j', rxcomp='dhdtx')

        def test_Jvec_j_dhdtz(self):
            self.JvecTest(prbtype='j', rxcomp='dhdtz')


# ====== TEST Jtvec ========== #

    if testAdjoint:

        def JvecVsJtvecTest(self, prbtype='b', rxcomp='bz'):

            print(
                '\nAdjoint Testing Jvec, Jtvec problem {}, data {}'.format(
                    prbtype, rxcomp
                )
            )

            prb, m0, mesh = setUp_TDEM(prbtype, rxcomp)
            m = np.random.rand(prb.sigmaMap.nP)
            d = np.random.randn(prb.survey.nD)
            V1 = d.dot(prb.Jvec(m0, m))
            V2 = m.dot(prb.Jtvec(m0, d))
            tol = TOL * (np.abs(V1) + np.abs(V2)) / 2.
            passed = (np.abs(V1-V2) < tol or np.abs(V1-V2) < EPS)

            print('     {v1}, {v2}, {diff}, {tol}, {passed}'.format(
                v1=V1, v2=V2, diff=np.abs(V1-V2), tol=tol, passed=passed))
            self.assertTrue(passed)

        def test_Jvec_adjoint_b_bx(self):
            self.JvecVsJtvecTest(prbtype='b', rxcomp='bx')

        def test_Jvec_adjoint_b_bz(self):
            self.JvecVsJtvecTest(prbtype='b', rxcomp='bz')

        def test_Jvec_adjoint_b_dbxdt(self):
            self.JvecVsJtvecTest(prbtype='b', rxcomp='dbdtx')

        def test_Jvec_adjoint_b_dbzdt(self):
            self.JvecVsJtvecTest(prbtype='b', rxcomp='dbdtz')

        def test_Jvec_adjoint_b_ey(self):
            self.JvecVsJtvecTest(prbtype='b', rxcomp='ey')

        def test_Jvec_adjoint_e_ey(self):
            self.JvecVsJtvecTest(prbtype='e', rxcomp='ey')

        def test_Jvec_adjoint_e_dbdtx(self):
            self.JvecVsJtvecTest(prbtype='e', rxcomp='dbdtx')

        def test_Jvec_adjoint_e_dbdtz(self):
            self.JvecVsJtvecTest(prbtype='e', rxcomp='dbdtz')

        def test_Jvec_adjoint_h_jy(self):
            self.JvecVsJtvecTest(prbtype='h', rxcomp='jy')

        def test_Jvec_adjoint_h_dhdtx(self):
            self.JvecVsJtvecTest(prbtype='h', rxcomp='dhdtx')

        def test_Jvec_adjoint_h_dhdtz(self):
            self.JvecVsJtvecTest(prbtype='h', rxcomp='dhdtz')

        def test_Jvec_adjoint_h_hx(self):
            self.JvecVsJtvecTest(prbtype='h', rxcomp='hx')

        def test_Jvec_adjoint_h_hz(self):
            self.JvecVsJtvecTest(prbtype='h', rxcomp='hz')

        def test_Jvec_adjoint_j_jy(self):
            self.JvecVsJtvecTest(prbtype='j', rxcomp='jy')

        def test_Jvec_adjoint_j_dhdtx(self):
            self.JvecVsJtvecTest(prbtype='j', rxcomp='dhdtx')

        def test_Jvec_adjoint_j_dhdtz(self):
            self.JvecVsJtvecTest(prbtype='j', rxcomp='dhdtz')

if __name__ == '__main__':
    unittest.main()
