# Copyright 2021 D-Wave Systems Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import itertools
import shutil
import tempfile
import unittest

import numpy as np

from parameterized import parameterized

import dimod

from dimod import Spin, Binary, Integer, QM, QuadraticModel


VARTYPES = dict(BINARY=dimod.BINARY, SPIN=dimod.SPIN, INTEGER=dimod.INTEGER)


def qmBinary(label):
    qm = QM()
    qm.set_linear(qm.add_variable('BINARY', label), 1)
    return qm


def qmSpin(label):
    qm = QM()
    qm.set_linear(qm.add_variable('SPIN', label), 1)
    return qm


class TestAddVariable(unittest.TestCase):
    @parameterized.expand(VARTYPES.items())
    def test_add_one(self, vartype_str, vartype):
        qm = QM()
        v = qm.add_variable(vartype_str)
        self.assertEqual(v, 0)
        self.assertIs(qm.vartype(v), vartype)

    @parameterized.expand(VARTYPES.items())
    def test_existing_same_type(self, vartype_str, vartype):
        qm = QM()
        u = qm.add_variable(vartype_str)
        v = qm.add_variable(vartype_str, label=u)
        self.assertEqual(u, v)

    @parameterized.expand(itertools.combinations(VARTYPES.values(), 2))
    def test_cross_vartype(self, vartype0, vartype1):
        qm = QM()
        u = qm.add_variable(vartype0)
        with self.assertRaises(TypeError):
            qm.add_variable(vartype1, u)

    def test_add_integer_with_ub_lb(self):
        qm = QM()

        h = qm.add_variable('INTEGER', 'h')
        i = qm.add_variable('INTEGER', 'i', lower_bound=-1)
        j = qm.add_variable('INTEGER', 'j', upper_bound=103)
        k = qm.add_variable('INTEGER', 'k', lower_bound=-50, upper_bound=50)

        self.assertEqual(qm.lower_bound(i), -1)
        self.assertEqual(qm.upper_bound(i), qm.upper_bound(h))

        self.assertEqual(qm.lower_bound(j), qm.lower_bound(h))
        self.assertEqual(qm.upper_bound(j), 103)

        self.assertEqual(qm.lower_bound(k), -50)
        self.assertEqual(qm.upper_bound(k), 50)

    def test_add_integer_with_contradicting_ub_lb(self):
        qm = QM()
        qm.add_variable('INTEGER', 'i', lower_bound=-1, upper_bound=103)

        with self.assertRaises(ValueError):
            qm.add_variable('INTEGER', 'i', lower_bound=-2)

        with self.assertRaises(ValueError):
            qm.add_variable('INTEGER', 'i', upper_bound=10)

        qm.add_variable('INTEGER', 'i', lower_bound=-1)
        qm.add_variable('INTEGER', 'i', upper_bound=103, lower_bound=-1)


class TestAddQuadratic(unittest.TestCase):
    def test_self_loop_spin(self):
        qm = QM(vartypes={'i': 'INTEGER', 's': 'SPIN', 'x': 'BINARY'})
        with self.subTest('BINARY'):
            with self.assertRaises(ValueError):
                qm.add_quadratic('x', 'x', 1)
        with self.subTest('INTEGER'):
            qm.add_quadratic('i', 'i', 1)
            self.assertEqual(qm.get_quadratic('i', 'i'), 1)
            self.assertEqual(qm.quadratic, {('i', 'i'): 1})
        with self.subTest('SPIN'):
            with self.assertRaises(ValueError):
                qm.add_quadratic('s', 's', 1)


class TestAlias(unittest.TestCase):
    def test_alias(self):
        self.assertIs(QM, QuadraticModel)


