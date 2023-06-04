import numpy as np
from numpy import ndarray
from typing import Literal

class InvalidImageError(Exception):
    pass

def unravel(image: ndarray) -> ndarray:
    if not is_valid_image(image):
        raise InvalidImageError()
    new_shape = [
        image.shape[0] * image.shape[1],
        image.shape[2]
    ]
    return image.reshape(new_shape)
    
def format(image: ndarray, base_shape: tuple[int, int]) -> ndarray:
    new_shape = [
        base_shape[0],
        base_shape[1],
        image.shape[1],
    ]
    return image.reshape(new_shape)
    
def is_valid_image(image: ndarray) -> bool:
    return len(image.shape) == 3 and image.shape[2] in [1,2,3,4]
    
def are_images_compatible(image_1: ndarray, image_2: ndarray, close_match: bool = True) -> bool:
    if close_match:
        return image_1.shape == image_2.shape
    else:
        return image_1.shape[:2] == image_2.shape[:2]
    
def overlay_image(background: ndarray, foreground: ndarray) -> ndarray:

    b = unravel(background)
    alpha_b = b[:,[3]]
    f = unravel(foreground)
    alpha_f = f[:,[3]]

    alpha = alpha_f + alpha_b * (1.0 - alpha_f)
    combined = (f * alpha_f) + (b * alpha_b * (1.0 - alpha_f))
    combined = np.divide(combined, alpha, out=np.zeros_like(b), where=alpha!=0)
    return format(combined, background.shape[:2])

def bw_to_alpha(image: ndarray) -> ndarray:
    base_shape: tuple[int, int] = image.shape[:2]
    new_unravel = np.repeat(1.0, base_shape[0] * base_shape[1] * 4).reshape([base_shape[0] * base_shape[1], 4])
    new_unravel[:,3] = unravel(image)[:,0]
    return format(new_unravel, base_shape)

def tint_image(image: ndarray, uniform_color: tuple[float, float, float]) -> ndarray:
    i = unravel(image)
    i[:] = i[:] * np.array([*uniform_color,1.0], dtype='float32')
    return format(i, image.shape[:2])
    
def empty_image(base_shape: tuple[int, int], channels: int = 4, flatten: bool = False) -> ndarray:
    image = np.zeros([int(base_shape[0]), int(base_shape[1]),channels], dtype='float32')
    if flatten:
        return image.flatten()
    else:
        return image

def resize_image(image: ndarray, base_shape: tuple[int, int], bilinear: bool = False):
    original_size = image.shape[:2]
    if original_size == base_shape:
        return image
    ratio = (original_size[0] / base_shape[0], original_size[1] / base_shape[1])
    grid = get_index_grid(base_shape, dtype='float16')
    grid[:,:,0] *= ratio[0]
    grid[:,:,1] *= ratio[1]

    if not bilinear:
        return sample_image(image, grid, mode='round') 
    else:
        nfloor = lambda x: np.int16(np.floor(x))
        nceil = lambda x, y: np.clip(np.int16(np.ceil(x)), 0, y - 1)

        frac = np.mod(grid, 1.0)
        fxc = frac[:,:,[0]]
        fxf = 1.0 - fxc
        p1f = image[
            nfloor(grid[:,:,0]),
            nfloor(grid[:,:,1]),
        ]
        p1c = image[
            nceil(grid[:,:,0], original_size[0]),
            nfloor(grid[:,:,1])
        ]
        p1 = p1c * fxc + p1f * fxf

        p2f = image[
            nfloor(grid[:,:,0]),
            nceil(grid[:,:,1], original_size[1])
        ]
        p2c = image[
            nceil(grid[:,:,0], original_size[0]),
            nceil(grid[:,:,1], original_size[1])
        ]
        p2 = p2c * fxc + p2f * fxf
        fyc = frac[:,:,[1]]
        p = p2 * fyc + p1 * (1.0 - fyc)

        return p

def get_index_grid(base_shape: tuple[int, int], dtype='int16'):
    y, x = base_shape
    row = np.resize(np.arange(x, dtype=dtype), [y,x])
    column = np.resize(np.arange(y, dtype=dtype), [x,y]).swapaxes(0,1)
    grid  = np.zeros([y,x,2], dtype=dtype)
    grid[:,:,1] = row
    grid[:,:,0] = column
    return grid
    

def sample_image(image: ndarray, index_grid: ndarray, mode: str = 'round'):
    s = image.shape[:2]
    if not mode is None:
        g = np.int16(getattr(np, mode)(index_grid))
    return image[
        np.clip(g[:,:,0], 0, s[0] - 1),
        np.clip(g[:,:,1], 0, s[1] - 1)
    ]

def gradient(
    base_shape: tuple[int, int], 
    color_1: tuple[float, float, float, float], 
    color_2: tuple[float, float, float, float], 
    direction: Literal['HOR', 'VER']) -> ndarray:
    grid = get_index_grid(base_shape, dtype='float16')
    gradient = {
        'HOR': grid[:,:,[1]] / base_shape[1],
        'VER': grid[:,:,[0]] / base_shape[0],
    }[direction]

    return np.float32(color_1 * gradient + color_2 * (1.0 - gradient))

def average_color(image: ndarray) -> ndarray:
    return np.average(unravel(image), axis=0)

def linear_to_srgb(pixels: ndarray) -> ndarray:
    is_below_threshold = pixels < 0.0031308
    return np.where(
        is_below_threshold,
        pixels * 12.92,
        1.055 * (pixels ** (1.0 / 2.4)) - 0.055
    )
