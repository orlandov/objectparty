#!/usr/bin/python

import unittest
import weakref
import simplejson
import uuid

class Reference(object):
    def __init__(self, referent):
        self.referent = weakref.proxy(referent)
        self.refid = None

class Person(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.__dict__['__class__'] = self.__class__.__name__

class ObjectParty(object):
    def __init__(self):
        self.storage = {}
        self._seen_ids=[]

    def store(self, obj):
        if not obj.__dict__.get('id'):
            obj.id = str(uuid.uuid4())

        self._seen_ids.append(obj.id)

        def reference_encoder(o):
            _data = o.__dict__

            for k in _data:
                v = _data[k]

                if isinstance(v, Reference):
                    try:
                        refid = v.referent.id
                    except:
                        refid = None

                    if refid and (refid in self._seen_ids or refid in self.storage):
                        print "found c"
                    else:
                        refid = self.store(v.referent)
                        v.referent.id = refid

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


        bart = Person(name='Bart')
        lisa = Person(name='Lisa')
        bart.father = Reference(homer)
        bart.mother = Reference(marge)
        lisa.father = Reference(homer)
        lisa.mother = Reference(marge)

        homer.children = [Reference(bart), Reference(lisa)]
        marge.children = [Reference(bart), Reference(lisa)]

        p.store(homer)
        p.store(bart)

        import pprint
        for k in p.storage:
            print "%s:\n\n%s\n\n" % (k, pprint.pformat(simplejson.loads(p.storage[k])))
        print pprint.pformat(p.storage)
