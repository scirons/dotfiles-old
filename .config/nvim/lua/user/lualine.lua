local status_ok, lualine = pcall(require, "lualine")
if not status_ok then
	return
end

local colors = {
  red      = '#d17b49',
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
    b = { fg = colors.black, bg = colors.cyan, },
    c = { fg = colors.white, bg = colors.black},
    y = { fg = colors.black, bg = colors.cyan, gui = 'bold' },
    z = { fg = colors.black, bg = colors.cyan},

  },

  insert =  { a = { fg = colors.black, bg = colors.red,    gui = 'bold' } },
  visual =  { a = { fg = colors.black, bg = colors.white,  gui = 'bold' } },
  replace = { a = { fg = colors.black, bg = colors.yellow, gui = 'bold' } },

--  inactive = {
--    a = { fg = colors.white, bg = colors.black },
--    b = { fg = colors.white, bg = colors.black },
--    c = { fg = colors.black, bg = colors.black },

}

-- cool function for progress
local progress = function()
	local current_line = vim.fn.line(".")
	local total_lines = vim.fn.line("$")
	local chars = { "__", "▁▁", "▂▂", "▃▃", "▄▄", "▅▅", "▆▆", "▇▇", "██" }
	local line_ratio = current_line / total_lines
	local index = math.ceil(line_ratio * #chars)
	return chars[index]
end

require('lualine').setup {
  options = {
    theme = scyrons_theme,
    icons_enabled = true,
    component_separators = { left = '', right = ''},
    section_separators = { left = '|', right = '|'},
    disabled_filetypes = {},
    always_divide_middle = true,
  },
 sections = {
    lualine_a = {'mode'},
    lualine_b = {"%{&spell ? '[en_US.utf8]' : '[NoSpell]'}"},
    lualine_c = {'branch','filename'},
    lualine_x = {'fileformat', 'filetype', 'diff', 'diagnostics'},
    lualine_y = { progress, 'progress'  },
    lualine_z = {'location'}
  },
  inactive = {
    lualine_a = {},
    lualine_b = {},
--    lualine_c = {'filename'},
--    lualine_x = {'location'},
    lualine_y = {},
    lualine_z = {}
  },
  tabline = {},
  extensions = {}
}
