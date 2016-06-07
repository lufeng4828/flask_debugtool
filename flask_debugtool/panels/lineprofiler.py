import line_profiler
import functools
import inspect
import linecache
import collections
import __builtin__
import jinja2

from ..debug_panel import DebugPanel

functions_to_profile = []


def line_profile(f):
    """The passed function will be included in the line profile displayed by
    the line profiler panel.

    Can be used either as a decorator or called directly as a function

        # Using it as a decorator
        @app.route('/profile')
        @line_profile
        def profile_page(profile_user_id):
            ...
            return flask.render_template('profile_page')

        # Explicit argument
        line_profile(some_function)
    """
    functions_to_profile.append(f)
    return f

__builtin__.__dict__["profile"] = line_profile


def process_line_stats(line_stats):
    "Converts line_profiler.LineStats instance into something more useful"

    profile_results = []

    if not line_stats:
        return profile_results

    # We want timings in ms (instead of CPython's microseconds)
    multiplier = line_stats.unit / 1e-3

    for key, timings in sorted(line_stats.timings.items()):
        if not timings:
            continue

        filename, start_lineno, func_name = key

        all_lines = linecache.getlines(filename)
        sublines = inspect.getblock(all_lines[start_lineno-1:])
        end_lineno = start_lineno + len(sublines)

        line_to_timing = collections.defaultdict(lambda: (-1, 0))

        for (lineno, nhits, time) in timings:
            line_to_timing[lineno] = (nhits, time)

        padded_timings = []

        for lineno in range(start_lineno, end_lineno):
            nhits, time = line_to_timing[lineno]
            padded_timings.append( (lineno, nhits, time) )

        profile_results.append({
            'filename': filename,
            'start_lineno': start_lineno,
            'func_name': func_name,
            'timings': [
                (
                    lineno,
                    unicode(all_lines[lineno - 1].decode("utf8")),
                    time * multiplier,
                    nhits,
                ) for (lineno, nhits, time) in padded_timings
            ],
            'total_time': sum([time for _, _, time in timings]) * multiplier
        })

    return profile_results


class LineProfilerPanel(DebugPanel):
    "Panel that displays the result from a line profiler run"
    name = 'Line Profiler'

    user_activate = True

    def __init__(self, jinja_env, context={}, cache=None):
        DebugPanel.__init__(self, jinja_env, context=context, cache=cache)
        self.jinja_env.loader = jinja2.ChoiceLoader([
            self.jinja_env.loader,
            jinja2.PrefixLoader({
                'lineprofiler': jinja2.PackageLoader(__name__, 'templates')
            })
        ])

        if functions_to_profile:
            self.is_active = True

    def has_content(self):
        return bool(self.profiler)

    def process_request(self, request):
        self.profiler = line_profiler.LineProfiler()

        for f in functions_to_profile:
            self.profiler.add_function(f)

        self.stats = None

    def process_view(self, request, view_func, view_kwargs):
        if self.is_active:
            return functools.partial(self.profiler.runcall, view_func)

    def process_response(self, request, response):
        if not self.is_active:
            return False
        self.stats = self.profiler.get_stats()
        if self.cache and process_line_stats(self.stats):
            self.cache.set("DEBUGTOOLBAR:%s" % self.name, self.render_cache())
        return response

    def title(self):
        if not self.is_active:
            return 'Line Profiler Usage Docs'

        return 'Line Profiler'

    def nav_title(self):
        return 'Line Profiler'

    def nav_subtitle(self):
        if not self.is_active:
            return "Click for Usage Docs"

        return '%d function(s)' % len(functions_to_profile)

    def url(self):
        return ''

    def render_cache(self):
        return {"title": self.title(), "nav_subtitile": self.nav_subtitle(), "content": self.content()}

    def content(self):
        processed_line_stats = process_line_stats(self.stats)
        return self.render('panels/lineprofiler.html', {
            'stats': processed_line_stats
        })
