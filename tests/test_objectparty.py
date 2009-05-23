#!/usr/bin/python

import unittest
import weakref
import sys

sys.path.append('lib')

from simplejson import loads as jloads, dumps as jdumps

from objectparty import Reference, ObjectParty

class Base(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.__dict__['__class__'] = self.__class__.__name__

class Person(Base): pass

class TestObjectParty(unittest.TestCase):
    def test_simple(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        homer_uuid = p.store(homer)
        homerobj = p.get(homer_uuid, how='decoded')

        self.assert_(homerobj.has_key('id'))
        self.assert_(homerobj['name'], 'Homer')

    def test_implicitly_store_reference(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        bart = Person(name='Bart')

        homer.son = Reference(bart)

        # should store bart implicitly
        homer_uuid = p.store(homer)
        homerobj = p.get(homer_uuid, how='decoded')

        bartuuid = homerobj['son']['$ref']
        bartobj = p.get(bartuuid, how='decoded')

        self.assertEqual(bartobj['name'], 'Bart')

    def Xtest(self):

        marge = Person(name='Marge')
        homer.spouse = Reference(marge)
        marge.spouse = Reference(homer)

        homerdict=homer.__dict__.copy();

        margeobj = jloads(p.get_undecoded(marge.id))

        # check that the references are pointing to each other properly
        self.assertEqual(homerobj['spouse']['$ref'], margeobj['id'])
        self.assertEqual(margeobj['spouse']['$ref'], homerobj['id'])

        # check that the original object wasn't modified
        # self.assertEqual(homer.__dict__, homerdict)

        bart = Person(name='Bart')
        lisa = Person(name='Lisa')
        homer.children = [Reference(bart), Reference(lisa)]
        marge.children = [Reference(bart), Reference(lisa)]

        
        bart.father = Reference(homer)
        bart.mother = Reference(marge)
        lisa.father = Reference(homer)
        lisa.mother = Reference(marge)


        p.store(homer)
        p.store(marge)
        p.store(bart)
        p.store(lisa)

        import pprint
        for k in p._storage:
            print "%s:\n\n%s\n\n" % (k, pprint.pformat(simplejson.loads(p.get_undecoded(k))))
        print pprint.pformat(p._storage)
