#!python

import weakref

from simplejson import loads as jloads, dumps as jdumps
from uuid import uuid4

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

    def _encode_object(self, obj):
        obj_uuid = self.object_id(obj, create=True)
        self._seen_uuids.add(obj_uuid)

        # could this func be pulled out of here?
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

        self._storage[obj_uuid] = jdumps(obj, default=object_encoder)
        return obj_uuid

    def store(self, obj):
        self._seen_ids = set()
        encobj = self._encode_object(obj)
        return encobj

    def get(self, id, **kwargs):
        how = kwargs.get('how')

        if how == 'decoded':
            return jloads(self._storage[id])
        elif how == 'undecoded':
            return self._storage[id]

        raise RuntimeError("getting real objects back isn't yet supported")
