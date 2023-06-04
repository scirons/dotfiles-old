#!/usr/bin/python
# coding'UTF-8
# These glyphs, and the mapping of file extensions to glyphs
# has been copied from the vimscript code that is present in
# https://github.com/ryanoasis/vim-devicons
import re;
import os;

# all those glyphs will show as weird squares if you don't have the correct patched font
# My advice is to use NerdFonts which can be found here:
# https://github.com/ryanoasis/nerd-fonts
file_node_extensions = {

'di':' ',
'txt':' ',
'mom':' ',
'me':' ',
'ms':' ',
'log':' ',
'png':' ',
'webp':': ',
'ico':' ',
'jpg':' ',
'jpe':' ',
'jpeg':': ',
'gif':' ',
'svg':' ',
'tif':' ',
'tiff':' ',
'html':' ',
'xml':' ',
'gpg':' ',
'pdf':' ',
'djvu':' ',
'epub':' ',
'csv':' ',
'xlsx':' ',
'tex':' ',
'md':' ',
'r':' ',
'r':' ',
'rmd':' ',
'rmd':' ',
'm':' ',
'mp3':' ',
'opus':' ',
'ogg':' ',
'm4a':' ',
'flac':' ',
'wav':' ',
'mkv':' ',
'mp4':' ',
'webm':' ',
'mpeg':' ',
'avi':' ',
'mov':' ',
'mpg':' ',
'wmv':' ',
'm4b':' ',
'flv':' ',
'zip':' ',
'rar':' ',
'7z':' ',
'tar':' ',
'gz':' ',
'nfo':' ',
'info':' ',
'iso':'. ',
'img':'. ',
'torrent':' ',
}

dir_node_exact_matches = {
# English
    '.git'                             : ' ',
    'Documents'                        : 'i',
    'Downloads'                        : ' ',
    'Music'                            : ' ',
    'Personal'                         : ' ',
    'Design'                           : ' ',
}

file_node_exact_matches = {
}


def devicon(file):
  if file.is_directory: return dir_node_exact_matches.get(file.relative_path, ' ')
  return file_node_exact_matches.get(os.path.basename(file.relative_path), file_node_extensions.get(file.extension, ' '))