class TestBounds(unittest.TestCase):
    def test_copy(self):
        i = Integer('i', lower_bound=-10, upper_bound=10)

        j = i.copy()

        self.assertEqual(j.lower_bound('i'), -10)
        self.assertEqual(j.upper_bound('i'), 10)

    def test_inconsistent(self):
        i0 = Integer('i', lower_bound=-7, upper_bound=14)
        i1 = Integer('i', lower_bound=-7, upper_bound=140)

        with self.assertRaises(ValueError):
            i0 + i1

        with self.assertRaises(ValueError):
            i0 - i1

        with self.assertRaises(ValueError):
            i0*i1

    @parameterized.expand([(np.float64,), (np.float32,)])
    def test_set_lower_bound(self, dtype):
        qm = QuadraticModel(dtype=dtype)
        qm.add_variable('INTEGER', 'i')
        qm.add_variable('SPIN', 's')
        qm.add_variable('BINARY', 'x')

        # cannot set less than max_integer
        with self.assertRaises(ValueError):
            qm.set_lower_bound('i', np.finfo(dtype).min)

        # cannot set for non-integer
        with self.assertRaises(ValueError):
            qm.set_lower_bound('s', -2)
        with self.assertRaises(ValueError):
            qm.set_lower_bound('x', 10)

        # cannot set one greater than the current upper bound
        with self.assertRaises(ValueError):
            qm.set_lower_bound('i', qm.upper_bound('i') + 1)

        qm.set_lower_bound('i', -10)
        self.assertEqual(qm.lower_bound('i'), -10)

        qm.set_lower_bound('i', -11.3)
        self.assertEqual(qm.lower_bound('i'), -11)

    @parameterized.expand([(np.float64,), (np.float32,)])
    def test_set_upper_bound(self, dtype):
        qm = QuadraticModel(dtype=dtype)
        qm.add_variable('INTEGER', 'i')
        qm.add_variable('SPIN', 's')
        qm.add_variable('BINARY', 'x')

        # cannot set less than max_integer
        with self.assertRaises(ValueError):
            qm.set_upper_bound('i', np.finfo(dtype).max)

        # cannot set for non-integer
        with self.assertRaises(ValueError):
            qm.set_upper_bound('s', -2)
        with self.assertRaises(ValueError):
            qm.set_upper_bound('x', 10)

        # cannot set one less than the current lower bound
        with self.assertRaises(ValueError):
            qm.set_upper_bound('i', qm.lower_bound('i') - 1)

        qm.set_upper_bound('i', 10)
        self.assertEqual(qm.upper_bound('i'), 10)

        qm.set_upper_bound('i', 11.3)
        self.assertEqual(qm.upper_bound('i'), 11)

    def test_symbolic_mul(self):
        i = Integer('i', lower_bound=-10, upper_bound=10)
        new = i*i

        self.assertEqual(new.lower_bound('i'), -10)
        self.assertEqual(new.upper_bound('i'), 10)

    def test_symbolic_add(self):
        i = Integer('i', lower_bound=-10, upper_bound=10)
        new = i+i
        self.assertEqual(new.lower_bound('i'), -10)
        self.assertEqual(new.upper_bound('i'), 10)


class TestChangeVartype(unittest.TestCase):
    def test_simple(self):
        qm = QM()
        a = qm.add_variable('SPIN', 'a')
        qm.set_linear(a, 1.5)
        qm.change_vartype('BINARY', a)
        self.assertEqual(qm.energy({a: 1}), 1.5)
        self.assertEqual(qm.energy({a: 0}), -1.5)
        self.assertIs(qm.vartype(a), dimod.BINARY)

    def test_invalid(self):
        qm = QM()
        a = qm.add_variable('INTEGER', 'a')
        with self.assertRaises(TypeError):
            qm.change_vartype('SPIN', a)


class TestConstruction(unittest.TestCase):
    def test_dtype(self):
        self.assertEqual(QM().dtype, np.float64)  # default
        self.assertEqual(QM(dtype=np.float32).dtype, np.float32)
        self.assertEqual(QM(dtype=np.float64).dtype, np.float64)

    def test_empty_offset(self):
        self.assertEqual(QM().offset, 0)
        self.assertEqual(QM(dtype=np.float64).offset.dtype, np.float64)


class TestDegree(unittest.TestCase):
    def test_degree(self):
        qm = QM()
        i = qm.add_variable('INTEGER')
        j = qm.add_variable('INTEGER')
        x = qm.add_variable('BINARY')

        qm.set_linear(i, 1.5)
        qm.set_linear(x, -2)

        qm.set_quadratic(i, j, 1)
        qm.set_quadratic(j, j, 5)
        qm.set_quadratic(x, i, 7)

        self.assertEqual(qm.degree(i), 2)
        self.assertEqual(qm.degree(j), 2)
        self.assertEqual(qm.degree(x), 1)


