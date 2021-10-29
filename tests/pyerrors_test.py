import autograd.numpy as np
import os
import random
import string
import copy
import pyerrors as pe
import pytest

np.random.seed(0)


def test_dump():
    value = np.random.normal(5, 10)
    dvalue = np.abs(np.random.normal(0, 1))
    test_obs = pe.pseudo_Obs(value, dvalue, 't')
    test_obs.dump('test_dump')
    new_obs = pe.load_object('test_dump.p')
    os.remove('test_dump.p')
    assert test_obs.deltas['t'].all() == new_obs.deltas['t'].all()


def test_comparison():
    value1 = np.random.normal(0, 100)
    test_obs1 = pe.pseudo_Obs(value1, 0.1, 't')
    value2 = np.random.normal(0, 100)
    test_obs2 = pe.pseudo_Obs(value2, 0.1, 't')
    assert (value1 > value2) == (test_obs1 > test_obs2)
    assert (value1 < value2) == (test_obs1 < test_obs2)
    assert (value1 >= value2) == (test_obs1 >= test_obs2)
    assert (value1 <= value2) == (test_obs1 <= test_obs2)
    assert test_obs1 >= test_obs1
    assert test_obs2 <= test_obs2
    assert test_obs1 == test_obs1
    assert test_obs2 == test_obs2
    assert test_obs1 - test_obs1 == 0.0
    assert test_obs1 / test_obs1 == 1.0
    assert test_obs1 != value1
    assert test_obs2 != value2
    assert test_obs1 != test_obs2
    assert test_obs2 != test_obs1


def test_function_overloading():
    a = pe.pseudo_Obs(17, 2.9, 'e1')
    b = pe.pseudo_Obs(4, 0.8, 'e1')

    fs = [lambda x: x[0] + x[1], lambda x: x[1] + x[0], lambda x: x[0] - x[1], lambda x: x[1] - x[0],
          lambda x: x[0] * x[1], lambda x: x[1] * x[0], lambda x: x[0] / x[1], lambda x: x[1] / x[0],
          lambda x: np.exp(x[0]), lambda x: np.sin(x[0]), lambda x: np.cos(x[0]), lambda x: np.tan(x[0]),
          lambda x: np.log(x[0]), lambda x: np.sqrt(np.abs(x[0])),
          lambda x: np.sinh(x[0]), lambda x: np.cosh(x[0]), lambda x: np.tanh(x[0])]

    for i, f in enumerate(fs):
        t1 = f([a, b])
        t2 = pe.derived_observable(f, [a, b])
        c = t2 - t1
        assert c.is_zero()

    assert np.log(np.exp(b)) == b
    assert np.exp(np.log(b)) == b
    assert np.sqrt(b ** 2) == b
    assert np.sqrt(b) ** 2 == b


def test_overloading_vectorization():
    a = np.random.randint(1, 100, 10)
    b = pe.pseudo_Obs(4, 0.8, 't')

    assert [o.value for o in a * b] == [o.value for o in b * a]
    assert [o.value for o in a + b] == [o.value for o in b + a]
    assert [o.value for o in a - b] == [-1 * o.value for o in b - a]
    assert [o.value for o in a / b] == [o.value for o in [p / b for p in a]]
    assert [o.value for o in b / a] == [o.value for o in [b / p for p in a]]

    a = np.random.normal(0.0, 1e10, 10)
    b = pe.pseudo_Obs(4, 0.8, 't')

    assert [o.value for o in a * b] == [o.value for o in b * a]
    assert [o.value for o in a + b] == [o.value for o in b + a]
    assert [o.value for o in a - b] == [-1 * o.value for o in b - a]
    assert [o.value for o in a / b] == [o.value for o in [p / b for p in a]]
    assert [o.value for o in b / a] == [o.value for o in [b / p for p in a]]


def test_gamma_method():
    for data in [np.tile([1, -1], 1000),
                 np.random.rand(100001),
                 np.zeros(1195),
                 np.sin(np.sqrt(2) * np.pi * np.arange(1812))]:
        test_obs = pe.Obs([data], ['t'])
        test_obs.gamma_method()
        assert test_obs.dvalue - test_obs.ddvalue <= np.std(data, ddof=1) / np.sqrt(len(data))
        assert test_obs.e_tauint['t'] - 0.5 <= test_obs.e_dtauint['t']
        test_obs.gamma_method(tau_exp=10)
        assert test_obs.e_tauint['t'] - 10.5 <= test_obs.e_dtauint['t']


