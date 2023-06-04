import bpy
import bpy.types as bt
import dataclasses, json, time
import numpy as np
from typing import Union
from pathlib import Path
from numpy import ndarray

from . import auto_load
from . t3dn_bip import previews, settings


THUMBNAIL_SIZE = (256, 256)

PREVIEW_COLLECTION: previews.ImagePreviewCollection = None
LIBRARY:"Library" = None

def get_render_engine_name(engine: str) -> str:
    return {
        'BLENDER_EEVEE': 'Eevee',
        'BLENDER_WORKBENCH': 'Workbench',
        'CYCLES': 'Cycles'
    }.get(engine, engine.replace('_', ' ').title())

@dataclasses.dataclass(unsafe_hash=True)
class LibraryItem:

    directory: Path
    item_name: str
    meta: dict
    parent: "Library"

    def __init__(self, directory: Path, item_name: str, parent: "Library"):
        self.directory = directory
        self.item_name = item_name
        self.parent = parent
        self.update_meta()

    @property
    def display_name(self) -> str:
        return self.item_name.replace('_', ' ').title()
    @property
    def description(self) -> str:
        return self.display_name #TODO
    @property
    def blend_file(self) -> Path:
        return self.directory.joinpath(self.item_name + '.blend')
    @property
    def icon_file(self) -> Path:
        file = self.directory.joinpath(self.item_name + '.bip')
        if not file.exists():
            file = self.directory.joinpath(self.item_name + '.jpg')
        if not file.exists():
            file = self.directory.joinpath(self.item_name + '.png')
        return file
    @property
    def meta_file(self) -> Path:
        return self.directory.joinpath(self.item_name + '.json')
    @property
    def icon(self) -> int:
        if (preview_item := self.get_preview()):
            return preview_item.icon_id
        else:
            return 1  
    @property
    def id(self) -> str:
        return self.library_path
    
    @property
    def library_path(self) -> str:
        return self.parent.library_path + '::' + self.item_name
    
    def update_meta(self):
        if not self.meta_file.exists():
            self.meta = {'hidden' : True}
            return
        with self.meta_file.open('r') as f:
            data = json.load(f)
        data['hidden'] = False
        self.meta = data
    
    def get_preview(self) -> Union[previews.ImagePreview, None]:
        return self.parent.preview_collection.get(self.id)
    
    def get_preview_pixels(self) -> ndarray:
        preview = self.get_preview()
        b = np.zeros(len(preview.image_pixels_float), dtype='float32')
        preview.image_pixels_float.foreach_get(b)
        return b.reshape([*preview.image_size,4])
    
    def get_compatible_engines(self, as_string: bool = False) -> Union[list[str], str]:
        engines = {
            'C': ['CYCLES'],
            'E': ['BLENDER_EEVEE'],
            'A': ['CYCLES', 'BLENDER_EEVEE'],
        }[self.meta.get('engine', 'A')]
        if as_string:
            return ' or '.join([f'"{get_render_engine_name(x)}"' for x in engines])
        else:
            return engines

