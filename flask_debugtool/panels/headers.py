from ..debug_panel import DebugPanel

_ = lambda x: x


class HeaderDebugPanel(DebugPanel):
    """
    A panel to display HTTP headers.
    """
    name = 'Header'
    has_content = True
    # List of headers we want to display
    header_filter = (
        'CONTENT_TYPE',
        'HTTP_ACCEPT',
        'HTTP_ACCEPT_CHARSET',
        'HTTP_ACCEPT_ENCODING',
        'HTTP_ACCEPT_LANGUAGE',
        'HTTP_CACHE_CONTROL',
        'HTTP_CONNECTION',
        'HTTP_HOST',
        'HTTP_KEEP_ALIVE',
        'HTTP_REFERER',
        'HTTP_USER_AGENT',
        'QUERY_STRING',
        'REMOTE_ADDR',
        'REMOTE_HOST',
        'REQUEST_METHOD',
        'SCRIPT_NAME',
        'SERVER_NAME',
        'SERVER_PORT',
        'SERVER_PROTOCOL',
        'SERVER_SOFTWARE',
    )

    def nav_title(self):
        return _('HTTP Headers')

    def title(self):
        return _('HTTP Headers')

    def url(self):
        return ''

    def process_request(self, request):
        self.headers = dict(
            [(k, request.environ[k])
                for k in self.header_filter if k in request.environ]
        )
        if self.cache:
            self.cache.set("DEBUGTOOLBAR:%s" % self.name, self.render_cache())

    def render_cache(self):
        return {"title": self.title(), "nav_subtitile": self.nav_subtitle(), "content": self.content()}

    def content(self):
        context = self.context.copy()
        context.update({
            'headers': self.headers
        })
        return self.render('panels/headers.html', context)
