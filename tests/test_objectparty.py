#!/usr/bin/python

import pprint
import sys
import unittest
import weakref

sys.path.append('lib')

from simplejson import loads as jloads, dumps as jdumps

from objectparty import Reference, ObjectParty

class Base(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.__dict__['__class__'] = self.__class__.__name__

class Person(Base): pass

class Dog(Base): pass

class Flea(Base): pass

class TestObjectParty(unittest.TestCase):
    def pprint(self, obj):
        pprint.pprint(obj)

    def test_simple(self):
        p = ObjectParty()

        homer = Person(name='Homer')

        homer_uuid = p.store(homer)
        self.assertEqual(p.count(), 1)

        homerobj = p.get(homer_uuid, how='decoded')

        self.assert_(homerobj.has_key('id'))
        self.assert_(homerobj['name'], 'Homer')
        self.assertEqual(p.count(), 1)

    def test_implicitly_stored_reference(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        bart = Person(name='Bart')

        homer.son = Reference(bart)

        # bart should get stored implicitly
        homer_uuid = p.store(homer)
        self.assertEqual(p.count(), 2)

        homerobj = p.get(homer_uuid, how='decoded')

        bart_uuid = homerobj['son']['$ref']
        bartobj = p.get(bart_uuid, how='decoded')

        self.assertEqual(bartobj['name'], 'Bart')

        # store bart explicitly
        old_bart_uuid = bart_uuid
        bart_uuid = p.store(bart)
        bartobj = p.get(bart_uuid, how='decoded')
        self.assertEqual(p.count(), 2)

        self.assertEqual(bartobj['name'], 'Bart')
        self.assertEqual(old_bart_uuid, bart_uuid,
            "uuid after explicitly storing implicitly stored object")

    def test_mutually_referential(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        marge = Person(name='Marge')

        homer.spouse = Reference(marge)
        marge.spouse = Reference(homer)

        homer_uuid = p.store(homer)
        self.assertEqual(p.count(), 2)

        homerobj = p.get(homer_uuid, how='decoded')
        marge_uuid = homerobj['spouse']['$ref']

        margeobj = p.get(marge_uuid, how='decoded')

        # check that the references are pointing to each other properly
        self.assertEqual(homerobj['spouse']['$ref'], margeobj['id'])
        self.assertEqual(margeobj['spouse']['$ref'], homerobj['id'])

    def test_list_of_references(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        bart = Person(name='Bart')
        lisa = Person(name='Lisa')

        homer.children = [Reference(bart), Reference(lisa)]

        bart.father = Reference(homer)
        lisa.father = Reference(homer)

        homer_uuid = p.store(homer)
        self.assertEqual(p.count(), 3)

        homerobj = p.get(homer_uuid, how='decoded')
        child0_uuid = homerobj['children'][0]['$ref']
        child1_uuid = homerobj['children'][1]['$ref']

        child0_obj = p.get(child0_uuid, how='decoded')
        child1_obj = p.get(child1_uuid, how='decoded')

        self.assertEqual(child0_obj['name'], "Bart")
        self.assertEqual(child1_obj['name'], "Lisa")
        self.assertEqual(child0_obj['father']['$ref'], homer_uuid)
        self.assertEqual(child1_obj['father']['$ref'], homer_uuid)

    def test_non_reference_member_object(self):
        p = ObjectParty()
        bart = Person(name='Bart')
        lisa = Person(name='Lisa')

        dog = Dog(name="Santa's Little Helper")
        lisa.dog = bart.dog = dog

        bart_uuid = p.store(bart)

        # lisa not stored yet
        self.assertEqual(p.count(), 2)
        lisa_uuid = p.store(lisa)
        self.assertEqual(p.count(), 3)

        bart_obj = p.get(bart_uuid, how='decoded')
        lisa_obj = p.get(lisa_uuid, how='decoded')
        dog_obj = p.get(bart_obj['dog']['$ref'], how='decoded')

        self.assertEqual(dog_obj['name'], "Santa's Little Helper")
        self.assertEqual(bart_obj['dog']['$ref'], dog_obj['id'])
        self.assertEqual(lisa_obj['dog']['$ref'], dog_obj['id'])

    def test_list_non_reference_object(self):
        p = ObjectParty()
        flea0 = Flea()
        flea1 = Flea()

        dog = Dog(name="Santa's Little Helper")
        dog.fleas = [flea0, flea1]
        dog_uuid = p.store(dog)
        self.assertEqual(p.count(), 3)

        self.assertEqual(
            [ flea['$ref'] for flea in p.from_object(dog)['fleas'] ],
            [ p.from_object(flea)['id'] for flea in [flea0, flea1] ]
        )

    def test_silly(self):
        p = ObjectParty()
        p.debug = 1

        class C(object): pass
        class D(object): pass
        c = C()
        d = D()

        c.foo = [[[[[d]]]]]
        p.store(c)
        self.assertEqual(p.count(), 2)

        self.assertEqual(
            p.from_object(c)['foo'][0][0][0][0][0]['$ref'],
            p.from_object(d)['id']
        )
