import typing
import bpy
import functools
import importlib
import inspect
import sys
import glob
import os
from types import ModuleType
from pathlib import Path
from typing import Union

CLASS_COLLECTION_NAME: str = 'CLASSES'
FUNCTION_COLLECTION_NAME: str = 'REGISTER_FUNCTIONS'
DEPENDENCY_ATTR = 'al_dependencies'

def _get_module_names(file: str, package: str = '') -> list[str]:

    if not package == '':
        package += '.'
    all_modules = Path(file).parent.glob('*')
    # filter __init__ and __pycache__
    return [package + x.name.rsplit('.py', 1)[0] for x in all_modules if not x.name.startswith('__')]


def import_modules(file: str, package: Union[str, None] = None) -> list[ModuleType]:
    modules = []
    for name in _get_module_names(file, package):
        try:
            modules.append(importlib.import_module(name, package=package))
        except ModuleNotFoundError:
            pass  # is not a module
    return modules


def get_collections_from_modules(modules: list[ModuleType]) -> tuple[list[type], list[typing.Callable[[bool], None]]]:

    classes = []
    functions = []
    for m in modules:
        classes += getattr(m, CLASS_COLLECTION_NAME, [])
        functions += getattr(m, FUNCTION_COLLECTION_NAME, [])
    return classes, functions


def get_classes_in_module(module_name):
    import sys
    import inspect
    return [x[1] for x in inspect.getmembers(sys.modules[module_name], inspect.isclass)]


def cleanse_modules(package: str):
    import sys
    for m in [x for x in sys.modules if x.startswith(package)]:
        sys.modules.pop(m)

def _add_obj_to_module_collection(obj, module = None):

    if module is None:
        module = sys.modules[obj.__module__]

    is_class = inspect.isclass(obj)
    attr = CLASS_COLLECTION_NAME if is_class else FUNCTION_COLLECTION_NAME
    l = getattr(module, attr, [])
    l.append(obj)
    setattr(module, attr, l)

# DECORATOR


def blender_register_objs(*objs: list[Union[type, typing.Callable]]):
    '''Adds functions or classes to Global list for registration.'''
    if len(objs) == 0:
        return
    else:
        for obj in objs:
            _add_obj_to_module_collection(obj)
    o: objs[0]
    return o

# DECORATOR


def blender_register(obj):
    '''Adds function or class to Global list for registration.'''
    _add_obj_to_module_collection(obj)
    return obj

# DECORATOR


def blender_operator(op_class):
    '''Adds operator class to global list for registration and makes sure it is valid.'''
    clss_name: str = op_class.__name__
    if '_OT_' in clss_name:
        name_parts = clss_name.partition('_OT_')
        if not hasattr(op_class, 'bl_idname'):
            op_class.bl_idname = f'{name_parts[0].lower()}.{name_parts[2].lower()}'
        if not hasattr(op_class, 'bl_label'):
            op_class.bl_label = name_parts[2].replace('_', ' ').title()
        if not hasattr(op_class, 'bl_description'):
            op_class.bl_description = op_class.bl_label
    else:
        raise ValueError(
            f'Operator Class "{clss_name}" has to contain "_OT_" in class name')
    _add_obj_to_module_collection(op_class)
    return op_class

# DECORATOR


def register_draw_function(*menus: list[Union[bpy.types.Menu, bpy.types.Panel]], prepend: bool = False):
    '''Auto register a draw callback to a Blender menu or panel.'''

    @functools.wraps(register_draw_function)
    def decorator(function: typing.Callable):
        
        def register_func(register: bool, menus: list[Union[bpy.types.Menu, bpy.types.Panel]], prepend: bool, function: typing.Callable):
            add_function_name = 'prepend' if prepend else 'append'
            for menu in menus:
                getattr(menu, add_function_name if register else 'remove')(function)

        composed_func = functools.partial(register_func, menus=menus, prepend=prepend, function=function)
        composed_func.__name__ = f'register_callback_{function.__name__}'
        _add_obj_to_module_collection(
            composed_func,
            module = sys.modules[function.__module__]
            )
        return function
    
    return decorator


# DECORATOR
def depends_on(*dependencies):
    '''Define dependencies to determine a registration order for certain classes. Use as decorator.'''
    dependencies = list(dependencies)

    @functools.wraps(depends_on)
    def func(clss: type):
        setattr(clss, DEPENDENCY_ATTR, dependencies)
        return clss
    return func


def _get_ordered_dependencies(clss: type) -> list[type]:
    '''For a class gets a list of all its dependencies going recursively through the inheritence stack.'''
    result = []
    for c in clss.mro():
        if c != clss:
            result += _get_ordered_dependencies(c)
    current_dependencies = getattr(clss, DEPENDENCY_ATTR, [])
    for d in current_dependencies:
        result += _get_ordered_dependencies(d)
    result += current_dependencies
    return list(set(result))

def _detect_annotation_dependencies(clss: type, builtin_classes: list[type]) -> typing.Generator[type, None, None]:
    DEPENDENCY_FUNCTIONS = [
        bpy.props.PointerProperty,
        bpy.props.CollectionProperty
    ]
    annotations = getattr(clss, '__annotations__', None)
    if annotations is None:
        return
    for pa in (x for x in annotations.values() if x.function in DEPENDENCY_FUNCTIONS):
        if (t := pa.keywords['type']) not in builtin_classes:
            yield t

def safe_register_classes(classes: list[type], *, register=True, debug=False):
    '''Registers all classes as blender classes taking dependency resolution into account.'''
    classes = list(set(classes))
    if not register:
        classes.reverse()
    _registered = []

    def register_dependent(clss, register, debug):

        nonlocal _registered
        for d in _get_ordered_dependencies(clss):
            if not d in _registered:
                register_dependent(d, register, debug)

        if not clss in _registered:
            if debug:
                print(
                    f'{"Register" if register else "Unregister"} Class: {clss.__name__}')
            getattr(bpy.utils, 'register_class' if register else 'unregister_class')(
                clss)
            _registered.append(clss)

    for c in classes:
        register_dependent(c, register, debug)


def register_functions(functions: list[typing.Callable[[bool], None]], *, register: bool = True, debug: bool = False):
    '''Registers a list of functions. Functions should determine the behavior for register and unregister using the boolean argument as a switch.'''
    if not register:
        functions.reverse()
    for func in functions:
        if debug:
            print(
                f'{"Register" if register else "Unregister"} Function: {func.__name__}')
        func(register)


def lazy_register(classes, functions, *, register: bool = True, debug: bool = False):
    '''Register all classes and functions at the same time.'''
    if register:
        safe_register_classes(classes, register=True, debug=debug)
        register_functions(functions, register=True, debug=debug)
    else:
        register_functions(functions, register=False, debug=debug)
        safe_register_classes(classes, register=False, debug=debug)

__all__ = [
    'import_modules',
    'get_collections_from_modules',
    'get_classes_in_module',
    'cleanse_modules',
    'blender_register_objs',
    'blender_register',
    'blender_operator',
    'register_draw_function',
    'depends_on',
    'safe_register_classes',
    'register_functions',
    'lazy_register',
]