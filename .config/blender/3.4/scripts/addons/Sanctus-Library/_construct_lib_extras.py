import os, sys, subprocess, argparse, json
from pathlib import Path

CONVERT_FROM = ['.png', '.jpg',]

LIB_PATH = Path(__file__).parent.joinpath('lib')

LIBRARIES: list[Path] = [
    LIB_PATH.joinpath('icons'),
    LIB_PATH.joinpath('materials'),
    LIB_PATH.joinpath('tools')
]

def scan_directory(dir: Path, remove_images=False) -> dict[str,list[Path]]:
    
    results = {
        'images':[],
        'meta_files':[]
    }

    if (meta_file := dir.joinpath('_meta.txt')).exists():
        results['meta_files'].append(meta_file)

    for entry in dir.glob('*'):
        if entry.is_dir():
            sub_results = scan_directory(entry, remove_images=remove_images)
            results['images'] += sub_results['images']
            results['meta_files'] += sub_results['meta_files']
        elif entry.is_file():
            if remove_images and entry.suffix == '.bip':
                results['images'].append(entry)
            if not remove_images and entry.suffix in CONVERT_FROM:
                results['images'].append(entry)
    return results

def main():

    sys.path.append(os.path.dirname(__file__))
    import lib_tools

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--remove', action='store_const', dest='use_remove', default=False, const=True)
    args = parser.parse_args()
    is_remove = args.use_remove

    for lib in LIBRARIES:
        print(lib)
        
        results = scan_directory(lib, remove_images=is_remove)
        image_files = results['images']
        dir_meta_files = results['meta_files']
        if is_remove:
            print('Removing Images...')
            for f in image_files:
                lib_tools.remove_bip_image(f)
            
        else:
            print('Creating Images...')
            lib_tools.convert_images(image_files)

        print('-'*30)
    
    input('Done converting images.')

if __name__ == '__main__':
    main()
