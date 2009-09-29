# Copyright (c) 2009 Six Apart Ltd.
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

from datetime import datetime
import logging
import sys
import unittest

from remoteobjects import fields, dataobject
from tests import utils


class TestDataObjects(unittest.TestCase):

    cls = dataobject.DataObject


    def testBasic(self):

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


    def testTypes(self):

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
        self.assertEquals(w.when, datetime(2008, 12, 31, 4, 0, 1, tzinfo=None),
            'Typething got something like the right when')

        w = WithTypes(name='hi', value=99, when=datetime(2009, 2, 3, 10, 44, 0, tzinfo=None)).to_dict()
        self.assert_(w, 'to_dict() returned something True')
        self.assertEquals(w, { 'name': 'hi', 'value': 99, 'when': '2009-02-03T10:44:00Z' },
            'Typething dict has proper contents')


    def testMustIgnore(self):

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
        self.assert_('name' in d)
        self.assert_('secret' in d)
        self.assertEquals(d['secret'], 'codes')


    def testNoSpookyAction(self):
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
        self.assertEquals(x.name, 'foo',
            "Changing initial data doesn't change instance's internal data")

        initial['secret']['code'] = 'steak'
        d = x.to_dict()
        self.assertEquals(d['secret']['code'], 'uuddlrlrba',
            "Changing initial data doesn't change instance's original data "
            "for export")

        d['name'] = 'baz'
        self.assertEquals(x.name, 'foo',
            "Changing exported data doesn't change instance's internal data")


    def testStrongTypes(self):

        class Blah(self.cls):
            name = fields.Field()

        class WithTypes(self.cls):
            name  = fields.Field()
            value = fields.Field()
            when  = fields.Datetime()
            bleh  = fields.Object(Blah)

        testdata = ({
                'name':  'foo',
                'value': 4,
                'when':  'magenta',
                'bleh':  Blah(name='what'),
            }, {
                'name':  'foo',
                'value': 4,
                'when':  '2008-12-31T04:00:01Z',
                'bleh':  True,
            })

        for d in testdata:
            self.assertRaises(TypeError, lambda: WithTypes.from_dict(d))


    def testComplex(self):

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


    def testSelfReference(self):

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


    def testPostReference(self):

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


    def testFieldOverride(self):

        class Parent(dataobject.DataObject):
            fred = fields.Field()
            ted  = fields.Field()

        class Child(Parent):
            ted = fields.Datetime()

        self.assert_('fred' in Child.fields, 'Child class inherited the fred field')
        self.assert_('ted'  in Child.fields, 'Child class has a ted field (from somewhere')
        self.assert_(isinstance(Child.fields['ted'], fields.Datetime),
            'Child class has overridden ted field, yay')


    def testFieldApiName(self):

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


    def testFieldDefault(self):

        global cheezCalled
        cheezCalled = False

        def cheezburgh(obj, data):
            self.assert_(isinstance(obj, WithDefaults))
            self.assert_(isinstance(data, dict))
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

        x = WithDefaults.from_dict({})

        self.assert_(x.plain is None)
        self.assertEquals(x.itsAlwaysSomething, 7)
        self.assertEquals(x.itsUsuallySomething, 'CHEEZBURGH')
        self.assert_(cheezCalled)


if __name__ == '__main__':
    utils.log()
    unittest.main()