class TestEnergies(unittest.TestCase):
    def test_bug982(self):
        # https://github.com/dwavesystems/dimod/issues/982
        i, j = dimod.Integers('ij')

        self.assertAlmostEqual((i*j).energy({'i': 4294967296, 'j': 4294967296}),
                               1.8446744073709552e+19)

    def test_spin_bin(self):
        x = Binary('x')
        s = Spin('s')

        self.assertEqual((2*x*s).energy({'x': 1, 's': 1}), 2)
        self.assertEqual((2*x*s).energy({'x': 1, 's': -1}), -2)
        self.assertEqual((2*x*s).energy({'x': 0, 's': 1}), 0)
        self.assertEqual((2*x*s+1).energy({'x': 0, 's': -1}), 1)

    def test_integer(self):
        i = Integer('i')

        for s in np.geomspace(1, i.upper_bound('i'), num=20, dtype=np.int64):
            sample = {'i': s}
            self.assertEqual(i.energy(sample), s)
            sample = {'i': -s}
            self.assertEqual(i.energy(sample), -s)

    def test_superset(self):
        a = Integer('a')
        b = Binary('b')

        qm = a + a*b + 1.5

        self.assertEqual(qm.energy({'a': 1, 'b': 1, 'c': 1}), 3.5)
        self.assertEqual(qm.energy({'a': 1, 'b': 0, 'c': 1}), 2.5)

    def test_subset(self):
        a = Integer('a')
        b = Binary('b')
        c = Spin('c')

        qm = a + a*b + c + 1.5

        samples = {'a': 1, 'c': 1}

        with self.assertRaises(ValueError):
            qm.energy(samples)


class TestFileSerialization(unittest.TestCase):
    @parameterized.expand([(np.float32,), (np.float64,)])
    def test_empty(self, dtype):
        qm = QM()

        with tempfile.TemporaryFile() as tf:
            with qm.to_file() as qmf:
                shutil.copyfileobj(qmf, tf)
            tf.seek(0)
            new = QM.from_file(tf)

        self.assertTrue(qm.is_equal(new))
        self.assertEqual(qm.dtype, new.dtype)

    @parameterized.expand([(np.float32,), (np.float64,)])
    def test_3var(self, dtype):
        qm = QM()
        qm.add_variable('INTEGER', 'i')
        qm.add_variable('BINARY', 'x')
        qm.add_variable('SPIN', 's')

        qm.set_linear('i', 3)
        qm.set_quadratic('s', 'i', 2)
        qm.set_quadratic('x', 's', -2)
        qm.set_quadratic('i', 'i', 5)
        qm.offset = 7

        with tempfile.TemporaryFile() as tf:
            with qm.to_file() as qmf:
                shutil.copyfileobj(qmf, tf)
            tf.seek(0)
            new = QM.from_file(tf)

        self.assertTrue(qm.is_equal(new))
        self.assertEqual(qm.dtype, new.dtype)


class TestFromBQM(unittest.TestCase):
    BQMs = dict(DictBQM=dimod.DictBQM,
                Float32BQM=dimod.Float32BQM,
                Float64BQM=dimod.Float64BQM,
                )

    @parameterized.expand(BQMs.items())
    def test(self, _, BQM):
        for vartype in ['SPIN', 'BINARY']:
            with self.subTest(vartype):
                bqm = BQM({'a': 1}, {'ab': 2, 'bc': 3}, 4, vartype)
                qm = QuadraticModel.from_bqm(bqm)

                self.assertEqual(bqm.linear, qm.linear)
                self.assertEqual(bqm.quadratic, qm.quadratic)
                self.assertEqual(bqm.offset, qm.offset)

                for v in bqm.variables:
                    self.assertIs(qm.vartype(v), bqm.vartype)


class TestInteger(unittest.TestCase):
    def test_init_no_label(self):
        integer_qm = Integer()
        self.assertIsInstance(integer_qm.variables[0], str)

    def test_multiple_labelled(self):
        i, j, k = dimod.Integers('ijk')

        self.assertEqual(i.variables[0], 'i')
        self.assertEqual(j.variables[0], 'j')
        self.assertEqual(k.variables[0], 'k')
        self.assertIs(i.vartype('i'), dimod.INTEGER)
        self.assertIs(j.vartype('j'), dimod.INTEGER)
        self.assertIs(k.vartype('k'), dimod.INTEGER)

    def test_multiple_unlabelled(self):
        i, j, k = dimod.Integers(3)

        self.assertNotEqual(i.variables[0], j.variables[0])
        self.assertNotEqual(i.variables[0], k.variables[0])
        self.assertIs(i.vartype(i.variables[0]), dimod.INTEGER)
        self.assertIs(j.vartype(j.variables[0]), dimod.INTEGER)
        self.assertIs(k.vartype(k.variables[0]), dimod.INTEGER)

    def test_no_label_collision(self):
        qm_1 = Integer()
        qm_2 = Integer()
        self.assertNotEqual(qm_1.variables[0], qm_2.variables[0])


