import yaml
import logging
import docker
import os
import types
import numpy as np

from colorama import Fore
from docker.types import Mount
from collections import defaultdict

OK = '[' + Fore.GREEN + ' OK ' + Fore.RESET + ']'
FAIL = '[' + Fore.RED + 'FAIL' + Fore.RESET + ']'
SEPARATOR = 'bbpypeline----------'


def parse_output(output, cmds):
    if isinstance(output, types.GeneratorType):
        stream = []
        for x in output:
            x = x.decode('utf-8')
            if SEPARATOR not in x:
                print(x, end='', flush=True)
            stream.append(x)
        output = ''.join(stream)
    else:
        output = output.decode('UTF-8')

    output_lines = np.array(output.split('\n'))
    separators = np.where(output_lines == SEPARATOR)[0].tolist()

    output_cmds = []
    for i in range(len(separators) - 1):
        output_cmds.append(output_lines[separators[i] + 1:separators[i + 1]])
    output_cmds.append(output_lines[separators[-1] + 1:])

    return cmds[:len(output_cmds)], output_cmds


def run_step(step, docker_image, verbose=False):
    cmds = step['script']
    with open('.bbpypeline.sh', 'w') as f:
        f.write('set -e\n')
        for cmd in cmds:
            f.write('printf "\\n{}\\n"\n'.format(SEPARATOR))
            f.write(cmd + '\n')

    outputs = []
    cwd = os.getcwd()
    docker_client = docker.from_env()
    container = docker_client.containers.run(
        docker_image,
        tty=True,
        detach=True,
        auto_remove=True,
        mounts=[Mount(target='/ws', source=cwd, type='bind')])

    res = container.exec_run('sh .bbpypeline.sh', workdir='/ws', stream=verbose)
    output = parse_output(res.output, cmds)
    container.stop()
    os.remove('.bbpypeline.sh')
    return (res.exit_code, output)


class BBPipeline:
    def __init__(self, yaml_file):
        self.pipeline = defaultdict(lambda: None)
        with open(args.file, 'r') as f:
            try:
                self.pipeline = yaml.load(f)
            except yaml.YAMLError as e:
                print(e)
                return

        self.docker_image = self.pipeline['image']
        if not self.docker_image:
            logging.WARNING('default docker image is None')

    def run_pipeline(self, name=None, verbose=False):
        if not name:
            name = 'default'  #TODO detect correct pipeline

        if name not in self.pipeline['pipelines']:
            raise ValueError('{} not in list of pipelines'.format(name))

        pipeline = self.pipeline['pipelines'][name]
        results = {}

        for step in pipeline:
            step = step['step']
            docker_image = step['image'] if 'image' in step else self.docker_image
            print('{:<60}'.format(step['name'] + '...'), end='', flush=True)
            exit_code, stdout = run_step(step, docker_image, verbose=verbose)
            results[step['name']] = (exit_code, stdout)
            if exit_code == 0:
                print(OK)
            else:
                print(FAIL)
            # print(stdout)

        for step in results:
            if results[step][0] != 0:
                for cmd, output in zip(results[step][1][0], results[step][1][1]):
                    print('\n{}{}{}'.format(Fore.YELLOW, cmd, Fore.RESET))
                    print('\n'.join(output), '\n')


def main(args):
    pipeline = BBPipeline(args.file)
    pipeline.run_pipeline(verbose=args.verbose)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run bitbucket pipeline locally')
    parser.add_argument(
        '-f',
        '--file',
        help='bitbucket-piplines.yml location',
        default='./bitbucket-pipelines.yml',
        type=str)
    parser.add_argument(
        '-v',
        '--verbose',
        help='show commands stdout',
        dest='verbose',
        action='store_true',
        default=False)

    args = parser.parse_args()
    main(args)