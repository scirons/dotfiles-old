import bpy
import bpy.types as bt
import numpy as np
from numpy import ndarray
from pathlib import Path

from . import library_manager
from . import image_processing

PREPROCESSED_IMAGES = {}

BLENDER_PREVIEW_SIZE: tuple[int, int] = (128, 128)

def process_preview(item: library_manager.LibraryItem):
    global PREPROCESSED_IMAGES

    lib = item.parent.root
    if not (prev := item.get_preview()):
        return
    if item.meta.get('hidden'):
        return

    original_pixels = item.get_preview_pixels()
    original_pixels = image_processing.resize_image(original_pixels, library_manager.THUMBNAIL_SIZE)

    engine_variation_name = f'engine-{item.meta["engine"]}'
    stripe_variation_name = f'stripe-{int(item.meta["use_displacement"])}-{item.meta["complexity"]}'
    variation_name = 'corner_' + '_'.join([engine_variation_name, stripe_variation_name])

    if (canvas := PREPROCESSED_IMAGES.get(variation_name, None)) is None:

        if (corner_pixels := PREPROCESSED_IMAGES.get('corner', None)) is None:
            corner_pixels = lib['icons']['corner'].get_preview_pixels()
            corner_pixels = image_processing.bw_to_alpha(corner_pixels)
            corner_pixels = image_processing.tint_image(corner_pixels, [0.2, 0.2, 0.2])
            PREPROCESSED_IMAGES['corner'] = corner_pixels
        canvas = image_processing.overlay_image(
            image_processing.empty_image(original_pixels.shape[:2], channels=4),
            corner_pixels)

        if item.meta['engine'] in ['C','E']:
            if (letter_pixels := PREPROCESSED_IMAGES.get(engine_variation_name, None)) is None:
                letter_pixels = lib['icons']['eevee' if item.meta['engine'] == 'E' else 'cycles'].get_preview_pixels()
                letter_pixels = image_processing.bw_to_alpha(letter_pixels)
                PREPROCESSED_IMAGES[engine_variation_name] = letter_pixels
            canvas = image_processing.overlay_image(canvas, letter_pixels)

        if (stripe_pixels := PREPROCESSED_IMAGES.get(stripe_variation_name, None)) is None:
            stripe_pixels = lib['icons']['stripe_displace' if item.meta['use_displacement'] else 'stripe'].get_preview_pixels()
            stripe_pixels = image_processing.bw_to_alpha(stripe_pixels)
            color = {
                0: [0.0, 1.0, 0.0],
                1: [1.0, 1.0, 0.0],
                2: [1.0, 0.0, 0.0]
            }[item.meta.get('complexity')]
            stripe_pixels = image_processing.tint_image(stripe_pixels, color)
            PREPROCESSED_IMAGES[stripe_variation_name] = stripe_pixels
        canvas = image_processing.overlay_image(canvas, stripe_pixels)
        PREPROCESSED_IMAGES[variation_name] = canvas

    new_pixels = image_processing.overlay_image(original_pixels, canvas)
    prev.image_size = library_manager.THUMBNAIL_SIZE
    prev.image_pixels_float.foreach_set(new_pixels.flatten())

def ensure_previews():
    bpy.ops.wm.previews_clear('EXEC_DEFAULT', id_type={'MATERIAL'})
    bpy.ops.wm.previews_ensure('EXEC_DEFAULT')

def capture_material_preview(mat: bt.Material) -> ndarray:
    ensure_previews()
    pixels = np.zeros(len(mat.preview_ensure().image_pixels_float), dtype='float32')
    mat.preview_ensure().image_pixels_float.foreach_get(pixels)

    return pixels.reshape([*BLENDER_PREVIEW_SIZE, 4])

def save_pixels_as_image(pixels: ndarray, file: Path):
    temp_image = bpy.data.images.new('.temp_sanctus_preview_image', width=pixels.shape[1], height=pixels.shape[0], alpha=True)
    temp_image.pixels.foreach_set(pixels.flatten())
    temp_image.pixels.update()
    temp_image.update()
    temp_image.filepath_raw = str(file)
    temp_image.file_format = 'PNG'
    temp_image.save()
    bpy.data.images.remove(temp_image)

def convert_linear_to_srgb(image: bt.Image) -> None:
    buffer = image_processing.empty_image(base_shape=image.size, channels=4, flatten=True)
    image.pixels.foreach_get(buffer)
    image.pixels.foreach_set(image_processing.linear_to_srgb(buffer))
    image.pixels.update()