class TestOffset(unittest.TestCase):
    def test_setting(self):
        qm = QM()
        qm.offset = 5
        self.assertEqual(qm.offset, 5)
        qm.offset -= 2
        self.assertEqual(qm.offset, 3)


class TestRemoveInteraction(unittest.TestCase):
    def test_several(self):
        i, j, k = dimod.Integers('ijk')
        qm = i*i + i*j + i*k + j*k + k + 1
        self.assertEqual(qm.num_interactions, 4)
        qm.remove_interaction('i', 'i')
        self.assertEqual(qm.num_interactions, 3)
        qm.remove_interaction('i', 'k')
        self.assertEqual(qm.num_interactions, 2)
        self.assertEqual(qm.quadratic, {('j', 'i'): 1.0, ('k', 'j'): 1.0})


class TestSpinToBinary(unittest.TestCase):
    def test_triangle(self):
        qm = QM()
        qm.add_variables_from('SPIN', 'rstu')
        qm.add_variable('BINARY', 'x')
        qm.add_variable('INTEGER', 'i')

        qm.quadratic['sx'] = 5
        qm.quadratic['si'] = -3
        qm.quadratic['xi'] = 23
        qm.quadratic['ti'] = -7
        qm.quadratic['xu'] = 3
        qm.quadratic['rs'] = -12

        qm.offset = 1.5
        qm.linear['r'] = 5
        qm.linear['x'] = -4
        qm.linear['i'] = .25

        new = qm.spin_to_binary(inplace=False)

        rng = np.random.default_rng(42)

        for _ in range(10):
            sample = {}
            for v in qm.variables:
                if qm.vartype(v) == dimod.BINARY:
                    sample[v] = rng.choice((0, 1))
                elif qm.vartype(v) == dimod.SPIN:
                    sample[v] = rng.choice((-1, 1))
                elif qm.vartype(v) == dimod.INTEGER:
                    sample[v] = rng.choice(10)

            energy = qm.energy(sample)

            for v in qm.variables:
                if qm.vartype(v) == dimod.SPIN:
                    sample[v] = (sample[v] + 1) // 2

            self.assertEqual(energy, new.energy(sample))

        self.assertIs(qm.vartype('r'), dimod.SPIN)
        self.assertIs(new.vartype('r'), dimod.BINARY)


