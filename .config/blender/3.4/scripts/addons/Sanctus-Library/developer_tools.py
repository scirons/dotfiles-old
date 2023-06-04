import bpy
import bpy.types as bt
from . import library_manager

def draw_ui(layout: bt.UILayout, library_element: library_manager.LibraryItem):
    c = layout.column(align=True)
    c.scale_y = 0.8
    c.label(text=f'Current Item Meta: ({library_element.item_name})')
    for v, k in library_element.meta.items():
        c.label(text=f'{v}: {k}')