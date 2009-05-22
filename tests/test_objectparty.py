#!/usr/bin/python

import unittest
import weakref
import simplejson
import uuid

class Reference(object):
    def __init__(self, referent):
        self.referent = weakref.proxy(referent)

class Base(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.__dict__['__class__'] = self.__class__.__name__

class Person(Base):
    pass

class ObjectParty(object):
    def __init__(self):
        self._storage = {}
        self._id_uuid = {}
        self._seen_ids = []

    def mk_id(self):
        return str(uuid.uuid4())

    def _encode_object(self, obj):
        # instead of modifying the original object, we should create a map of
        # the real objects' id() (the python builtin) to storage uuids

        if not obj.__dict__.get('id'):
            obj.id = self.mk_id()

        self._seen_ids.append(obj.id)

        def object_encoder(o):
            # we're serializing a reference
            if isinstance(o, Reference):
                refid = o.referent.__dict__.get('id')

                if not refid or (refid not in self._seen_ids and refid not in self._storage):
                    refid = o.referent.id = self.mk_id()
                    self._encode_store(o.referent)

                return { "$ref": refid }

            # we're serializing an object
            _data = o.__dict__.copy()
            for k in _data:
                v = _data[k]

                if isinstance(v, Reference):
                    refid = v.referent.__dict__.get('id')

                    if not refid or (refid not in self._seen_ids and refid not in self._storage):
                        refid = v.referent.id = self.mk_id()
                        self._encode_object(v.referent)

                    _data[k] = { "$ref": refid }

            return _data

        self._storage[obj.id] = simplejson.dumps(obj, default=object_encoder)
        return obj.id

    def store(self, obj):
        self._seen_ids = []
        encobj = self._encode_object(obj)
        return encobj

    def get_undecoded(self, id):
        return self._storage[id]

class TestObjectParty(unittest.TestCase):
    def test_simple(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        marge = Person(name='Marge')
        homer.spouse = Reference(marge)
        marge.spouse = Reference(homer)

        homerdict=homer.__dict__.copy();

        p.store(homer)

        homerobj = simplejson.loads(p.get_undecoded(homer.id))
        margeobj = simplejson.loads(p.get_undecoded(marge.id))

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


        p.store(bart)

        import pprint
        for k in p._storage:
            print "%s:\n\n%s\n\n" % (k, pprint.pformat(simplejson.loads(p.get_undecoded(k))))
        print pprint.pformat(p._storage)
