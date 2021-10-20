import numpy as np


gammaX = np.array(
    [[0, 0, 0, 1j], [0, 0, 1j, 0], [0, -1j, 0, 0], [-1j, 0, 0, 0]],
    dtype=complex)
gammaY = np.array(
    [[0, 0, 0, -1], [0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0]],
    dtype=complex)
gammaZ = np.array(
    [[0, 0, 1j, 0], [0, 0, 0, -1j], [-1j, 0, 0, 0], [0, 1j, 0, 0]],
    dtype=complex)
gammaT = np.array(
    [[0, 0, 1, 0], [0, 0, 0, 1], [1, 0, 0, 0], [0, 1, 0, 0]],
    dtype=complex)
gamma = np.array([gammaX, gammaY, gammaZ, gammaT])
gamma5 = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, -1]],
    dtype=complex)
identity = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    dtype=complex)


def Grid_gamma(gamma_tag):
    """Returns gamma matrix in Grid labeling."""
    if gamma_tag == 'Identity':
        g = identity
    elif gamma_tag == 'Gamma5':
        g = gamma5
    elif gamma_tag == 'GammaX':
        g = gamma[0]
    elif gamma_tag == 'GammaY':
        g = gamma[1]
    elif gamma_tag == 'GammaZ':
        g = gamma[2]
    elif gamma_tag == 'GammaT':
        g = gamma[3]
    elif gamma_tag == 'GammaXGamma5':
        g = gamma[0] @ gamma5
    elif gamma_tag == 'GammaYGamma5':
        g = gamma[1] @ gamma5
    elif gamma_tag == 'GammaZGamma5':
        g = gamma[2] @ gamma5
    elif gamma_tag == 'GammaTGamma5':
        g = gamma[3] @ gamma5
    elif gamma_tag == 'SigmaXT':
        g = 0.5 * (gamma[0] @ gamma[3] - gamma[3] @ gamma[0])
    elif gamma_tag == 'SigmaXY':
        g = 0.5 * (gamma[0] @ gamma[1] - gamma[1] @ gamma[0])
    elif gamma_tag == 'SigmaXZ':
        g = 0.5 * (gamma[0] @ gamma[2] - gamma[2] @ gamma[0])
    elif gamma_tag == 'SigmaYT':
        g = 0.5 * (gamma[1] @ gamma[3] - gamma[3] @ gamma[1])
    elif gamma_tag == 'SigmaYZ':
        g = 0.5 * (gamma[1] @ gamma[2] - gamma[2] @ gamma[1])
    elif gamma_tag == 'SigmaZT':
        g = 0.5 * (gamma[2] @ gamma[3] - gamma[3] @ gamma[2])
    else:
        raise Exception('Unkown gamma structure', gamma_tag)
    return g


class Npr_matrix(np.ndarray):

    def __new__(cls, input_array, mom_in=None, mom_out=None):
        obj = np.asarray(input_array).view(cls)
        obj.mom_in = mom_in
        obj.mom_out = mom_out
        return obj

    @property
    def g5H(self):
        """Gamma_5 hermitean conjugate

        Returns gamma_5 @ M.T.conj() @ gamma_5 and exchanges in and out going
        momenta. Works only for 12x12 matrices.
        """
        if self.shape != (12, 12):
            raise Exception('g5H only works for 12x12 matrices.')
        extended_g5 = np.kron(np.eye(3, dtype=int), gamma5)
        new_matrix = extended_g5 @ self.conj().T @ extended_g5
        new_matrix.mom_in = self.mom_out
        new_matrix.mom_out = self.mom_in
        return new_matrix

    def _propagate_mom(self, other, name):
        s_mom = getattr(self, name, None)
        o_mom = getattr(other, name, None)
        if s_mom is not None and o_mom is not None:
            if not np.allclose(s_mom, o_mom):
                raise Exception(name + ' does not match.')
        return o_mom if o_mom else s_mom

    def __matmul__(self, other):
        return self.__new__(Npr_matrix,
                            super().__matmul__(other),
                            self._propagate_mom(other, 'mom_in'),
                            self._propagate_mom(other, 'mom_out'))

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.mom_in = getattr(obj, 'mom_in', None)
        self.mom_out = getattr(obj, 'mom_out', None)
