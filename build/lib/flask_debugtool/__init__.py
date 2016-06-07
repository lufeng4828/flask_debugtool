import os

from flask import Blueprint, current_app, request, g, send_from_directory, jsonify
from flask.globals import _request_ctx_stack
from jinja2 import Environment, PackageLoader
from werkzeug.urls import url_quote_plus

from .compat import iteritems
from .toolbar import DebugToolbar
from .utils import decode_text


module = Blueprint('debugtoolbar', __name__)


def replace_insensitive(string, target, replacement):
    """Similar to string.replace() but is case insensitive
    Code borrowed from:
    http://forums.devshed.com/python-programming-11/case-insensitive-string-replace-490921.html
    """
    no_case = string.lower()
    index = no_case.rfind(target.lower())
    if index >= 0:
        return string[:index] + replacement + string[index + len(target):]
    else:  # no results so return the original string
        return string


def _printable(value):
    try:
        return decode_text(repr(value))
    except Exception as e:
        return '<repr(%s) raised %s: %s>' % (
               object.__repr__(value), type(e).__name__, e)


class DebugToolbarExtension(object):
    _static_dir = os.path.realpath(
        os.path.join(os.path.dirname(__file__), 'static'))

    _redirect_codes = [301, 302, 303, 304]

    def __init__(self, app=None, cache=None):
        self.app = app
        self.debug_toolbars = {}
        self.cache = cache
        # Configure jinja for the internal templates and add url rules
        # for static data
        self.jinja_env = Environment(
            autoescape=True,
            extensions=['jinja2.ext.i18n', 'jinja2.ext.with_'],
            loader=PackageLoader(__name__, 'templates'))
        self.jinja_env.filters['urlencode'] = url_quote_plus
        self.jinja_env.filters['printable'] = _printable

        if app is not None:
            self.init_app(app, cache)

    def init_app(self, app, cache=None):
        if not self.cache and cache:
            self.cache = cache
        if not self.cache:
            raise RuntimeError("The Flask-DebugToolbar requires the cache ext")

        for k, v in iteritems(self._default_config(app)):
            app.config.setdefault(k, v)

        if not app.config['DEBUG_TB_ENABLED']:
            return

        if not app.config.get('SECRET_KEY'):
            raise RuntimeError(
                "The Flask-DebugToolbar requires the 'SECRET_KEY' config "
                "var to be set")

        DebugToolbar.load_panels(app)

        app.before_request(self.process_request)
        app.after_request(self.process_response)
        app.teardown_request(self.teardown_request)

        # Monkey-patch the Flask.dispatch_request method
        app.dispatch_request = self.dispatch_request

        app.add_url_rule('/_debug_toolbar/static/<path:filename>',
                         '_debug_toolbar.static', self.send_static_file)
        app.add_url_rule('/_debug_toolbar/info/<path:name>',
                         '_debug_toolbar.info', self.send_info)
        app.register_blueprint(module, url_prefix='/_debug_toolbar/views')

    def _default_config(self, app):
        return {
            'DEBUG_TB_ENABLED': app.debug,
            'DEBUG_TB_HOSTS': (),
            'DEBUG_TB_INTERCEPT_REDIRECTS': True,
            'DEBUG_TB_PANELS': (
                'flask_debugtool.panels.versions.VersionDebugPanel',
                'flask_debugtool.panels.timer.TimerDebugPanel',
                'flask_debugtool.panels.headers.HeaderDebugPanel',
                'flask_debugtool.panels.request_vars.RequestVarsDebugPanel',
                'flask_debugtool.panels.config_vars.ConfigVarsDebugPanel',
                'flask_debugtool.panels.template.TemplateDebugPanel',
                'flask_debugtool.panels.sqlalchemy.SQLAlchemyDebugPanel',
                'flask_debugtool.panels.logger.LoggingPanel',
                'flask_debugtool.panels.profiler.ProfilerDebugPanel',
                'flask_debugtool.panels.lineprofiler.LineProfilerPanel',
            ),
        }

    def dispatch_request(self):
        """Modified version of Flask.dispatch_request to call process_view."""
        req = _request_ctx_stack.top.request
        app = current_app

        if req.routing_exception is not None:
            app.raise_routing_exception(req)

        rule = req.url_rule

        # if we provide automatic options for this URL and the
        # request came with the OPTIONS method, reply automatically
        if getattr(rule, 'provide_automatic_options', False) \
           and req.method == 'OPTIONS':
            return app.make_default_options_response()

        # otherwise dispatch to the handler for that endpoint
        view_func = app.view_functions[rule.endpoint]
        view_func = self.process_view(app, view_func, req.view_args)

        return view_func(**req.view_args)

    def _show_toolbar(self):
        """Return a boolean to indicate if we need to show the toolbar."""
        if request.blueprint == 'debugtoolbar':
            return False

        hosts = current_app.config['DEBUG_TB_HOSTS']
        if hosts and request.remote_addr not in hosts:
            return False

        return True

    def send_static_file(self, filename):
        """Send a static file from the flask-debugtoolbar static directory."""
        return send_from_directory(self._static_dir, filename)

    def send_info(self, name):
        """Send info """
        info = self.cache.get("DEBUGTOOLBAR:%s" % name)
        return jsonify(info=info)

    def process_request(self):
        g.debug_toolbar = self

        if not self._show_toolbar():
            return

        real_request = request._get_current_object()

        self.debug_toolbars[real_request] = DebugToolbar(real_request, self.jinja_env, self.cache)
        for panel in self.debug_toolbars[real_request].panels:
            panel.process_request(real_request)

    def process_view(self, app, view_func, view_kwargs):
        """ This method is called just before the flask view is called.
        This is done by the dispatch_request method.
        """
        real_request = request._get_current_object()
        if real_request in self.debug_toolbars:
            for panel in self.debug_toolbars[real_request].panels:
                new_view = panel.process_view(real_request, view_func, view_kwargs)
                if new_view:
                    view_func = new_view
        return view_func

    def process_response(self, response):
        real_request = request._get_current_object()
        if real_request not in self.debug_toolbars:
            return response

        # Intercept http redirect codes and display an html page with a
        # link to the target.
        if current_app.config['DEBUG_TB_INTERCEPT_REDIRECTS']:
            if (response.status_code in self._redirect_codes and
                    not real_request.is_xhr):
                redirect_to = response.location
                redirect_code = response.status_code
                if redirect_to:
                    content = self.render('redirect.html', {
                        'redirect_to': redirect_to,
                        'redirect_code': redirect_code
                    })
                    response.content_length = len(content)
                    response.location = None
                    response.response = [content]
                    response.status_code = 200

        # If the http response code is 200 then we process to add the
        # toolbar to the returned html response.
        if response.status_code == 200:
            for panel in self.debug_toolbars[real_request].panels:
                panel.process_response(real_request, response)

            if response.headers['content-type'].startswith('text/html') and response.is_sequence:
                response_html = response.data.decode(response.charset)
                toolbar_html = self.debug_toolbars[real_request].render_toolbar()

                content = replace_insensitive(
                    response_html, '</body>', toolbar_html + '</body>')
                content = content.encode(response.charset)
                response.response = [content]
                response.content_length = len(content)

        return response

    def teardown_request(self, exc):
        self.debug_toolbars.pop(request._get_current_object(), None)

    def render(self, template_name, context):
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)