def test_gamma_method_persistance():
    my_obs = pe.Obs([np.random.rand(730)], ['t'])
    my_obs.gamma_method()
    value = my_obs.value
    dvalue = my_obs.dvalue
    ddvalue = my_obs.ddvalue
    my_obs = 1.0 * my_obs
    my_obs.gamma_method()
    assert value == my_obs.value
    assert dvalue == my_obs.dvalue
    assert ddvalue == my_obs.ddvalue
    my_obs.gamma_method()
    assert value == my_obs.value
    assert dvalue == my_obs.dvalue
    assert ddvalue == my_obs.ddvalue
    my_obs.gamma_method(S=3.7)
    my_obs.gamma_method()
    assert value == my_obs.value
    assert dvalue == my_obs.dvalue
    assert ddvalue == my_obs.ddvalue


def test_covariance_is_variance():
    value = np.random.normal(5, 10)
    dvalue = np.abs(np.random.normal(0, 1))
    test_obs = pe.pseudo_Obs(value, dvalue, 't')
    test_obs.gamma_method()
    assert np.abs(test_obs.dvalue ** 2 - pe.covariance(test_obs, test_obs)) <= 10 * np.finfo(np.float64).eps
    test_obs = test_obs + pe.pseudo_Obs(value, dvalue, 'q', 200)
    test_obs.gamma_method(e_tag=0)
    assert np.abs(test_obs.dvalue ** 2 - pe.covariance(test_obs, test_obs)) <= 10 * np.finfo(np.float64).eps


def test_fft():
    value = np.random.normal(5, 100)
    dvalue = np.abs(np.random.normal(0, 5))
    test_obs1 = pe.pseudo_Obs(value, dvalue, 't', int(500 + 1000 * np.random.rand()))
    test_obs2 = copy.deepcopy(test_obs1)
    test_obs1.gamma_method()
    test_obs2.gamma_method(fft=False)
    assert max(np.abs(test_obs1.e_rho[''] - test_obs2.e_rho[''])) <= 10 * np.finfo(np.float64).eps
    assert np.abs(test_obs1.dvalue - test_obs2.dvalue) <= 10 * max(test_obs1.dvalue, test_obs2.dvalue) * np.finfo(np.float64).eps


def test_covariance_symmetry():
    value1 = np.random.normal(5, 10)
    dvalue1 = np.abs(np.random.normal(0, 1))
    test_obs1 = pe.pseudo_Obs(value1, dvalue1, 't')
    test_obs1.gamma_method()
    value2 = np.random.normal(5, 10)
    dvalue2 = np.abs(np.random.normal(0, 1))
    test_obs2 = pe.pseudo_Obs(value2, dvalue2, 't')
    test_obs2.gamma_method()
    cov_ab = pe.covariance(test_obs1, test_obs2)
    cov_ba = pe.covariance(test_obs2, test_obs1)
    assert np.abs(cov_ab - cov_ba) <= 10 * np.finfo(np.float64).eps
    assert np.abs(cov_ab) < test_obs1.dvalue * test_obs2.dvalue * (1 + 10 * np.finfo(np.float64).eps)


def test_gamma_method():
    # Construct pseudo Obs with random shape
    value = np.random.normal(5, 10)
    dvalue = np.abs(np.random.normal(0, 1))

    test_obs = pe.pseudo_Obs(value, dvalue, 't', int(1000 * (1 + np.random.rand())))

    # Test if the error is processed correctly
    test_obs.gamma_method(e_tag=1)
    assert np.abs(test_obs.value - value) < 1e-12
    assert abs(test_obs.dvalue - dvalue) < 1e-10 * dvalue


