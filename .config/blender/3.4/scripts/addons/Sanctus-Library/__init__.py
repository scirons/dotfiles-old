bl_info = {
    "name":         "Sanctus-Library-Lite",
    "author":       "Sanctus, Kolupsy",
    "version":      (2, 3, 0),
    "blender":      (3, 00, 0),
    "location":     "",
    "description":  "Sanctus Library Lite (FREE VERSION)",
    "warning":      "",
    "doc_url":      "http://sanctuslibrary.xyz",
    "category":     "Material",
}

from . import auto_load

MODULES = auto_load.import_modules(__file__, __package__)

CLASSES, FUNCTIONS = auto_load.get_collections_from_modules(MODULES)

def register():
    auto_load.lazy_register(CLASSES, FUNCTIONS, register=True, debug=False)

def unregister():
    auto_load.lazy_register(CLASSES, FUNCTIONS, register=False, debug=False)
    auto_load.cleanse_modules(__package__)