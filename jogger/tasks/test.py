import argparse
import os

from .base import Task, TaskError

try:
    import django  # noqa
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False

try:
    import coverage  # noqa
    HAS_COVERAGE = True
except ImportError:
    HAS_COVERAGE = False

try:
    import tblib  # noqa
    HAS_TBLIB = True
except ImportError:
    HAS_TBLIB = False


class TestTask(Task):
    
    help = (
        'Run the test suite. If coverage.py is detected, perform code '
        'coverage analysis, print an on-screen summary, and generate a fully '
        'detailed HTML report.'
    )
    
    def __init__(self, *args, **kwargs):
        
        self._has_output = False
        
        super().__init__(*args, **kwargs)
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            'paths',
            nargs='*',
            metavar='test_path',
            help='Module paths to test.'
        )
        
        parser.add_argument(
            '-q', '--quick',
            action='store_true',
            help=(
                'Run a "quick" variant of the task: no coverage analysis and '
                'running tests in parallel (where possible).'
            )
        )
        
        parser.add_argument(
            '-a',
            action='store_true',
            dest='accumulate',
            help=(
                'Accumulate coverage data across multiple runs. Disables all '
                'coverage reporting (to be run after all coverage data is'
                'accumulated).'
            )
        )
        
        parser.add_argument(
            '--report',
            action='store_true',
            dest='reports_only',
            help=(
                'Skip the test suite and just output the on-screen summary '
                'and generate the HTML report. Useful to review previous '
                'results or if using -a to accumulate results before running '
                'the reports.'
            )
        )
        
        parser.add_argument(
            '--no-html',
            action='store_false',
            dest='html_report',
            help='Do not generate a detailed HTML code coverage report.'
        )
        
        parser.add_argument(
            '--src',
            default='',
            dest='source',
            help=(
                'Specify the source to measure the coverage of.'
            )
        )
        
        parser.add_argument('extra', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    @property
    def section_prefix(self):
        
        # If the command has generated any output, sections should be prefixed
        # with a newline. The first section to generate output should not.
        if self._has_output:
            return '\n'
        
        return ''
    
    def get_coverage_command(self, quick, source, accumulate, **options):
        
        if not HAS_COVERAGE or quick:
            return ''
        
        if source:
            source = f' --source {source}'
        
        accumulate = ' -a' if accumulate else ''
        
        return f'coverage run --branch{source}{accumulate} '
    
    def get_test_command(self, labels, quick, verbosity, extra, **options):
        
        command = ['python -Wa manage.py test']
        command.extend(labels)
        
        # Pass all "extra" arguments, and the verbosity level, through to the
        # test command
        command.extend(extra)
        command.append(f'-v {verbosity}')
        
        # Add --parallel switch if using "quick" mode, unless disabled in
        # settings or if the switch is provided explicitly in "extra" arguments
        if not any(v.startswith('--parallel') for v in extra):
            parallel = self.settings.get('quick_parallel', None)
            if quick and (parallel is None or int(parallel) > 1):
                if not HAS_TBLIB:
                    self.stdout.write(self.styler.warning(
                        'Tracebacks in parallel tests may not display correctly: '
                        'tblib not detected. pip install tblib to fix.'
                    ))
                
                command.append('--parallel')
                if parallel:
                    command.append(parallel)
        
        return ' '.join(command)
    
    def do_summary(self, verbosity, **options):
        
        if verbosity < 1:
            return
        
        self.stdout.write(self.styler.label(f'{self.section_prefix}Coverage summary'))
        if verbosity > 1:
            self.cli('coverage report')
        else:
            self.cli('coverage report --skip-covered')
    
    def do_html_report(self, html_report, **options):
        
        if not html_report:
            return
        
        self.stdout.write(self.styler.label(f'{self.section_prefix}Generating HTML report...'), use_ending=False)
        self.cli('coverage html')
        
        html_report_path = os.path.abspath('htmlcov/index.html')
        if os.path.exists(html_report_path):
            html_report_path = f'file://{html_report_path}'
        else:
            html_report_path = f'Location of HTML report unknown, expected {html_report_path}'
        
        self.stdout.write(f' done: {html_report_path}')
    
    def handle(self, *args, **options):
        
        reports_only = options['reports_only']
        if reports_only:
            if options['quick']:
                raise TaskError('-q/--quick and --report are mutually exclusive.')
            elif options['accumulate']:
                raise TaskError('-a and --report are mutually exclusive.')
        
        if not HAS_DJANGO:
            raise TaskError('Django not detected.')
        
        if not reports_only:
            test_paths = options.pop('paths', None)
            coverage_command = self.get_coverage_command(**options)
            test_command = self.get_test_command(test_paths, **options)
            
            self.cli(f'{coverage_command}{test_command}')
        
        if not HAS_COVERAGE:
            # Not having coverage available is simply a warning unless directly
            # requesting coverage reports, in which case it is an error
            msg = 'Code coverage not available: coverage.py not detected'
            if not reports_only:
                self.stdout.write(self.styler.warning(msg))
            else:
                raise TaskError(msg)
        elif not options['accumulate'] and not options['quick']:
            self.do_summary(**options)
            self.do_html_report(**options)
    
    def cli(self, cmd):
        
        self._has_output = True
        
        return super().cli(cmd)