class Library:

    library_items: dict[str, Union[LibraryItem, "Library"]] = {}
    name: str = ""
    preview_collection: previews.ImagePreviewCollection = None
    parent: Union[None, "Library"]

    def __init__(self, directory: Path, preview_collection: previews.ImagePreviewCollection):
        self.library_items = {}
        self.name = directory.stem
        self.preview_collection = preview_collection
        self.parent = None

        for entry in directory.glob('*'):
            if entry.is_file() and entry.suffix in ['.blend', '.bip', '.jpg', '.png']:
                i = LibraryItem(directory, entry.stem, self)
                self[i.item_name] = i
            if entry.is_dir():
                self.link_library(Library(entry, self.preview_collection))
    
    def link_library(self, lib: 'Library', key: str = None):
        if key is None:
            key = lib.name
        item = self.get(key, None)
        if item is None:
            self[key] = lib
            lib.parent = self
        if isinstance(item, Library):
                for k, v in lib.items():
                    if isinstance(v, LibraryItem):
                        v.parent = item
                        item[k] = v
                    if isinstance(v, Library):
                        item.link_library(v)
        
        if isinstance(item, LibraryItem):
            raise ValueError(f'Can not link library with key "{key}". Place is already taken by LibraryItem.')

    @property
    def display_name(self):
        return self.name.replace('_', ' ').title()

    @property
    def is_root(self):
        return self.parent == None

    @property
    def root(self):
        if self.is_root:
            return self
        else:
            return self.parent.root
    
    @property
    def hierarchy(self) -> list["Library"]:
        result = [self]
        if not self.is_root:
            result = self.parent.hierarchy + result
        return result
    
    @property
    def library_path(self):
        return '::'.join([x.name for x in self.hierarchy])

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.library_items[key]
        if isinstance(key, int):
            return self[list(self.keys())[key]]
        raise KeyError(f'{key}')
    
    def get(self, key, default=None):
        return self.library_items.get(key, default)
    
    def __setitem__(self, key, value):
        self.library_items[key] = value

    def keys(self):
        return self.library_items.keys()
    
    def values(self):
        return self.library_items.values()
    
    def items(self):
        return self.library_items.items()
    
    def get_library_items(self, recursive: bool = False) -> list[LibraryItem]:
        items = [x for x in self.values() if isinstance(x, LibraryItem)]
        if recursive:
            for l in self.get_sublibraries():
                items += l.get_library_items(recursive=True)
        
        return items
    
    def get_sublibraries(self, recursive: bool = False) -> list["Library"]:
        sublibs = [x for x in self.values() if isinstance(x, Library)]
        if recursive:
            for s in sublibs:
                sublibs += s.get_sublibraries(recursive=True)
        return sublibs
    
    def __str__(self):
        lib_count = len(self.get_sublibraries())
        item_count = len(self.get_library_items())
        return f'Library "{self.name}" [Sublibs={lib_count},Items={item_count}]'
    
    def __repr__(self):
        return str(self)
    
    def generate_icons(self, recursive: bool = True, debug: bool = False) -> None:
        start = time.perf_counter()
        for i in self.get_library_items():
            if i.icon_file.exists():
                prev = self.preview_collection.load_safe(i.id, str(i.icon_file), 'IMAGE')
        if recursive:
            for l in self.get_sublibraries():
                l.generate_icons(recursive=True)
        end = time.perf_counter()
        if debug:
            print(f'Generated Icons in {round(end - start, 3)} seconds.')
    
    def process_icons(self, recursive: bool = True, debug: bool = False):
        from . import img_tools
        start = time.perf_counter()
        items = self.get_library_items(recursive=recursive)
        for i in items:
            img_tools.process_preview(i)
        
        end = time.perf_counter()
        if debug:
            print(f'Prepared Thumbnails in {round(end - start, 3)} seconds.')

    def get_enum_items(self) -> list[tuple[str, str, str, int, int]]:
        result = []

        i = 0
        for sublib in self.get_sublibraries():
            if len(sublib.values()):
                result.append((sublib.name, sublib.display_name, sublib.display_name, 0, i))
                i += 1
        for item in self.get_library_items():
            result.append((item.item_name, item.display_name, item.description, item.icon, i))
            i += 1
        return result
    
    def get_enum_attr_name(self) -> str:
        suffix = '_'.join([x.name for x in self.hierarchy])
        return f'sanctus_{suffix}'

    def path_resolve(self, library_path: str):
        parts = library_path.split('::')
        if not parts[0] == self.name:
            return None
        current: Union[Library, LibraryItem] = self
        for p in parts[1:]:
            current = current.get(p)
        if type(current) in [Library, LibraryItem]:
            return current
        else:
            raise ValueError(f'Could not resolve path: "{library_path}"')

def register_previews(register: bool) -> None:
    global PREVIEW_COLLECTION
    settings.WARNINGS = False
    if register:
        PREVIEW_COLLECTION = previews.new(max_size=THUMBNAIL_SIZE, lazy_load=True)
    if not register and isinstance(PREVIEW_COLLECTION, previews.ImagePreviewCollection):
        previews.remove(PREVIEW_COLLECTION)
    settings.WARNINGS = True

def register_load_libraries(register: bool):
    global LIBRARY, PREVIEW_COLLECTION
    if register:
        print('Start generating Libraries...')

        builtin_path = Path(__file__).parent.joinpath('lib')
        LIBRARY = Library(builtin_path, PREVIEW_COLLECTION)
        LIBRARY.name = 'lib'

        LIBRARY.generate_icons(debug=True)
        print(f'Library Size: {len(LIBRARY.get_library_items(recursive=True))}')

    else:
        LIBRARY = None

def register_library_enums(register: bool):
    wm = bt.WindowManager
    global LIBRARY

    def register_lib_enum_rec(library: Library, register):
        if register:
            setattr(wm, library.get_enum_attr_name(), bpy.props.EnumProperty(items=library.get_enum_items(), name=library.display_name))
        else:
            delattr(wm, library.get_enum_attr_name())
        
        for l in library.get_sublibraries():
            register_lib_enum_rec(l, register)

    register_lib_enum_rec(LIBRARY, register)

@auto_load.blender_register
def register_module(register: bool):
    functions = [
        register_previews,
        register_load_libraries,
        register_library_enums,
    ]
    if not register:
        functions.reverse()
    
    for f in functions:
        f(register)

def reload_library_full():
    register_module(False)
    register_module(True)