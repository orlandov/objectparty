#!/usr/bin/python

import unittest
import weakref
import simplejson
import uuid

class Reference(object):
    def __init__(self, referent):
        self._referent = weakref.ref(referent)

    @property
    def referent(self):
        return self._referent()

class ObjectParty(object):
    def __init__(self):
        self._storage = {}
        self._id_uuid = {}
        self._seen_uuids = [] # TODO: turn this into a Set

    def mk_id(self):
        return str(uuid.uuid4())

    def object_id(self, obj, **kwargs):
        # check if we have an id for this object, if not, create one and map
        # the object's id() (python buildin) value to the generated uuid
        obj_id = id(obj)
        uuid = self._id_uuid.get(obj_id)
        if not uuid and kwargs.get('create'):
            uuid = self.mk_id()
            self._id_uuid[obj_id] = uuid

        return uuid


    def _encode_object(self, obj):
        # instead of modifying the original object, we should create a map of
        # the real objects' id() (the python builtin) to storage uuids

        obj_uuid = self.object_id(obj, create=True)
        self._seen_uuids.append(obj_uuid)

        def object_encoder(o):
            # we're serializing a reference
            if isinstance(o, Reference):
                ref_uuid = self.object_id(o.referent)

                if not ref_uuid or (ref_uuid not in self._seen_uuids and ref_uuid not in self._storage):
                    ref_uuid = self.object_id(o.referent, create=True)
                    self._encode_object(o.referent)

                return { "$ref": ref_uuid }

            # we're serializing an object
            _data = o.__dict__.copy()
            for k in _data:
                v = _data[k]

                if isinstance(v, Reference):
                    ref_uuid = self.object_id(v.referent)

                    if not ref_uuid or (ref_uuid not in self._seen_uuids and ref_uuid not in self._storage):
                        ref_uuid = self.object_id(v.referent, create=True)
                        self._encode_object(v.referent)

                    _data[k] = { "$ref": ref_uuid }

            _data['id'] = self.object_id(o)
            return _data

        self._storage[obj_uuid] = simplejson.dumps(obj, default=object_encoder)
        return obj_uuid

    def store(self, obj):
        self._seen_ids = []
        encobj = self._encode_object(obj)
        return encobj

    def get_undecoded(self, id):
        return self._storage[id]


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
        homerobj = simplejson.loads(p.get_undecoded(homer_uuid))

        self.assert_(homerobj.has_key('id'))
        self.assert_(homerobj['name'], 'Homer')

    def test_one_reference(self):
        p = ObjectParty()

        homer = Person(name='Homer')
        bart = Person(name='Bart')

        homer.son = Reference(bart)

        homer_uuid = p.store(homer)
        bart_uuid = p.store(bart)

        homerobj = simplejson.loads(p.get_undecoded(homer_uuid))
        bartobj = simplejson.loads(p.get_undecoded(bart_uuid))

        self.assertEqual(homerobj['son']['$ref'], bartobj['id'])

        return

        marge = Person(name='Marge')
        homer.spouse = Reference(marge)
        marge.spouse = Reference(homer)

        homerdict=homer.__dict__.copy();


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


        p.store(homer)
        p.store(marge)
        p.store(bart)
        p.store(lisa)

        import pprint
        for k in p._storage:
            print "%s:\n\n%s\n\n" % (k, pprint.pformat(simplejson.loads(p.get_undecoded(k))))
        print pprint.pformat(p._storage)
