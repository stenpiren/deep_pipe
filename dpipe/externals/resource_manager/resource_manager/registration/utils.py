import os
import re
import json
import hashlib
import importlib

first_cap = re.compile('(.)([A-Z][a-z]+)')
all_cap = re.compile('([a-z0-9])([A-Z])')


def snake_case(name):
    name = first_cap.sub(r'\1_\2', name)
    return all_cap.sub(r'\1_\2', name).lower()


def analyze_file(path, source, config):
    config = [x for x in config if x['source'] != source]
    imported = importlib.import_module(source)
    real_path = os.path.realpath(path)

    for var in dir(imported):
        variable = getattr(imported, var)
        try:
            module_type = getattr(variable, '__module_type__')
            module_name = getattr(variable, '__module_name__')
            source_path = getattr(variable, '__source_path__')

            if module_type is None:
                module_type = os.path.basename(os.path.dirname(source_path))
            if module_name is None:
                module_name = snake_case(var)

            if source_path == real_path:
                for x in config:
                    if x['module_type'] == module_type and \
                                    x['module_name'] == module_name:
                        raise ValueError(
                            f'The module "{module_name}" of type  '
                            f'"{module_type}" already exists')

                config.append({
                    'module_type': module_type,
                    'module_name': module_name,
                    'source_path': source_path,
                    'variable': var,
                    'source': source,
                })

        except AttributeError:
            pass

    return config


def walk(path, source, exclude):
    modules = []
    if path in exclude:
        return modules

    for root, dirs, files in os.walk(path):
        for directory in dirs:
            if not directory.startswith('__'):
                dir_path = os.path.join(root, directory)
                #                 TODO: inspect.getmodulename
                modules.extend(walk(dir_path, f'{source}.{directory}', exclude))

        for file in files:
            name, ext = os.path.splitext(file)
            # TODO: doesn't look good
            if not file.startswith(('__', 'test')) and ext == '.py':
                file_path = os.path.join(root, file)
                modules.append((file_path, f'{source}.{name}'))
        break
    return modules


def handle_corruption():
    # TODO: more details
    raise RuntimeError('Config file corrupted')


def read_config(path):
    try:
        with open(path, 'r') as file:
            config = json.load(file)
        try:
            hashes = config['hashes']
            config = config['config']
        except KeyError:
            handle_corruption()

    except FileNotFoundError:
        config = []
        hashes = {}

    return config, hashes


def get_hash(path, buffer_size=65536):
    current_hash = hashlib.md5()

    with open(path, 'rb') as file:
        data = file.read(buffer_size)
        while data:
            current_hash.update(data)
            data = file.read(buffer_size)

    return f'{current_hash.hexdigest()}_{os.path.getsize(path)}'
