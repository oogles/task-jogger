import argparse
import sys

from jogger import __version__ as version
from jogger.exceptions import TaskDefinitionError
from jogger.tasks.base import TaskProxy
from jogger.utils.input import JOG_FILE_NAME, get_tasks
from jogger.utils.output import OutputWrapper


def parse_args(argv=None):
    
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Execute common, project-specific tasks.',
        epilog=(
            'Any additional arguments are passed through to the executed tasks.'
            '\n\n'
            'Run without arguments from within a target project to output all '
            f'tasks configured in that project\'s {JOG_FILE_NAME} file.'
        )
    )
    
    parser.add_argument(
        'task_name',
        nargs='?',
        metavar='task',
        help='The name of the task'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {version}',
        help='Display the version number and exit'
    )
    
    parser.add_argument('extra', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    return parser.parse_args(argv)


def main(argv=None):
    
    arguments = parse_args(argv)
    stdout = OutputWrapper(sys.stdout)
    stderr = OutputWrapper(sys.stderr, default_style='error')
    
    try:
        tasks = get_tasks()
        for name, task in tasks.items():
            tasks[name] = TaskProxy(name, task, stdout, stderr, arguments.extra)
    except (FileNotFoundError, TaskDefinitionError) as e:
        stderr.write(str(e))
        sys.exit(1)
    
    task_name = arguments.task_name
    if task_name:
        try:
            task = tasks[task_name]
        except KeyError:
            stderr.write(f'Unknown task "{task_name}".')
            sys.exit(1)
        
        task.execute()
    elif not tasks:
        stdout.write(f'No tasks defined.')
    else:
        stdout.write('Available tasks:', 'label')
        for task in tasks.values():
            task.output_help_line()


if __name__ == '__main__':
    main()
