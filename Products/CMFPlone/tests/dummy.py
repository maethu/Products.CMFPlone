#
# Helper objects for the Plone test suite
#

# $Id$

import os

from zope.interface import Interface, implements
from zope.interface import Interface

from Products.CMFPlone.interfaces import INonStructuralFolder

from ComputedAttribute import ComputedAttribute
from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder as SimpleFolder
from ZPublisher.HTTPRequest import FileUpload

from Globals import package_home
from Products.CMFPlone.tests import GLOBALS
PACKAGE_HOME = package_home(GLOBALS)

TEXT = 'file data'
UTEXT = u'file data'
GIF = open(os.path.join(PACKAGE_HOME, os.pardir, 'tool.gif')).read()


class Dummy:
    '''General purpose dummy object'''

    def __init__(self, **kw):
        self.__dict__.update(kw)


class Item(SimpleItem):
    '''Dummy Item
       First-class Zope object. Can be _setObject'ed.
    '''

    id = 'dummy'
    meta_type = 'Dummy Item'

    def __init__(self, id=None, title=None, **kw):
        self.__dict__.update(kw)
        if id is not None:
            self.id = id
        if title is not None:
            self.title = title

class SizedItem(Item):
    '''Item maintaining a size'''

    size = 0

    def set_size(self, size):
        self.size = size

    def get_size(self):
        return self.size


class FieldStorage(object):
    def __init__(self, file, filename='testfile', headers=None):
        self.file = file
        if headers is None:
            headers = {}
        self.headers = headers
        self.filename = filename


class File(FileUpload):
    '''Dummy upload object
       Used to fake uploaded files.
    '''

    __allow_access_to_unprotected_subobjects__ = 1
    filename = 'dummy.txt'
    data = TEXT
    headers = {}

    def __init__(self, filename=None, data=None, headers=None):
        if filename is not None:
            self.filename = filename
        if data is not None:
            self.data = data
        if headers is not None:
            self.headers = headers

    def seek(self, *args): pass
    def tell(self, *args): return 1
    def read(self, *args): return self.data


class Image(File):
    '''Dummy image upload object
       Contains valid image data by default.
    '''

    filename = 'dummy.gif'
    data = GIF


class Folder(SimpleFolder):
    '''Dummy Folder
       First-class Zope object. Can be _setObject'ed.
    '''

    id = 'dummy_folder'
    meta_type = 'Dummy Folder'

    def __init__(self, id=None, title=None, **kw):
        self.__dict__.update(kw)
        if id is not None:
            self.id = id
        if title is not None:
            self.title = title


class NonStructuralFolder(Folder):
    '''Folder implementing the INonStructuralFolder interface'''
    implements(INonStructuralFolder)


class Error(Exception):
    '''Dummy exception'''


class Raiser(SimpleItem):
    '''Raises the stored exception when called'''

    exception = Error

    def __init__(self, exception=None):
        if exception is not None:
            self.exception = exception

    def __call__(self, *args, **kw):
        raise self.exception


class DefaultPage(Item):
    '''Helper for browserDefault tests'''

    def __init__(self, default=['test'], keys=['index_html']):
        self.keys = keys
        self.isPrincipiaFolderish = 1 # fake a folder
        self.set_default(default)

    def set_default(self, default, has_key=0):
        self.default_page = default
        if has_key:
            if type(default) == type(''):
                self.keys = [default]
            self.keys = default

    def has_key(self, key):
        return key in self.keys


class ImageComputedProps(Item):
    '''Helper for testing the imagePatch interaction with
    ComputedAttributes (which are used in Archetypes ImageField).
    '''

    def get_title(self):
        return getattr(self, '_title', '')

    title = ComputedAttribute(get_title, 1)

    def get_alt(self):
        return getattr(self, '_alt', '')

    alt = ComputedAttribute(get_alt, 1)

    def get_longdesc(self):
        return getattr(self, '_longdesc', '')

    longdesc = ComputedAttribute(get_longdesc, 1)


class IDummyUtility(Interface):
    pass


class DummyUtility(SimpleItem):
    implements(IDummyUtility)


class ICantBeDeleted(Interface):
    """A marker indicating that an object can't be deleted"""


def disallow_delete_handler(obj, event):
    obj.delete_attempted = True
    raise Exception, "You can't delete this!"
