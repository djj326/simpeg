import SimPEG
from SimPEG.Utils import Identity, Zero
import numpy as np

class Fields(SimPEG.Problem.Fields):
    knownFields = {}
    dtype = float

    def _phiDeriv(self, src, du_dm_v, v, adjoint=False):
        if getattr(self, '_phiDeriv_u', None) is None or getattr(self, '_phiDeriv_m', None) is None:
            raise NotImplementedError ('Getting phiDerivs from %s is not implemented' %self.knownFields.keys()[0])

        if adjoint:
            return self._phiDeriv_u(src, v, adjoint=adjoint), self._phiDeriv_m(src, v, adjoint=adjoint)

        return np.array(self._phiDeriv_u(src, du_dm_v, adjoint) + self._phiDeriv_m(src, v, adjoint), dtype = float)

    def _eDeriv(self, src, du_dm_v, v, adjoint=False):
        if getattr(self, '_eDeriv_u', None) is None or getattr(self, '_eDeriv_m', None) is None:
            raise NotImplementedError ('Getting eDerivs from %s is not implemented' %self.knownFields.keys()[0])

        if adjoint:
            return self._eDeriv_u(src, v, adjoint), self._eDeriv_m(src, v, adjoint)
        return np.array(self._eDeriv_u(src, du_dm_v, adjoint) + self._eDeriv_m(src, v, adjoint), dtype = float)

    def _jDeriv(self, src, du_dm_v, v, adjoint=False):
        if getattr(self, '_jDeriv_u', None) is None or getattr(self, '_jDeriv_m', None) is None:
            raise NotImplementedError ('Getting jDerivs from %s is not implemented' %self.knownFields.keys()[0])

        if adjoint:
            return self._jDeriv_u(src, v, adjoint), self._jDeriv_m(src, v, adjoint)
        return np.array(self._jDeriv_u(src, du_dm_v, adjoint) + self._jDeriv_m(src, v, adjoint), dtype = float)


class Fields_CC(Fields):
    knownFields = {'phiSolution':'CC'}
    aliasFields = {
                    'phi': ['phiSolution','CC','_phi'],
                    'j' : ['phiSolution','F','_j'],
                    'e' : ['phiSolution','F','_e'],
                  }
                  # primary - secondary
                  # CC variables

    def __init__(self, mesh, survey, **kwargs):
        Fields.__init__(self, mesh, survey, **kwargs)

    def startup(self):
        self.prob = self.survey.prob

    def _GLoc(self, fieldType):
        if fieldType == 'phi':
            return 'CC'
        elif fieldType == 'e' or fieldType == 'j':
            return 'F'
        else:
            raise Exception('Field type must be phi, e, j')

    def _phi(self, phiSolution, srcList):
        return phiSolution

    def _phiDeriv_u(self, src, v, adjoint = False):
        return Identity()*v

    def _phiDeriv_m(self, src, v, adjoint = False):
        return Zero()

    def _j(self, phiSolution, srcList):
        raise NotImplementedError

    def _e(self, phiSolution, srcList):
        raise NotImplementedError

class Fields_N(Fields):
    knownFields = {'phiSolution':'N'}
    aliasFields = {
                    'phi': ['phiSolution','N','_phi'],
                    'j' : ['phiSolution','E','_j'],
                    'e' : ['phiSolution','E','_e'],
                  }
                  # primary - secondary
                  # N variables

    def __init__(self, mesh, survey, **kwargs):
        Fields.__init__(self, mesh, survey, **kwargs)

    def startup(self):
        self.prob = self.survey.prob

    def _GLoc(self, fieldType):
        if fieldType == 'phi':
            return 'N'
        elif fieldType == 'e' or fieldType == 'j':
            return 'E'
        else:
            raise Exception('Field type must be phi, e, j')

    def _phi(self, phiSolution, srcList):
        return phiSolution

    def _phiDeriv_u(self, src, v, adjoint = False):
        return Identity()

    def _phiDeriv_m(self, src, v, adjoint = False):
        return Zero()

    def _j(self, phiSolution, srcList):
        raise NotImplementedError

    def _e(self, phiSolution, srcList):
        raise NotImplementedError