def test_derived_observables():
    # Construct pseudo Obs with random shape
    test_obs = pe.pseudo_Obs(2, 0.1 * (1 + np.random.rand()), 't', int(1000 * (1 + np.random.rand())))

    # Check if autograd and numgrad give the same result
    d_Obs_ad = pe.derived_observable(lambda x, **kwargs: x[0] * x[1] * np.sin(x[0] * x[1]), [test_obs, test_obs])
    d_Obs_ad.gamma_method()
    d_Obs_fd = pe.derived_observable(lambda x, **kwargs: x[0] * x[1] * np.sin(x[0] * x[1]), [test_obs, test_obs], num_grad=True)
    d_Obs_fd.gamma_method()

    assert d_Obs_ad.value == d_Obs_fd.value
    assert np.abs(4.0 * np.sin(4.0) - d_Obs_ad.value) < 1000 * np.finfo(np.float64).eps * np.abs(d_Obs_ad.value)
    assert np.abs(d_Obs_ad.dvalue-d_Obs_fd.dvalue) < 1000 * np.finfo(np.float64).eps * d_Obs_ad.dvalue

    i_am_one = pe.derived_observable(lambda x, **kwargs: x[0] / x[1], [d_Obs_ad, d_Obs_ad])
    i_am_one.gamma_method(e_tag=1)

    assert i_am_one.value == 1.0
    assert i_am_one.dvalue < 2 * np.finfo(np.float64).eps
    assert i_am_one.e_dvalue['t'] <= 2 * np.finfo(np.float64).eps
    assert i_am_one.e_ddvalue['t'] <= 2 * np.finfo(np.float64).eps


def test_multi_ens_system():
    names = []
    for i in range(100 + int(np.random.rand() * 50)):
        tmp_string = ''
        for _ in range(int(2 + np.random.rand() * 4)):
            tmp_string += random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        names.append(tmp_string)
    names = list(set(names))
    samples = [np.random.rand(5)] * len(names)
    new_obs = pe.Obs(samples, names)

    for e_tag_length in range(1, 6):
        new_obs.gamma_method(e_tag=e_tag_length)
        e_names = sorted(set([n[:e_tag_length] for n in names]))
        assert e_names == new_obs.e_names
        assert sorted(x for y in sorted(new_obs.e_content.values()) for x in y) == sorted(new_obs.names)


def test_overloaded_functions():
    funcs = [np.exp, np.log, np.sin, np.cos, np.tan, np.sinh, np.cosh, np.arcsinh, np.arccosh]
    deriv = [np.exp, lambda x: 1 / x, np.cos, lambda x: -np.sin(x), lambda x: 1 / np.cos(x) ** 2, np.cosh, np.sinh, lambda x: 1 / np.sqrt(x ** 2 + 1), lambda x: 1 / np.sqrt(x ** 2 - 1)]
    val = 3 + 0.5 * np.random.rand()
    dval = 0.3 + 0.4 * np.random.rand()
    test_obs = pe.pseudo_Obs(val, dval, 't', int(1000 * (1 + np.random.rand())))

    for i, item in enumerate(funcs):
        ad_obs = item(test_obs)
        fd_obs = pe.derived_observable(lambda x, **kwargs: item(x[0]), [test_obs], num_grad=True)
        ad_obs.gamma_method(S=0.01, e_tag=1)
        assert np.max((ad_obs.deltas['t'] - fd_obs.deltas['t']) / ad_obs.deltas['t']) < 1e-8, item.__name__
        assert np.abs((ad_obs.value - item(val)) / ad_obs.value) < 1e-10, item.__name__
        assert np.abs(ad_obs.dvalue - dval * np.abs(deriv[i](val))) < 1e-6, item.__name__


def test_utils():
    my_obs = pe.pseudo_Obs(1.0, 0.5, 't')
    my_obs.print(0)
    my_obs.print(1)
    my_obs.print(2)
    assert not my_obs.is_zero_within_error()
    my_obs.plot_tauint()
    my_obs.plot_rho()
    my_obs.plot_rep_dist()
    my_obs.plot_history()
    my_obs.plot_piechart()
    assert my_obs > (my_obs - 1)
    assert my_obs < (my_obs + 1)


