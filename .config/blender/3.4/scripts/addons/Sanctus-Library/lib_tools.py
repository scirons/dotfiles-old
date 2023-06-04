from pathlib import Path
import os, sys, subprocess, json

#IMAGES

def to_bip_file(image_file: Path):
    return Path(os.path.splitext(str(image_file))[0] + '.bip')

def convert_image(image_file: Path, output_file: Path = None, force_update: bool = False) -> Path:

    if output_file == None:
        output_file = to_bip_file(image_file)

    if output_file.exists() and not force_update:
        print(f'File "{str(output_file)}" already exists. Dont write File.')
        return output_file
    
    try:
        subprocess.Popen(f'"{sys.executable}" -m t3dn_bip_converter "{str(image_file)}" "{str(output_file)}"', shell=False)
    except:
        import traceback
        traceback.print_exc()
        return None
    
    return output_file

def convert_images(image_files: list[Path], output_files: list[Path] = [], force_update: bool = False):

    if output_files == []:
        output_files = [to_bip_file(x) for x in image_files]
    
    if not len(output_files) == len(image_files):
        raise ValueError(f'Length of output files ({len(output_files)}) does not match length of image files ({len(image_files)})')
    
    for i, o in zip(image_files, output_files):
        convert_image(i, o, force_update=force_update)

def remove_bip_image(image_file: Path):

    if not image_file.exists():
        raise FileNotFoundError(f'File "{str(image_file)}" does not exist. Can not remove.')
    if not image_file.suffix == '.bip':
        raise FileNotFoundError(f'File "{str(image_file)}" is not a BIP file. Can not remove.')

    image_file.unlink()

#META DATA

def write_meta_file(directory: Path, item_name: str, data: dict, force_update: bool = False) -> Path:

    file = directory.joinpath(f'{item_name}.json')
    if file.exists() and not force_update:
        print(f'File "{str(file)}" already exists. Did not update the file.')
        return

    with file.open('w') as f:
        json.dump(data, f)

    return file

def remove_meta_file(directory: Path, item_name: str):

    file = directory.joinpath(f'{item_name}.json')
    if file.exists():
        file.unlink()