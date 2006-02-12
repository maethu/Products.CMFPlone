#
# Test id autogeneration related scripts
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from Products.PloneTestCase import PloneTestCase
from Products.PloneTestCase import dummy
PloneTestCase.setupPloneSite()

from AccessControl import Unauthorized
from ZODB.POSException import ConflictError


class TestIsIDAutoGenerated(PloneTestCase.PloneTestCase):
    '''Tests the isIDAutoGenerated script'''

    def testAutoGeneratedId(self):
        r = self.portal.plone_utils.isIDAutoGenerated('document.2004-11-09.0123456789')
        self.assertEqual(r, True)

    def testEmptyId(self):
        r = self.portal.plone_utils.isIDAutoGenerated('')
        self.assertEqual(r, False)

    def testValidPortalTypeNameButNotAutoGeneratedId(self):
        # This was raising an IndexError exception for
        # Zope < 2.7.3 (DateTime.py < 1.85.12.11) and a
        # SyntaxError for Zope >= 2.7.3 (DateTime.py >= 1.85.12.11)
        r = self.portal.plone_utils.isIDAutoGenerated('document.tar.gz')
        self.assertEqual(r, False)
        # check DateError
        r = self.portal.plone_utils.isIDAutoGenerated('document.tar.12/32/2004')
        self.assertEqual(r, False)
        # check TimeError
        r = self.portal.plone_utils.isIDAutoGenerated('document.tar.12/31/2004 12:62')
        self.assertEqual(r, False)


