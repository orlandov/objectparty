#!python

import weakref

from simplejson import loads as jloads, dumps as jdumps, JSONEncoder
from uuid import uuid4

class Reference(object):
    def __init__(self, referent):
        self._referent = weakref.ref(referent)

    @property
    def referent(self):
        return self._referent()

class Encoder(JSONEncoder):
    def __init__(self, db):
        JSONEncoder.__init__(self)
        self.db = db

    def encode_list(self, l):
        for (i, elem) in enumerate(l):
            if elem.__class__ in [str, int, float, None, True, False]: continue

            obj = self.encode_object(l[i])
            if isinstance(obj, dict) and obj.get('id'):
                l[i] = { "$ref": obj['id'] }
        return l

    def encode_object(self, o):
        if isinstance(o, list):
            return self.encode_list(o)

        obj_uuid = self.db.object_id(o, create=True)
        self.db._seen_uuids.add(obj_uuid)

        # we're serializing a reference
        if isinstance(o, Reference):
            ref_uuid = self.db.object_id(o.referent)

            if  not ref_uuid or \
               (    ref_uuid not in self.db._seen_uuids \
                and ref_uuid not in self.db._storage):
                ref_uuid = self.db.object_id(o.referent, create=True)
                self.encode_object(o.referent)

            return { "$ref": ref_uuid }

        # we're serializing an object
        _data = o.__dict__.copy()
        for k in _data:
            v = _data[k]

            if isinstance(v, Reference):
                ref_uuid = self.db.object_id(v.referent)

                if  not ref_uuid or \
                   (    ref_uuid not in self.db._seen_uuids \
                    and ref_uuid not in self.db._storage):
                    ref_uuid = self.db.object_id(v.referent, create=True)
                    self.encode_object(v.referent)

                _data[k] = { "$ref": ref_uuid }
            elif v.__class__ == list:
                _data[k] = self.encode_list(v)

            elif v.__class__ not in [str, int, float, dict, None,
                    True, False]:
                ref_uuid = self.db.object_id(v, create=True)
                self.encode_object(v)
                _data[k] = { "$ref": ref_uuid }

        _data['id'] = self.db.object_id(o, create=True)
        self.db._storage[obj_uuid] = self.encode(_data)
        return _data

    def default(self, obj):
        return self.encode_object(obj)

class ObjectParty(object):
    def __init__(self):
        self._storage = {}
        self._id_uuid = {}
        self._seen_uuids = set()

    def mk_id(self):
        return str(uuid4())

    def object_id(self, obj, **kwargs):
        obj_id = id(obj)
        uuid = self._id_uuid.get(obj_id)
        if not uuid and kwargs.get('create'):
            uuid = self.mk_id()
            self._id_uuid[obj_id] = uuid

        return uuid

    def store(self, obj):
        self._seen_ids = set()
        enc_obj = Encoder(self).encode(obj)
        obj_uuid = self.from_object(obj)['id']
        return obj_uuid

    def count(self):
        return len(self._storage)

    def get(self, id, **kwargs):
        how = kwargs.get('how')
        if how == 'decoded':
            return jloads(self._storage[id])
        elif how == 'undecoded':
            return self._storage[id]

        raise RuntimeError("getting real objects back isn't yet supported")

    def from_object(self, obj):
        return jloads(self._storage[self.uuid_from_id(obj)])

    def uuid_from_id(self, obj):
        return self._id_uuid[id(obj)]
