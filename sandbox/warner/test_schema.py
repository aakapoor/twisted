#! /usr/bin/python

from twisted.trial import unittest
import schema

class Dummy:
    pass

class CreateTest(unittest.TestCase):
    def conforms(self, c, obj):
        c.checkObject(obj)
    def violates(self, c, obj):
        self.assertRaises(schema.Violation, c.checkObject, obj)
    def assertSize(self, c, maxsize):
        self.assertEquals(c.maxSize(), maxsize)
    def assertDepth(self, c, maxdepth):
        self.assertEquals(c.maxDepth(), maxdepth)
    def assertUnboundedSize(self, c):
        self.assertRaises(schema.UnboundedSchema, c.maxSize)
    def assertUnboundedDepth(self, c):
        self.assertRaises(schema.UnboundedSchema, c.maxDepth)

    def testAny(self):
        c = schema.Constraint()
        self.assertUnboundedSize(c)
        self.assertUnboundedDepth(c)

    def testString(self):
        c = schema.StringConstraint(10)
        self.assertSize(c, 75)
        self.assertSize(c, 75)
        self.assertDepth(c, 1)
        self.conforms(c, "I'm short")
        self.violates(c, "I am too long")
        self.conforms(c, "a" * 10)
        self.violates(c, "a" * 11)
        self.violates(c, 123)
        self.violates(c, Dummy())
        self.violates(c, None)

    def testInteger(self):
        c = schema.IntegerConstraint()
        self.assertSize(c, 73)
        self.assertDepth(c, 1)
        self.conforms(c, 123)
        self.violates(c, 2**64)
        self.violates(c, "123")
        self.violates(c, Dummy())
        self.violates(c, None)
        
    def testBool(self):
        c = schema.BooleanConstraint()
        self.assertSize(c, 147)
        self.assertDepth(c, 2)
        self.conforms(c, False)
        self.conforms(c, True)
        self.violates(c, 0)
        self.violates(c, 1)
        self.violates(c, "vrai")
        self.violates(c, Dummy())
        self.violates(c, None)
        
    def testPoly(self):
        c = schema.PolyConstraint(schema.StringConstraint(100),
                                  schema.IntegerConstraint())
        self.assertSize(c, 165)
        self.assertDepth(c, 1)

    def testTuple(self):
        c = schema.TupleConstraint(schema.StringConstraint(10),
                                   schema.StringConstraint(100),
                                   schema.IntegerConstraint() )
        self.conforms(c, ("hi", "there buddy, you're number", 1))
        self.violates(c, "nope")
        self.violates(c, ("string", "string", "NaN"))
        self.violates(c, ("string that is too long", "string", 1))
        self.violates(c, ["Are tuples", "and lists the same?", 0])
        self.assertSize(c, 72+75+165+73)
        self.assertDepth(c, 2)

    def testNestedTuple(self):
        inner = schema.TupleConstraint(schema.StringConstraint(10),
                                       schema.IntegerConstraint())
        self.assertSize(inner, 72+75+73)
        self.assertDepth(inner, 2)
        outer = schema.TupleConstraint(schema.StringConstraint(100),
                                       inner)
        self.assertSize(outer, 72+165 + 72+75+73)
        self.assertDepth(outer, 3)

        self.conforms(inner, ("hi", 2))
        self.conforms(outer, ("long string here", ("short", 3)))
        self.violates(outer, (("long string here", ("short", 3, "extra"))))
        self.violates(outer, (("long string here", ("too long string", 3))))

        outer2 = schema.TupleConstraint(inner, inner)
        self.assertSize(outer2, 72+ 2*(72+75+73))
        self.assertDepth(outer2, 3)
        self.conforms(outer2, (("hi", 1), ("there", 2)) )
        self.violates(outer2, ("hi", 1, "flat", 2) )

    def testUnbounded(self):
        big = schema.StringConstraint(None)
        self.assertUnboundedSize(big)
        self.assertDepth(big, 1)
        self.conforms(big, "blah blah blah blah blah" * 1024)
        self.violates(big, 123)

        bag = schema.TupleConstraint(schema.IntegerConstraint(),
                                     big)
        self.assertUnboundedSize(bag)
        self.assertDepth(bag, 2)

        polybag = schema.PolyConstraint(schema.IntegerConstraint(),
                                        bag)
        self.assertUnboundedSize(polybag)
        self.assertDepth(polybag, 2)

    def testRecursion(self):
        # we have to fiddle with PolyConstraint's innards
        value = schema.ChoiceOf(schema.StringConstraint(),
                                schema.IntegerConstraint(),
                                # will add 'value' here
                                )
        self.assertSize(value, 1065)
        self.assertDepth(value, 1)
        self.conforms(value, "key")
        self.conforms(value, 123)
        self.violates(value, [])

        mapping = schema.TupleConstraint(schema.StringConstraint(10),
                                         value)
        self.assertSize(mapping, 72+75+1065)
        self.assertDepth(mapping, 2)
        self.conforms(mapping, ("name", "key"))
        self.conforms(mapping, ("name", 123))
        value.alternatives = value.alternatives + (mapping,)
        
        self.assertUnboundedSize(value)
        self.assertUnboundedDepth(value)
        self.assertUnboundedSize(mapping)
        self.assertUnboundedDepth(mapping)

        # but note that the constraint can still be applied
        self.conforms(mapping, ("name", 123))
        self.conforms(mapping, ("name", "key"))
        self.conforms(mapping, ("name", ("key", "value")))
        self.conforms(mapping, ("name", ("key", 123)))
        self.violates(mapping, ("name", ("key", [])))
        l = []
        l.append(l)
        self.violates(mapping, ("name", l))

    def testList(self):
        l = schema.ListOf(schema.StringConstraint(10))
        self.assertSize(l, 71 + 30*75)
        self.assertDepth(l, 2)
        self.conforms(l, ["one", "two", "three"])
        self.violates(l, ("can't", "fool", "me"))
        self.violates(l, ["but", "perspicacity", "is too long"])
        self.conforms(l, ["short", "sweet"])

        l2 = schema.ListOf(schema.StringConstraint(10), 3)
        self.assertSize(l2, 71 + 3*75)
        self.assertDepth(l2, 2)
        self.conforms(l2, ["the number", "shall be", "three"])
        self.violates(l2, ["five", "is", "...", "right", "out"])

