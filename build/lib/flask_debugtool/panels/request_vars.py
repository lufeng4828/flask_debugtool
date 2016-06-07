from flask import session

from ..debug_panel import DebugPanel

_ = lambda x: x


class RequestVarsDebugPanel(DebugPanel):
    """
    A panel to display request variables (POST/GET, session, cookies).
    """
    name = 'RequestVars'
    has_content = True

    def nav_title(self):
        return _('Request Vars')

    def title(self):
        return _('Request Vars')

    def url(self):
        return ''

    def process_request(self, request):
        self.request = request
        self.session = session
        self.view_func = None
        self.view_args = []
        self.view_kwargs = {}

    def process_view(self, request, view_func, view_kwargs):
        self.view_func = view_func
        self.view_kwargs = view_kwargs

    def process_response(self, request, response):
        self.data = self.context.copy()
        self.data.update({
            'get': [(k, self.request.args.getlist(k)) for k in self.request.args],
            'post': [(k, self.request.form.getlist(k)) for k in self.request.form],
            'cookies': [(k, self.request.cookies.get(k)) for k in self.request.cookies],
            'view_func': ('%s.%s' % (self.view_func.__module__, self.view_func.__name__)
                          if self.view_func else '[unknown]'),
            'view_args': self.view_args,
            'view_kwargs': self.view_kwargs or {},
            'session': self.session.items(),
        })
        if self.cache:
            self.cache.set("DEBUGTOOLBAR:%s" % self.name, self.render_cache())

    def render_cache(self):
        return {"title": self.title(), "nav_subtitile": self.nav_subtitle(), "content": self.content()}

    def content(self):
        return self.render('panels/request_vars.html', self.data)