class TestCheckId(PloneTestCase.PloneTestCase):
    '''Tests the check_id script'''

    def testGoodId(self):
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testEmptyId(self):
        r = self.folder.check_id('')
        self.assertEqual(r, None)   # success

    def testRequiredId(self):
        r = self.folder.check_id('', required=1)
        self.assertEqual(r, "Please enter a name.")

    def testAlternativeId(self):
        r = self.folder.check_id('', alternative_id='foo')
        self.assertEqual(r, None)   # success

    def testBadId(self):
        r = self.folder.check_id('=')
        #self.assertEqual(r, "'=' is not a legal name.")
        self.assertEqual(r, "'=' is not a legal name. The following characters are invalid: =")

    def testCatalogIndex(self):
        # TODO: Tripwire
        have_permission = self.portal.portal_membership.checkPermission
        self.failUnless(have_permission('Search ZCatalog', self.portal.portal_catalog),
                        'Expected permission "Search ZCatalog"')

        r = self.folder.check_id('created')
        self.assertEqual(r, "'created' is reserved.")

    def testCollision(self):
        self.folder.invokeFactory('Document', id='foo')
        self.folder.invokeFactory('Document', id='bar')
        r = self.folder.foo.check_id('bar')
        self.assertEqual(r, "There is already an item named 'bar' in this folder.")

    def testTempObjectCollision(self):
        foo = self.folder.restrictedTraverse('portal_factory/Document/foo')
        self.folder._setObject('bar', dummy.Item('bar'))
        r = foo.check_id('bar')
        self.assertEqual(r, "'bar' is reserved.")

    def testReservedId(self):
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('portal_catalog')
        self.assertEqual(r, "'portal_catalog' is reserved.")

    def testHiddenObjectId(self):
        # If a parallel object is not in content-space, should get 'reserved'
        # instead of 'taken'
        r = self.folder.check_id('portal_skins')
        self.assertEqual(r, "'portal_skins' is reserved.")

    def testCanOverrideParentNames(self):
        self.folder.invokeFactory('Document', id='item1')
        self.folder.invokeFactory('Folder', id='folder1')
        self.folder.invokeFactory('Document', id='foo')
        r = self.folder.folder1.foo.check_id('item1')
        self.assertEqual(r, None)

    def testInvalidId(self):
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('_foo')
        self.assertEqual(r, "'_foo' is reserved.")

    def testContainerHook(self):
        # Container may have a checkValidId method; make sure it is called
        self.folder._setObject('checkValidId', dummy.Raiser(dummy.Error))
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('whatever')
        self.assertEqual(r, "'whatever' is reserved.")

    def testContainerHookRaisesUnauthorized(self):
        # check_id should not swallow Unauthorized errors raised by hook
        self.folder._setObject('checkValidId', dummy.Raiser(Unauthorized))
        self.folder._setObject('foo', dummy.Item('foo'))
        self.assertRaises(Unauthorized, self.folder.foo.check_id, 'whatever')

    def testContainerHookRaisesConflictError(self):
        # check_id should not swallow ConflictErrors raised by hook
        self.folder._setObject('checkValidId', dummy.Raiser(ConflictError))
        self.folder._setObject('foo', dummy.Item('foo'))
        self.assertRaises(ConflictError, self.folder.foo.check_id, 'whatever')

    def testMissingUtils(self):
        # check_id should not bomb out if the plone_utils tool is missing
        self.portal._delObject('plone_utils')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testMissingCatalog(self):
        # check_id should not bomb out if the portal_catalog tool is missing
        self.portal._delObject('portal_catalog')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testMissingFactory(self):
        # check_id should not bomb out if the portal_factory tool is missing
        self.portal._delObject('portal_factory')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testCatalogIndexSkipped(self):
        # Note that the check is skipped when we don't have
        # the "Search ZCatalogs" permission.
        self.portal.manage_permission('Search ZCatalog', ['Manager'], acquire=0)

        r = self.folder.check_id('created')
        #self.assertEqual(r, None)   # success

        # But now the final hasattr check picks this up
        self.assertEqual(r, "'created' is reserved.")   # success

    def testCollisionSkipped(self):
        # Note that check is skipped when we don't have
        # the "Access contents information" permission.
        self.folder.manage_permission('Access contents information', ['Manager'], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        self.folder._setObject('bar', dummy.Item('bar'))
        r = self.folder.foo.check_id('bar')
        self.assertEqual(r, None)   # success

    def testReservedIdSkipped(self):
        # This check is picked up by the checkIdAvailable, unless we don't have
        # the "Add portal content" permission, in which case it is picked up by
        # the final hasattr check.
        self.folder.manage_permission('Add portal content', ['Manager'], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('portal_catalog')
        self.assertEqual(r, "'portal_catalog' is reserved.")   # success

    def testInvalidIdSkipped(self):
        # Note that the check is skipped when we don't have
        # the "Add portal content" permission.
        self.folder.manage_permission('Add portal content', ['Manager'], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('_foo')
        self.assertEqual(r, None)   # success


    def testParentMethodAliasDisallowed(self):
        # Note that the check is skipped when we don't have
        # the "Add portal content" permission.
        self.folder.manage_permission('Add portal content', ['Manager'], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        for alias in self.folder.getTypeInfo().getMethodAliases().keys():
            r = self.folder.foo.check_id(alias)
            self.assertEqual(r, "'%s' is reserved." % alias)   # success

    def testCheckingMethodAliasesOnPortalRoot(self):
        # Test for bug http://dev.plone.org/plone/ticket/4351
        self.setRoles(['Manager'])
        self.portal.manage_permission('Add portal content', ['Manager'], acquire=0)

        # Should not raise: Before we were using obj.getTypeInfo(), which is
        # not defined on the portal root.
        try:
            self.portal.check_id('foo')
        except AttributeError, e:
            self.fail(e)


class TestVisibleIdsEnabled(PloneTestCase.PloneTestCase):
    '''Tests the visibleIdsEnabled script'''

    def testVisibleIdsEnabledFailsWithSitePropertyDisabled(self):
        member = self.portal.portal_membership.getAuthenticatedMember()
        props = self.portal.portal_properties.site_properties
        # Set baseline
        member.manage_changeProperties(visible_ids=False)
        props.manage_changeProperties(visible_ids=False)
        # Should fail when site property is set false
        self.failIf(self.portal.visibleIdsEnabled())
        member.manage_changeProperties(visible_ids=True)
        self.failIf(self.portal.visibleIdsEnabled())

    def testVisibleIdsEnabledFailsWithMemberPropertyDisabled(self):
        member = self.portal.portal_membership.getAuthenticatedMember()
        props = self.portal.portal_properties.site_properties
        # Should fail when member property is false
        member.manage_changeProperties(visible_ids=False)
        props.manage_changeProperties(visible_ids=True)
        self.failIf(self.portal.visibleIdsEnabled())

    def testVisibleIdsEnabledFailsWithMemberPropertyDisabled(self):
        member = self.portal.portal_membership.getAuthenticatedMember()
        props = self.portal.portal_properties.site_properties
        # Should succeed only when site property and member property are true
        props.manage_changeProperties(visible_ids=True)
        member.manage_changeProperties(visible_ids=True)
        self.failUnless(self.portal.visibleIdsEnabled())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCheckId))
    suite.addTest(makeSuite(TestIsIDAutoGenerated))
    suite.addTest(makeSuite(TestVisibleIdsEnabled))
    return suite

if __name__ == '__main__':
    framework()