def test_cobs():
    obs1 = pe.pseudo_Obs(1.0, 0.1, 't')
    obs2 = pe.pseudo_Obs(-0.2, 0.03, 't')

    my_cobs = pe.CObs(obs1, obs2)
    assert not (my_cobs + my_cobs.conjugate()).real.is_zero()
    assert (my_cobs + my_cobs.conjugate()).imag.is_zero()
    assert (my_cobs - my_cobs.conjugate()).real.is_zero()
    assert not (my_cobs - my_cobs.conjugate()).imag.is_zero()
    np.abs(my_cobs)

    assert (my_cobs * my_cobs / my_cobs - my_cobs).is_zero()
    assert (my_cobs + my_cobs - 2 * my_cobs).is_zero()

    fs = [[lambda x: x[0] + x[1], lambda x: x[1] + x[0]],
          [lambda x: x[0] * x[1], lambda x: x[1] * x[0]]]
    for other in [3, 1.1, (1.1 - 0.2j), (2.3 + 0j), (0.0 + 7.7j), pe.CObs(obs1), pe.CObs(obs1, obs2)]:
        for funcs in fs:
            ta = funcs[0]([my_cobs, other])
            tb = funcs[1]([my_cobs, other])
            diff = ta - tb
            assert diff.is_zero()

        ta = my_cobs - other
        tb = other - my_cobs
        diff = ta + tb
        assert diff.is_zero()

        ta = my_cobs / other
        tb = other / my_cobs
        diff = ta * tb - 1
        assert diff.is_zero()

        assert (my_cobs / other * other - my_cobs).is_zero()
        assert (other / my_cobs * my_cobs - other).is_zero()


def test_reweighting():
    my_obs = pe.Obs([np.random.rand(1000)], ['t'])
    assert not my_obs.reweighted
    r_obs = pe.reweight(my_obs, [my_obs])
    assert r_obs[0].reweighted
    r_obs2 = r_obs[0] * my_obs
    assert r_obs2.reweighted


def test_merge_obs():
    my_obs1 = pe.Obs([np.random.rand(100)], ['t'])
    my_obs2 = pe.Obs([np.random.rand(100)], ['q'], idl=[range(1, 200, 2)])
    merged = pe.merge_obs([my_obs1, my_obs2])
    diff = merged - my_obs2 - my_obs1
    assert diff == -(my_obs1.value + my_obs2.value) / 2


def test_irregular_error_propagation():
    obs_list = [pe.Obs([np.random.rand(100)], ['t']),
                pe.Obs([np.random.rand(50)], ['t'], idl=[range(1, 100, 2)]),
                pe.Obs([np.random.rand(50)], ['t'], idl=[np.arange(1, 100, 2)]),
                pe.Obs([np.random.rand(6)], ['t'], idl=[[4, 18, 27, 29, 57, 80]]),
                pe.Obs([np.random.rand(50)], ['t'], idl=[list(range(1, 26)) + list(range(50, 100, 2))])]
    for obs1 in obs_list:
        for obs2 in obs_list:
            assert obs1 == (obs1 / obs2) * obs2
            assert obs1 == (obs1 * obs2) / obs2
            assert obs1 == obs1 * (obs2 / obs2)
            assert obs1 == (obs1 + obs2) - obs2
            assert obs1 == obs1 + (obs2 - obs2)


