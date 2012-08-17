# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from datetime import datetime, timedelta, tzinfo
import logging
import pickle
import sys
import unittest

import mox

from remoteobjects import fields, dataobject
from tests import utils


class TestDataObjects(unittest.TestCase):

    cls = dataobject.DataObject

    def test_basic(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost.from_dict({ 'name': 'foo', 'value': '4' })
        self.assert_(b, 'from_dict() returned something True')
        self.assertEquals(b.name, 'foo', 'from_dict() result has correct name')
        self.assertEquals(b.value, '4', 'from_dict() result has correct value')

        b = BasicMost(name='bar', value='47').to_dict()
        self.assert_(b, 'to_dict() returned something True')
        self.assertEquals({ 'name': 'bar', 'value': '47' }, b, 'Basic dict has proper contents')

        self.assertEquals(BasicMost.__name__, 'BasicMost',
            "metaclass magic didn't break our class's name")

        bm = BasicMost(name='fred', value=2)
        bm.api_data = {"name": "fred", "value": 2}
        bm_dict = bm.to_dict()
        self.assertEquals({ 'name': 'fred', 'value': 2 }, bm_dict, 'First go-round has proper contents')
        bm.name = 'tom'
        bm_dict = bm.to_dict()
        self.assertEquals({ 'name': 'tom', 'value': 2 }, bm_dict, 'Setting name to another string works')
        bm.name = None
        bm_dict = bm.to_dict()
        self.assertEquals({ 'value': 2 }, bm_dict, 'Setting name to None works, and name is omitted in the dict')

    def test_descriptorwise(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost()
        b.name = 'hi'
        self.assertEquals(b.name, 'hi')

        del b.name
        self.assert_(b.name is None)

    def test_types(self):

        class WithTypes(self.cls):
            name  = fields.Field()
            value = fields.Field()
            when  = fields.Datetime()

        w = WithTypes.from_dict({
            'name': 'foo',
            'value': 4,
            'when': '2008-12-31T04:00:01Z',
        })
        self.assert_(w, 'from_dict returned something True')
        self.assertEquals(w.name, 'foo', 'Typething got the right name')
        self.assertEquals(w.value, 4, 'Typething got the right value')
        self.assertEquals(w.when, datetime(2008, 12, 31, 4, 0, 1,
            tzinfo=fields.Datetime.utc),
            'Typething got something like the right when')

        w = WithTypes.from_dict({
            'name': 'bar',
            'value': 99,
            'when': '2012-08-17T14:49:50-05:00'
        })

        self.assertEquals(w.when, datetime(2012, 8, 17, 19, 49, 50,
            tzinfo=fields.Datetime.utc),
            'Non-UTC timezone was parsed and converted to UTC')

        w = WithTypes.from_dict({
            'when': '2012-13-01T24:01:01-05:00'
        })

        try:
            w.when
            self.fail('No TypeError parsing invalid, well-formatted timestamp')
        except TypeError:
            pass
        except Exception:
            self.fail('No TypeError parsing invalid, well-formatted timestamp')

        w = WithTypes.from_dict({
            'when': 'pack my bag with six dozen liquor jugs'
        })

        try:
            w.when
            self.fail('No TypeError parsing malformatted timestamp')
        except TypeError:
            pass
        except Exception:
            self.fail('No TypeError parsing malformatted timestamp')

        w = WithTypes(name='hi', value=99, when=datetime(2009, 2, 3, 10, 44, 0, tzinfo=None)).to_dict()
        self.assert_(w, 'to_dict() returned something True')
        self.assertEquals(w, { 'name': 'hi', 'value': 99, 'when': '2009-02-03T10:44:00Z' },
            'Typething dict has proper contents')

    def test_must_ignore(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost.from_dict({
            'name':   'foo',
            'value':  '4',
            'secret': 'codes',
        })

        self.assert_(b)
        self.assert_(b.name)
        self.assertRaises(AttributeError, lambda: b.secret)

        d = b.to_dict()
        self.assert_('name' in d)
        self.assert_('secret' in d)
        self.assertEquals(d['secret'], 'codes')

        d['blah'] = 'meh'
        d = b.to_dict()
        self.assert_('blah' not in d)

        x = BasicMost.from_dict({
            'name':  'foo',
            'value': '4',
        })
        self.assertNotEqual(id(b), id(x))
        self.assert_(x)
        self.assert_(x.name)

        x.update_from_dict({ 'secret': 'codes' })
        self.assertRaises(AttributeError, lambda: x.secret)

        d = x.to_dict()
        self.assert_('name' not in d)
        self.assert_('secret' in d)
        self.assertEquals(d['secret'], 'codes')

    def test_spooky_action(self):
        """Tests that an instance's content can't be changed through the data
        structures it was created with, or a data structure pulled out of
        it."""

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        initial = {
            'name': 'foo',
            'value': '4',
            'secret': {
                'code': 'uuddlrlrba'
            },
        }
        x = BasicMost.from_dict(initial)

        initial['name'] = 'bar'
        self.assertEquals(x.name, 'bar',
            "Changing initial data does change instance's "
            "internal data")

        initial['secret']['code'] = 'steak'
        d = x.to_dict()
        self.assertEquals(d['secret']['code'], 'steak',
            "Changing deep hidden initial data *does* change instance's "
            "original data for export")

        d['name'] = 'baz'
        self.assertEquals(x.name, 'bar',
            "Changing shallow exported data doesn't change instance's "
            "internal data retroactively")

        d['secret']['code'] = 'walt sent me'
        self.assertEquals(x.to_dict()['secret']['code'], 'steak',
            "Changing deep exported data doesn't change instance's "
            "internal data retroactively")

    def test_strong_types(self):

        class Blah(self.cls):
            name = fields.Field()

        class WithTypes(self.cls):
            name  = fields.Field()
            value = fields.Field()
            when  = fields.Datetime()
            bleh  = fields.Object(Blah)

        testobj = WithTypes.from_dict({
            'name':  'foo',
            'value': 4,
            'when':  'magenta',
            'bleh':  {'name': 'what'},
        })

        self.assertRaises(TypeError, lambda: testobj.when)
        self.assert_(testobj.bleh, 'Accessing properly formatted subobject raises no exceptions')

        testobj = WithTypes.from_dict({
            'name':  'foo',
            'value': 4,
            'when':  '2008-12-31T04:00:01Z',
            'bleh':  True,
        })

        self.assert_(testobj.when, 'Accessing properly formatted datetime attribute raises no exceptions')
        self.assertRaises(TypeError, lambda: testobj.bleh)

    def test_complex(self):

        class Childer(self.cls):
            name = fields.Field()

        class Parentish(self.cls):
            name     = fields.Field()
            children = fields.List(fields.Object(Childer))

        p = Parentish.from_dict({
            'name': 'the parent',
            'children': [
                { 'name': 'fredina' },
                { 'name': 'billzebub' },
                { 'name': 'wurfledurf' },
            ],
        })

        self.assert_(p, 'from_dict() returned something True for a parent')
        self.assertEquals(p.name, 'the parent', 'parent has correct name')
        self.assert_(p.children, 'parent has some children')
        self.assert_(isinstance(p.children, list), 'children set is a Python list')
        self.assertEquals(len(p.children), 3, 'parent has 3 children')
        f, b, w = p.children
        self.assert_(isinstance(f, Childer), "parent's first child is a Childer")
        self.assert_(isinstance(b, Childer), "parent's twoth child is a Childer")
        self.assert_(isinstance(w, Childer), "parent's third child is a Childer")
        self.assertEquals(f.name, 'fredina', "parent's first child is named fredina")
        self.assertEquals(b.name, 'billzebub', "parent's twoth child is named billzebub")
        self.assertEquals(w.name, 'wurfledurf', "parent's third child is named wurfledurf")

        childs = Childer(name='jeff'), Childer(name='lisa'), Childer(name='conway')
        p = Parentish(name='molly', children=childs).to_dict()
        self.assert_(p, 'to_dict() returned something True')
        self.assertEquals(p, {
            'name': 'molly',
            'children': [
                { 'name': 'jeff' },
                { 'name': 'lisa' },
                { 'name': 'conway' },
            ],
        }, 'Parentish dict has proper contents')

        p = Parentish.from_dict({
            'name': 'the parent',
            'children': None
        })

        self.assertEquals(p.children, None)

    def test_complex_dict(self):

        class Thing(self.cls):
            name     = fields.Field()
            attributes = fields.Dict(fields.Field())

        t = Thing.from_dict({
            'name': 'the thing',
            'attributes': None,
        })

        self.assertEquals(t.attributes, None)


    def test_self_reference(self):

        class Reflexive(self.cls):
            itself     = fields.Object('Reflexive')
            themselves = fields.List(fields.Object('Reflexive'))

        r = Reflexive.from_dict({
            'itself': {},
            'themselves': [ {}, {}, {} ],
        })

        self.assert_(r)
        self.assert_(isinstance(r, Reflexive))
        self.assert_(isinstance(r.itself, Reflexive))
        self.assert_(isinstance(r.themselves[0], Reflexive))

    def test_post_reference(self):

        from tests import extra_dataobject

        class Referencive(extra_dataobject.Referencive):
            pass

        class Related(extra_dataobject.Related):
            pass

        class NotRelated(extra_dataobject.OtherRelated):
            pass

        r = Referencive.from_dict({ 'related': {}, 'other': {} })

        self.assert_(isinstance(r, Referencive))
        self.assert_(isinstance(r.related, Related))  # not extra_dataobject.Related
        self.assert_(isinstance(r.other,   extra_dataobject.OtherRelated))  # not NotRelated

        r = extra_dataobject.Referencive.from_dict({ 'related': {}, 'other': {} })

        self.assert_(isinstance(r, extra_dataobject.Referencive))
        self.assert_(isinstance(r.related, Related))  # not extra_dataobject.Related
        self.assert_(isinstance(r.other,   extra_dataobject.OtherRelated))  # not NotRelated

    def set_up_pickling_class(self):
        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        # Simulate a special module for this BasicMost, so pickle can find
        # the class for it.
        pickletest_module = mox.MockAnything()
        pickletest_module.BasicMost = BasicMost
        # Note this pseudomodule has no file, so coverage doesn't get a mock
        # method by mistake.
        pickletest_module.__file__ = None
        BasicMost.__module__ = 'remoteobjects._pickletest'
        sys.modules['remoteobjects._pickletest'] = pickletest_module

        return BasicMost

    def test_pickling(self):

        BasicMost = self.set_up_pickling_class()

        obj = BasicMost(name='fred', value=7)

        pickled_obj = pickle.dumps(obj)
        self.assert_(pickled_obj)
        unpickled_obj = pickle.loads(pickled_obj)
        self.assertEquals(unpickled_obj, obj)

        obj = BasicMost.from_dict({'name': 'fred', 'value': 7})

        cloned_obj = pickle.loads(pickle.dumps(obj))
        self.assert_(cloned_obj)
        self.assert_(hasattr(cloned_obj, 'api_data'), "unpickled instance has api_data too")
        self.assertEquals(cloned_obj.api_data, obj.api_data,
            "unpickled instance kept original's api_data")

    def test_field_override(self):

        class Parent(dataobject.DataObject):
            fred = fields.Field()
            ted  = fields.Field()

        class Child(Parent):
            ted = fields.Datetime()

        self.assert_('fred' in Child.fields, 'Child class inherited the fred field')
        self.assert_('ted'  in Child.fields, 'Child class has a ted field (from somewhere')
        self.assert_(isinstance(Child.fields['ted'], fields.Datetime),
            'Child class has overridden ted field, yay')

    def test_field_api_name(self):

        class WeirdNames(dataobject.DataObject):
            normal    = fields.Field()
            fooBarBaz = fields.Field(api_name='foo-bar-baz')
            xyzzy     = fields.Field(api_name='plugh')

        w = WeirdNames.from_dict({
            'normal': 'asfdasf',
            'foo-bar-baz': 'wurfledurf',
            'plugh':       'http://en.wikipedia.org/wiki/Xyzzy#Poor_password_choice',
        })

        self.assertEquals(w.normal,    'asfdasf', 'normal value carried through')
        self.assertEquals(w.fooBarBaz, 'wurfledurf', 'fbb value carried through')
        self.assertEquals(w.xyzzy,     'http://en.wikipedia.org/wiki/Xyzzy#Poor_password_choice',
            'xyzzy value carried through')

        w = WeirdNames(normal='gloing', fooBarBaz='grumdabble', xyzzy='slartibartfast')
        d = w.to_dict()

        self.assert_(d, 'api_named to_dict() returned something True')
        self.assertEquals(d, {
            'normal':      'gloing',
            'foo-bar-baz': 'grumdabble',
            'plugh':       'slartibartfast',
        }, 'WeirdNames dict has proper contents')

    def test_field_default(self):

        global cheezCalled
        cheezCalled = False

        def cheezburgh(obj):
            self.assert_(isinstance(obj, WithDefaults))
            global cheezCalled
            cheezCalled = True
            return 'CHEEZBURGH'

        class WithDefaults(dataobject.DataObject):
            plain               = fields.Field()
            itsAlwaysSomething  = fields.Field(default=7)
            itsUsuallySomething = fields.Field(default=cheezburgh)

        w = WithDefaults.from_dict({
            'plain': 'awesome',
            'itsAlwaysSomething': 'haptics',
            'itsUsuallySomething': 'omg hi',
        })

        self.assertEquals(w.plain, 'awesome')
        self.assertEquals(w.itsAlwaysSomething, 'haptics')
        self.assertEquals(w.itsUsuallySomething, 'omg hi')
        self.failIf(cheezCalled)

        for x in (WithDefaults.from_dict({}), WithDefaults()):
            self.assert_(x.plain is None)
            self.assertEquals(x.itsAlwaysSomething, 7)
            self.assertEquals(x.itsUsuallySomething, 'CHEEZBURGH')
            self.assert_(cheezCalled)

        d = WithDefaults().to_dict()
        self.assert_('plain' not in d)
        self.assertEquals(d['itsAlwaysSomething'], 7)
        self.assertEquals(d['itsUsuallySomething'], 'CHEEZBURGH')

    def test_field_constant(self):

        noninconstant = 'liono'

        class WithConstant(dataobject.DataObject):
            alwaysTheSame = fields.Constant(noninconstant)

        d = WithConstant().to_dict()
        self.assertEquals(d['alwaysTheSame'], noninconstant)

        x = WithConstant()
        self.assertEquals(x.alwaysTheSame, noninconstant)

        try:
            x.alwaysTheSame = 'snarf'
        except ValueError:
            pass
        else:
            self.fail('Set Constant field to invalid value.')
        x.alwaysTheSame = noninconstant

        # Just to make sure
        self.assertEquals(x.alwaysTheSame, noninconstant)

    def test_field_link(self):

        class Frob(dataobject.DataObject):
            blerg = fields.Field()

        class WithLink(dataobject.DataObject):
            link = fields.Link(Frob)

        x = WithLink()
        x.link = Frob()
        # Links don't serialize... for now anyways.
        self.assertEquals(x.to_dict(), {})

    def test_forwards_link(self):
        class Foo(dataobject.DataObject):
            link = fields.Link('Bar')

        class Bar(dataobject.DataObject):
            thing = fields.Field()

        # The string class name should be converted to the class
        self.assertEquals(Foo.__dict__["link"].cls, Bar)

    def test_field_datetime(self):

        class Timely(dataobject.DataObject):
            when = fields.Datetime()

        t = Timely.from_dict({
            'when': '2008-12-31T04:00:01Z',
        })

        self.assert_(isinstance(t, Timely), 'Datetime class decoded properly')
        self.assert_(isinstance(t.when, datetime), 'Datetime data decoded into a datetime')
        when = datetime(year=2008, month=12, day=31, hour=4, minute=0, second=1,
                tzinfo=fields.Datetime.utc)
        self.assertEquals(t.when, when, 'Datetime data decoded into the expected datetime')
        self.assert_(t.when.tzinfo is fields.Datetime.utc, 
                'Datetime data decoded with utc timezone info')

        when = datetime(year=2010, month=2, day=11, hour=4, minute=37, second=44)
        t_data = Timely(when=when).to_dict()
        self.assert_(isinstance(t_data, dict), 'Datetime dict encoded properly')
        self.assertEquals(t_data['when'], '2010-02-11T04:37:44Z', 'Datetime dict encoded with expected timestamp')

        when = datetime(year=2010, month=2, day=11, hour=4, minute=37,
                second=44, tzinfo=fields.Datetime.utc)
        t_data = Timely(when=when).to_dict()
        self.assert_(isinstance(t_data, dict), 'Datetime dict with UTC tzinfo encoded properly')
        self.assertEquals(t_data['when'], '2010-02-11T04:37:44Z', 'Datetime dict encoded with expected timestamp')

        class EST(tzinfo):

            def utcoffset(self, dt):
                return timedelta(hours=-5)

            def tzname(self, dt):
                return "UTC"

            def dst(self, dt):
                return timedelta(0)

        when = datetime(year=2010, month=2, day=10, hour=23, minute=37,
                second=44, tzinfo=EST())
        t_data = Timely(when=when).to_dict()
        self.assert_(isinstance(t_data, dict), 'Datetime dict with non-UTC tzinfo encoded properly')
        self.assertEquals(t_data['when'], '2010-02-11T04:37:44Z', 'Datetime dict encoded with expected timestamp')

        t = Timely.from_dict({
            'when': None,
        })
        self.assert_(isinstance(t, Timely), 'Datetime with None data decoded properly')
        self.assert_(t.when is None, 'Datetime with None data decoded to None timestamp')

        t = Timely.from_dict({})
        self.assert_(isinstance(t, Timely), 'Datetime with missing data decoded properly')
        self.assert_(t.when is None, 'Datetime with missing data decoded to None timestamp')


if __name__ == '__main__':
    utils.log()
    unittest.main()
