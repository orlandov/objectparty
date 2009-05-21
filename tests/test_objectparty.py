#!/usr/bin/python

import unittest
import weakref
import simplejson
import uuid

class Reference(object):
    def __init__(self, referent):
        self.referent = weakref.proxy(referent)


class Person(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.__dict__['__class__'] = self.__class__.__name__


class ObjectParty(object):
    def __init__(self):
        self.storage = {}
        self._seen_ids=[]

    def mk_id(self):
        return str(uuid.uuid4())

    def store(self, obj):
        if not obj.__dict__.get('id'):
            obj.id = self.mk_id()

        # _seen_ids is a brutal hax, plz 2 fix
        self._seen_ids.append(obj.id)

        def reference_encoder(o):
            # we're serializing a reference
            if isinstance(o, Reference):
                refid = o.referent.__dict__.get('id')

                if not refid or (refid not in self._seen_ids and refid not in self.storage):
                    refid = o.referent.id = self.mk_id()
                    self.store(o.referent)

                return { "$ref": refid }

            # we're serializing an object
            _data = o.__dict__
            for k in _data:
                v = _data[k]

                if isinstance(v, Reference):
                    refid = v.referent.__dict__.get('id')

                    if not refid or (refid not in self._seen_ids and refid not in self.storage):
                        refid = v.referent.id = self.mk_id()
                        self.store(v.referent)

                    _data[k] = { "$ref": refid }

            return _data

        self.storage[obj.id] = simplejson.dumps(obj, default=reference_encoder)
        return obj.id


class TestObjectParty(unittest.TestCase):
    def test_simple(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        marge = Person(name='Marge')
        homer.spouse = Reference(marge)
        marge.spouse = Reference(homer)

        p.store(homer)

        homerobj = simplejson.loads(p.storage[homer.id])
        margeobj = simplejson.loads(p.storage[marge.id])
        self.assertEqual(homerobj['spouse']['$ref'], margeobj['id'])
        self.assertEqual(margeobj['spouse']['$ref'], homerobj['id'])

        bart = Person(name='Bart')
        lisa = Person(name='Lisa')
        homer.children = [Reference(bart), Reference(lisa)]
        marge.children = [Reference(bart), Reference(lisa)]
        bart.father = Reference(homer)
        bart.mother = Reference(marge)
        lisa.father = Reference(homer)
        lisa.mother = Reference(marge)


        p.store(bart)

        import pprint
        for k in p.storage:
            print "%s:\n\n%s\n\n" % (k, pprint.pformat(simplejson.loads(p.storage[k])))
        print pprint.pformat(p.storage)