def test_gamma_method_irregular():
    N = 20000
    arr = np.random.normal(1, .2, size=N)
    afull = pe.Obs([arr], ['a'])

    configs = np.ones_like(arr)
    for i in np.random.uniform(0, len(arr), size=int(.8 * N)):
        configs[int(i)] = 0
    zero_arr = [arr[i] for i in range(len(arr)) if not configs[i] == 0]
    idx = [i + 1 for i in range(len(configs)) if configs[i] == 1]
    a = pe.Obs([zero_arr], ['a'], idl=[idx])

    afull.gamma_method()
    a.gamma_method()
    ad = a.dvalue

    expe = (afull.dvalue * np.sqrt(N / np.sum(configs)))
    assert (a.dvalue - 5 * a.ddvalue < expe and expe < a.dvalue + 5 * a.ddvalue)

    afull.gamma_method(fft=False)
    a.gamma_method(fft=False)

    expe = (afull.dvalue * np.sqrt(N / np.sum(configs)))
    assert (a.dvalue - 5 * a.ddvalue < expe and expe < a.dvalue + 5 * a.ddvalue)
    assert np.abs(a.dvalue - ad) <= 10 * max(a.dvalue, ad) * np.finfo(np.float64).eps

    afull.gamma_method(tau_exp=.00001)
    a.gamma_method(tau_exp=.00001)

    expe = (afull.dvalue * np.sqrt(N / np.sum(configs)))
    assert (a.dvalue - 5 * a.ddvalue < expe and expe < a.dvalue + 5 * a.ddvalue)

    arr2 = np.random.normal(1, .2, size=N)
    afull = pe.Obs([arr, arr2], ['a1', 'a2'])

    configs = np.ones_like(arr2)
    for i in np.random.uniform(0, len(arr2), size=int(.8*N)):
        configs[int(i)] = 0
    zero_arr2 = [arr2[i] for i in range(len(arr2)) if not configs[i] == 0]
    idx2 = [i + 1 for i in range(len(configs)) if configs[i] == 1]
    a = pe.Obs([zero_arr, zero_arr2], ['a1', 'a2'], idl=[idx, idx2])

    afull.gamma_method(e_tag=1)
    a.gamma_method(e_tag=1)

    expe = (afull.dvalue * np.sqrt(N / np.sum(configs)))
    assert (a.dvalue - 5 * a.ddvalue < expe and expe < a.dvalue + 5 * a.ddvalue)

    def gen_autocorrelated_array(inarr, rho):
        outarr = np.copy(inarr)
        for i in range(1, len(outarr)):
            outarr[i] = rho * outarr[i - 1] + np.sqrt(1 - rho**2) * outarr[i]
        return outarr

    arr = np.random.normal(1, .2, size=N)
    carr = gen_autocorrelated_array(arr, .346)
    a = pe.Obs([carr], ['a'])
    a.gamma_method(e_tag=1)

    ae = pe.Obs([[carr[i] for i in range(len(carr)) if i % 2 == 0]], ['a'], idl=[[i for i in range(len(carr)) if i % 2 == 0]])
    ae.gamma_method(e_tag=1)

    ao = pe.Obs([[carr[i] for i in range(len(carr)) if i % 2 == 1]], ['a'], idl=[[i for i in range(len(carr)) if i % 2 == 1]])
    ao.gamma_method(e_tag=1)

    assert(ae.e_tauint['a'] < a.e_tauint['a'])
    assert((ae.e_tauint['a'] - 4 * ae.e_dtauint['a'] < ao.e_tauint['a']))
    assert((ae.e_tauint['a'] + 4 * ae.e_dtauint['a'] > ao.e_tauint['a']))


def test_covariance2_symmetry():
    value1 = np.random.normal(5, 10)
    dvalue1 = np.abs(np.random.normal(0, 1))
    test_obs1 = pe.pseudo_Obs(value1, dvalue1, 't')
    test_obs1.gamma_method()
    value2 = np.random.normal(5, 10)
    dvalue2 = np.abs(np.random.normal(0, 1))
    test_obs2 = pe.pseudo_Obs(value2, dvalue2, 't')
    test_obs2.gamma_method()
    cov_ab = pe.covariance2(test_obs1, test_obs2)
    cov_ba = pe.covariance2(test_obs2, test_obs1)
    assert np.abs(cov_ab - cov_ba) <= 10 * np.finfo(np.float64).eps
    assert np.abs(cov_ab) < test_obs1.dvalue * test_obs2.dvalue * (1 + 10 * np.finfo(np.float64).eps)

    N = 100
    arr = np.random.normal(1, .2, size=N)
    configs = np.ones_like(arr)
    for i in np.random.uniform(0, len(arr), size=int(.8 * N)):
        configs[int(i)] = 0
    zero_arr = [arr[i] for i in range(len(arr)) if not configs[i] == 0]
    idx = [i + 1 for i in range(len(configs)) if configs[i] == 1]
    a = pe.Obs([zero_arr], ['t'], idl=[idx])
    a.gamma_method()
    assert np.isclose(a.dvalue**2, pe.covariance2(a, a), atol=100, rtol=1e-4)

    cov_ab = pe.covariance2(test_obs1, a)
    cov_ba = pe.covariance2(a, test_obs1)
    assert np.abs(cov_ab - cov_ba) <= 10 * np.finfo(np.float64).eps
    assert np.abs(cov_ab) < test_obs1.dvalue * test_obs2.dvalue * (1 + 10 * np.finfo(np.float64).eps)
