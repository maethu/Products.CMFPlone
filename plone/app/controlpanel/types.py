from plone.app.workflow.remap import remap_workflow
from plone.memoize.instance import memoize

from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

from Acquisition import aq_inner

from Products.CMFCore.utils import getToolByName
from Products.CMFEditions.setuphandlers import DEFAULT_POLICIES
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone import PloneMessageFactory as pmf
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


def format_description(text):
    # We expect the workflow to be a text of '- ' divided bullet points.
    return [s.strip() for s in text.split('- ') if s]


class TypesControlPanel(BrowserView):

    # Actions

    template = ViewPageTemplateFile('types.pt')

    @property
    @memoize
    def type_id(self):
        type_id = self.request.get('type_id', None)
        if type_id is None:
            type_id=''
        return type_id

    @property
    @memoize
    def fti(self):
        type_id = self.type_id
        portal_types = getToolByName(self.context, 'portal_types')
        return getattr(portal_types, type_id)

    def __call__(self):
        """Perform the update and redirect if necessary, or render the page
        """
        postback = True
        context = aq_inner(self.context)

        form = self.request.form
        submitted = form.get('form.submitted', False)
        save_button = form.get('form.button.Save', None) is not None
        cancel_button = form.get('form.button.Cancel', None) is not None
        type_id = form.get('old_type_id', None)

        if submitted and not cancel_button:
            if type_id:
                portal_types = getToolByName(self.context, 'portal_types')
                portal_repository = getToolByName(self.context,
                                                  'portal_repository')
                portal_properties = getToolByName(self.context,
                                                  'portal_properties')
                site_properties = getattr(portal_properties, 'site_properties')

                fti = getattr(portal_types, type_id)

                # Set FTI properties

                addable = form.get('addable', False)
                allow_discussion = form.get('allow_discussion', False)

                fti.manage_changeProperties(global_allow = bool(addable),
                                            allow_discussion = bool(allow_discussion))

                versionable = form.get('versionable', False)
                versionable_types = list(portal_repository.getVersionableContentTypes())
                if versionable and type_id not in versionable_types:
                    versionable_types.append(type_id)
                    # Add default versioning policies to the versioned type
                    for policy_id in DEFAULT_POLICIES:
                        portal_repository.addPolicyForContentType(type_id,
                                                                  policy_id)
                elif not versionable and type_id in versionable_types:
                    versionable_types.remove(type_id)
                portal_repository.setVersionableContentTypes(versionable_types)

                searchable = form.get('searchable', False)
                blacklisted = list(site_properties.getProperty('types_not_searched'))
                if searchable and type_id in blacklisted:
                    blacklisted.remove(type_id)
                elif not searchable and type_id not in blacklisted:
                    blacklisted.append(type_id)
                site_properties.manage_changeProperties(types_not_searched = \
                                                        blacklisted)

            # Update workflow

            if self.have_new_workflow() and \
               form.get('form.workflow.submitted', False) and \
               save_button:
                if self.new_workflow_is_different():
                    new_wf = self.new_workflow()
                    if new_wf == '[none]':
                        chain = ()
                    elif new_wf == '(Default)':
                        chain = new_wf
                    else:
                        chain = (new_wf,)
                    state_map = dict([(s['old_state'], s['new_state']) for s in \
                                      form.get('new_wfstates', [])])
                    if state_map.has_key('[none]'):
                        state_map[None] = state_map['[none]']
                        del state_map['[none]']
                    if type_id:
                        types=(type_id,)
                    else:
                        wt = getToolByName(self.context, 'portal_workflow')
                        tt = getToolByName(self.context, 'portal_types')
                        nondefault = [info[0] for info in wt.listChainOverrides()]
                        type_ids = [type for type in tt.listContentTypes() if type not in nondefault]

                    remap_workflow(context, type_ids=(type_id,), chain=chain,
                                   state_map=state_map)
                else:
                    portal_workflow = getToolByName(context, 'portal_workflow')
                    portal_workflow.setChainForPortalTypes((type_id,), self.new_workflow())


                self.request.response.redirect('%s/@@types-controlpanel?\
type_id=%s' % (context.absolute_url() , type_id))
                postback = False

        elif cancel_button:
            self.request.response.redirect(self.context.absolute_url() + \
                                           '/plone_control_panel')
            postback = False

        if postback:
            return self.template()

    # View

    @memoize
    def selectable_types(self):
        vocab_factory = getUtility(IVocabularyFactory,
                                   name="plone.app.vocabularies.ReallyUserFriendlyTypes")
        return [dict(id=v.value, title=v.token) for v in \
                vocab_factory(self.context)]

    def selected_type_title(self):
        return self.fti.Title()

    def is_addable(self):
        return self.fti.getProperty('global_allow', False)

    def is_discussion_allowed(self):
        return self.fti.getProperty('allow_discussion', False)

    def is_versionable(self):
        context = aq_inner(self.context)
        portal_repository = getToolByName(context, 'portal_repository')
        return (self.type_id in portal_repository.getVersionableContentTypes())

    def is_searchable(self):
        context = aq_inner(self.context)
        portal_properties = getToolByName(context, 'portal_properties')
        blacklisted = portal_properties.site_properties.types_not_searched
        return (self.type_id not in blacklisted)

    @memoize
    def current_workflow(self):
        context = aq_inner(self.context)
        portal_workflow = getToolByName(context, 'portal_workflow')
        try:
            nondefault = [info[0] for info in portal_workflow.listChainOverrides()]
            if self.type_id in nondefault:
                wf_id = portal_workflow.getChainForPortalType(self.type_id)[0]
            else:
                default_workflow = self.default_workflow(False)
                return dict(id='(Default)',
                        title=_(u"label_default_workflow_title",
                                default=u"Default workflow (${title})",
                                mapping=dict(title=pmf(default_workflow.title))),
                        description=format_description(default_workflow.description))
        except IndexError:
            return dict(id='[none]', title=_(u"label_no_workflow",
                                             default=u"No workflow"))
        wf = getattr(portal_workflow, wf_id)
        return dict(id=wf.id, title=wf.title, description=format_description(wf.description))

    def available_workflows(self):
        vocab_factory = getUtility(IVocabularyFactory,
                                   name="plone.app.vocabularies.Workflows")
        workflows = [dict(id=v.value, title=v.token) 
                        for v in vocab_factory(self.context)]
        if self.type_id:
            # Only offer a default workflow option on a real type
            default_workflow = self.default_workflow(False)
            workflows.insert(0, dict(id='(Default)',
                    title=_(u"label_default_workflow_title",
                            default=u"Default workflow (${title})",
                            mapping=dict(title=pmf(default_workflow.title))),
                    description=format_description(default_workflow.description)))

        return workflows

    @memoize
    def new_workflow(self):
        current_workflow = self.current_workflow()['id']
        old_type_id = self.request.form.get('old_type_id', self.type_id)
        if old_type_id != self.type_id:
            return current_workflow
        else:
            return self.request.form.get('new_workflow', current_workflow)

    @memoize
    def have_new_workflow(self):
        return self.current_workflow()['id'] != self.new_workflow()

    @memoize
    def default_workflow(self, id_only=True):
        portal_workflow = getToolByName(self.context, 'portal_workflow')
        id = portal_workflow.getDefaultChain()[0]
        if id_only:
            return id
        else:
            return portal_workflow.getWorkflowById(id)

    @memoize
    def real_workflow(self, wf):
        if wf=='(Default)':
            return self.default_workflow()
        else:
            return wf

    @memoize
    def new_workflow_is_different(self):
        new_workflow = self.new_workflow()
        current_workflow = self.current_workflow()['id']

        return self.real_workflow(new_workflow)!=self.real_workflow(current_workflow)

    @memoize
    def new_workflow_is_none(self):
        return self.new_workflow() == '[none]'

    def new_workflow_description(self):
        portal_workflow = getToolByName(self.context, 'portal_workflow')
        current_workflow = self.current_workflow()['id']
        new_workflow = self.new_workflow()

        if self.new_workflow_is_different():
            new_workflow = self.real_workflow(self.new_workflow())
            wf = getattr(portal_workflow, new_workflow)
            return format_description(wf.description)

        return None

    def new_workflow_available_states(self):
        current_workflow = self.current_workflow()['id']
        if self.new_workflow_is_different():
            new_workflow = self.real_workflow(self.new_workflow())
            portal_workflow = getToolByName(self.context, 'portal_workflow')
            wf = getattr(portal_workflow, new_workflow)
            return [dict(id=s.id, title=s.title) for s in \
                    wf.states.objectValues()]
        else:
            return []

    def suggested_state_map(self):
        current_workflow = self.real_workflow(self.current_workflow()['id'])
        new_workflow = self.real_workflow(self.new_workflow())

        portal_workflow = getToolByName(self.context, 'portal_workflow')

        if current_workflow == '[none]':
            new_wf = getattr(portal_workflow, new_workflow)
            default_state = new_wf.initial_state
            return [dict(old_id = '[none]',
                         old_title = _(u"No workflow"),
                         suggested_id = default_state)]

        elif self.new_workflow_is_different():
            old_wf = getattr(portal_workflow, current_workflow)
            new_wf = getattr(portal_workflow, new_workflow)

            new_states = set([s.id for s in new_wf.states.objectValues()])
            default_state = new_wf.initial_state

            return [dict(old_id = old.id,
                         old_title = old.title,
                         suggested_id = (old.id in new_states and \
                                         old.id or default_state))
                    for old in old_wf.states.objectValues()]

        else:
            return []
