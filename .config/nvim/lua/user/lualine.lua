
local colors = {
  orange   = '#d17b49',
  yellow   = '#af865a',
  black    = '#1f1f1f',
  grey     = '#4A3637',
  white    = '#c0b18b',
  cyan     = '#6d715e',
  magenta  = '#755759',
}

local scyrons_theme = {
  normal = {
    a = { fg = colors.black, bg = colors.cyan },
    b = { fg = colors.black, bg = colors.cyan },
    c = { fg = colors.white, bg = colors.grey },

  },

  insert  = { a = { fg = colors.black, bg = colors.orange } },
  visual  = { a = { fg = colors.black, bg = colors.white  } },
  replace = { a = { fg = colors.black, bg = colors.yellow } }
  },

require('lualine').setup {
    options = {
    theme = scyrons_theme,
    component_separators = '|',
    section_separators = { left = '', right = '' },
  },
  sections = {
    lualine_a = {
      { 'mode', separator = { left = '' }, right_padding = 2 },
    },
    lualine_b = { 'filename', 'branch' },
    lualine_c = { 'fileformat' },
    lualine_x = {},
    lualine_y = { 'filetype', 'progress' },
    lualine_z = {
      { 'location', separator = { right = '' }, left_padding = 2 },
    },
  },
  inactive_sections = {
    lualine_a = { 'filename' },
    lualine_b = {},
    lualine_c = {},
    lualine_x = {},
    lualine_y = {},
    lualine_z = { 'location' },
  },
  tabline = {},
  extensions = {},
}