class TestSymbolic(unittest.TestCase):
    def test_add_number(self):
        qm = QuadraticModel()
        new = qm + 1
        self.assertIsNot(qm, new)
        self.assertEqual(qm.offset, 0)
        self.assertEqual(new.offset, 1)
        self.assertEqual(qm.num_variables, 0)
        self.assertEqual(new.num_variables, 0)

    def test_iadd_number(self):
        qm = QuadraticModel()
        original = qm
        qm += 1
        self.assertIs(qm, original)
        self.assertEqual(qm.offset, 1)
        self.assertEqual(qm.num_variables, 0)

    def test_radd_number(self):
        qm = QuadraticModel()
        new = 1 + qm
        self.assertIsNot(qm, new)
        self.assertEqual(qm.offset, 0)
        self.assertEqual(new.offset, 1)
        self.assertEqual(qm.num_variables, 0)
        self.assertEqual(new.num_variables, 0)

    def test_div_number(self):
        i, j = dimod.Integers('ij')
        x = Binary('x')

        qm = 6*i*j + 2*i*x + 4*x + 12
        ref = qm
        qm /= 2
        self.assertIs(qm, ref)
        self.assertTrue(qm.is_equal(3*i*j + i*x + 2*x + 6))

    def test_isub(self):
        qm = Integer('i')
        qm -= Integer('j')
        qm -= 5
        self.assertTrue(
            qm.is_equal(QM({'i': 1, 'j': -1}, {}, -5, {'i': 'INTEGER', 'j': 'INTEGER'})))

    def test_expressions(self):
        i = Integer('i')
        j = Integer('j')

        self.assertTrue((i*j).is_equal(QM({}, {'ij': 1}, 0, {'i': 'INTEGER', 'j': 'INTEGER'})))
        self.assertTrue((i*i).is_equal(QM({}, {'ii': 1}, 0, {'i': 'INTEGER'})))
        self.assertTrue(((2*i)*(3*i)).is_equal(QM({}, {'ii': 6}, 0, {'i': 'INTEGER'})))
        self.assertTrue((i + j).is_equal(QM({'i': 1, 'j': 1}, {}, 0,
                                            {'i': 'INTEGER', 'j': 'INTEGER'})))
        self.assertTrue((i + 2*j).is_equal(QM({'i': 1, 'j': 2}, {}, 0,
                                              {'i': 'INTEGER', 'j': 'INTEGER'})))
        self.assertTrue((i - 2*j).is_equal(QM({'i': 1, 'j': -2}, {}, 0,
                                              {'i': 'INTEGER', 'j': 'INTEGER'})))
        self.assertTrue((-i).is_equal(QM({'i': -1}, {}, 0, {'i': 'INTEGER'})))
        self.assertTrue((1 - i).is_equal(QM({'i': -1}, {}, 1, {'i': 'INTEGER'})))
        self.assertTrue((i - 1).is_equal(QM({'i': 1}, {}, -1, {'i': 'INTEGER'})))
        self.assertTrue(((i - j)**2).is_equal((i - j)*(i - j)))
        self.assertTrue(((2*i + 4*i*j + 6) / 2.).is_equal(i + 2*i*j + 3))

    def test_expression_mixed_smoke(self):
        i = Integer('i')
        j = Integer('j')
        x = Binary('x')
        y = Binary('y')
        s = Spin('s')
        t = Spin('t')

        exp = i + j + x + y + s + t + i*j + s*i + x*j + (s + 1)*(1 - j)


class TestViews(unittest.TestCase):
    @parameterized.expand([(np.float32,), (np.float64,)])
    def test_empty(self, dtype):
        qm = QM(dtype=dtype)
        self.assertEqual(qm.linear, {})
        self.assertEqual(qm.quadratic, {})
        self.assertEqual(qm.adj, {})

    @parameterized.expand([(np.float32,), (np.float64,)])
    def test_linear(self, dtype):
        qm = QM(dtype=dtype)
        qm.add_variable('INTEGER', 'a')
        qm.add_variable('SPIN', 'b')
        qm.add_variable('BINARY', 'c')

        self.assertEqual(qm.linear, {'a': 0, 'b': 0, 'c': 0})
        self.assertEqual(qm.quadratic, {})
        self.assertEqual(qm.adj, {'a': {}, 'b': {}, 'c': {}})

    @parameterized.expand([(np.float32,), (np.float64,)])
    def test_quadratic(self, dtype):
        qm = QM(dtype=dtype)
        qm.add_variable('INTEGER', 'a')
        qm.add_variable('SPIN', 'b')
        qm.add_variable('BINARY', 'c')

        qm.set_quadratic('a', 'b', 1)
        qm.set_quadratic('b', 'c', 2)

        self.assertEqual(qm.linear, {'a': 0, 'b': 0, 'c': 0})
        self.assertEqual(qm.quadratic, {'ab': 1, 'bc': 2})
        self.assertEqual(qm.adj, {'a': {'b': 1}, 'b': {'a': 1, 'c': 2}, 'c': {'b': 2}})

    def test_min_max_sum(self):
        qm = QM()
        i = qm.add_variable('INTEGER')
        j = qm.add_variable('INTEGER')
        x = qm.add_variable('BINARY')

        qm.set_linear(i, 1.5)
        qm.set_linear(x, -2)

        qm.set_quadratic(i, j, 1)
        qm.set_quadratic(j, j, 5)
        qm.set_quadratic(x, i, 7)

        self.assertEqual(qm.linear.max(), 1.5)
        self.assertEqual(qm.linear.min(), -2)
        self.assertEqual(qm.linear.sum(), -.5)

        self.assertEqual(qm.quadratic.max(), 7)
        self.assertEqual(qm.quadratic.min(), 1)
        self.assertEqual(qm.quadratic.sum(), 13)

        self.assertEqual(qm.adj[j].max(), 5)
        self.assertEqual(qm.adj[j].min(), 1)
        self.assertEqual(qm.adj[j].sum(), 6)
