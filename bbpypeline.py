import glob
import yaml
import logging
import docker
import os
import types
import numpy as np

from colorama import Fore
from collections import defaultdict
from subprocess import call

OK = '[' + Fore.GREEN + ' OK ' + Fore.RESET + ']'
FAIL = '[' + Fore.RED + 'FAIL' + Fore.RESET + ']'
SEPARATOR = 'bbpypeline----------'
SUCCESS = '2716No0Y5Fxaat9gzwlE'


def output_buffer(out_stream):
    line = ''
    for data in out_stream:
        data = data.decode('utf-8')
        if '\n' not in data:
            line += data
        else:
            split_data = data.split('\n')
            for l in split_data[:-1]:
                yield line + l
                line = ''
            line += split_data[-1]
    if len(line.strip()) > 0:
        yield line


def parse_output(res, cmds):
    exit_code = res.exit_code
    if isinstance(res.output, types.GeneratorType):
        stream = []
        for line in output_buffer(res.output):
            if SEPARATOR not in line and SUCCESS not in line:
                print(line, flush=True)
            stream.append(line + '\n')
        if SUCCESS in stream[-1]:
            exit_code = 0
        else:
            exit_code = 1
        output = ''.join(stream)
    else:
        output = res.output.decode('UTF-8')

    output_lines = np.array(output.split('\n'))
    separators = np.where(output_lines == SEPARATOR)[0].tolist()

    output_cmds = []
    for i in range(len(separators) - 1):
        output_cmds.append(output_lines[separators[i] + 1:separators[i + 1]])
    if len(separators) > 0:
        output_cmds.append(output_lines[separators[-1] + 1:])

    return (cmds[:len(output_cmds)], output_cmds), exit_code


def run_step(step, docker_image, verbose=False):
    ignored_files = []

    if os.path.exists('./.bbignore'):
        with open('./.bbignore', 'r') as f:
            patterns = f.readlines()
        patterns = map(lambda x: x.strip(), patterns)
        for p in patterns:
            ignored_files += glob.glob(p, recursive=True)

    cmds = step['script']
    with open('.bbpypeline.sh', 'w') as f:
        f.write('set -e\n')
        for i in ignored_files:
            f.write('rm -rf {}\n'.format(i))
        for cmd in cmds:
            f.write('printf "\\n{}\\n"\n'.format(SEPARATOR))
            f.write(cmd + '\n')
        if verbose:
            f.write('printf "{}"'.format(SUCCESS))

    docker_client = docker.from_env()
    container = docker_client.containers.run(docker_image, tty=True, detach=True, auto_remove=True)
    container.exec_run('mkdir /ws')
    call(['docker', 'cp', './', '{}:/ws'.format(container.id)])

    res = container.exec_run('sh .bbpypeline.sh', workdir='/ws', stream=verbose)
    output, exit_code = parse_output(res, cmds)
    container.stop()
    os.remove('.bbpypeline.sh')
    return exit_code, output


def run_pipeline(bbpypeline, name=None, verbose=False, stop=False):
    if not name:
        name = 'default'  # TODO detect correct pipeline

    if name not in bbpypeline.pipeline['pipelines']:
        raise ValueError('{} not in list of pipelines'.format(name))

    pipeline = bbpypeline.pipeline['pipelines'][name]
    results = {}

    for i, step in enumerate(pipeline):
        step = step['step']
        if 'name' in step:
            name = step['name']
        else:
            name = 'step' + str(i + 1)
        docker_image = step['image'] if 'image' in step else bbpypeline.docker_image
        print('{:<60}'.format(name + '...'), end=('\n' if verbose else ''), flush=True)

        exit_code, stdout = run_step(step, docker_image, verbose=verbose)
        results[name] = (exit_code, stdout)
        if exit_code == 0:
            print(OK)
        else:
            print(FAIL)
            if stop:
                break

    for step in results:
        if results[step][0] != 0:
            for cmd, output in zip(results[step][1][0], results[step][1][1]):
                print('\n{}{}{}'.format(Fore.YELLOW, cmd, Fore.RESET))
                print('\n'.join(output), '\n')

    if verbose:
        for step in results:
            print('{:<60}'.format(step), end='', flush=True)
            if results[step][0] == 0:
                print(OK)
            else:
                print(FAIL)


class BBPipeline:
    def __init__(self, yaml_file):
        self.pipeline = defaultdict(lambda: None)
        with open(yaml_file, 'r') as f:
            try:
                self.pipeline = yaml.load(f)
            except yaml.YAMLError as e:
                print(e)
                return

        self.docker_image = self.pipeline['image']
        if not self.docker_image:
            logging.WARNING('default docker image is None')


def main(args):
    pipeline = BBPipeline(args.file)
    run_pipeline(pipeline, verbose=args.verbose, stop=args.stop)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run bitbucket pipeline locally')
    parser.add_argument(
        '-f',
        '--file',
        help='bitbucket-piplines file path',
        default='./bitbucket-pipelines.yml',
        type=str)
    parser.add_argument(
        '-v',
        '--verbose',
        help='show commands stdout',
        dest='verbose',
        action='store_true',
        default=False)
    parser.add_argument('-s', '--stop', help='stop after step fail', dest='stop', action='store_true', default=False)

    args = parser.parse_args()
    main(args)
