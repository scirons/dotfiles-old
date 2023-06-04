require "user.keymaps"
require "user.autocommands"
require "user.plugins"
require "user.cmp"
require "user.lsp"
require "user.treesitter"
require "user.autopairs"
require "user.lualine"
require "user.xresources"

local options = {
  title = true,                            -- automatically set screen title
  backup = false,                          -- creates a backup file
   --  go = "a",				                   -- append text after cursor to the first column on go command
  clipboard = "unnamedplus",               -- allows neovim to access the system clipboard
  cmdheight = 2,                           -- more space in the neovim command line for displaying messages
  completeopt = { "menuone", "noselect" }, -- mostly just for cmp
  spelllang = "en_us",
  conceallevel = 0,                        -- so that `` is visible in markdown files
  fileencoding = "utf-8",                  -- the encoding written to a file
  hlsearch = false,                         -- highlight all matches on previous search pattern
  ignorecase = true,                       -- ignore case in search patterns
  mouse = "a",                             -- allow the mouse to be used in neovim
  pumheight = 10,                          -- pop up menu height
  showmode = false,                        -- we don't need to see things like -- INSERT -- anymore
  showtabline = 1,                         -- always show tabs
  smartcase = true,                        -- smart case
  smartindent = true,                      -- make indenting smarter again
  splitbelow = true,                       -- force all horizontal splits to go below current window
  splitright = true,                       -- force all vertical splits to go to the right of current window
  swapfile = false,                        -- creates a swapfile
  termguicolors = true,                    -- set term gui colors (most terminals support this)
  timeoutlen = 100,                        -- time to wait for a mapped sequence to complete (in milliseconds)
  undofile = true,                         -- enable persistent undo
  updatetime = 300,                        -- faster completion (4000ms default)
  writebackup = false,                     -- if a file is being edited by another program (or was written to file while editing with another program), it is not allowed to be edited
  expandtab = true,                        -- convert tabs to spaces
  shiftwidth = 2,                          -- the number of spaces inserted for each indentation
  tabstop = 2,                             -- insert 2 spaces for a tab
  cursorline = true,                       -- highlight the current line
  number = true,                           -- set numbered lines
  relativenumber = true,                  -- set relative numbered lines
  numberwidth = 4,                         -- set number column width to 2 {default 4}
  signcolumn = "yes",                      -- always show the sign column, otherwise it would shift the text each time
  wrap = false,                            -- display lines as one long line
  scrolloff = 8,                           -- is one of my fav
  sidescrolloff = 8,
  guifont = "monospace:h17",               -- the font used in graphical neovim applications
  background = "light",                     -- system colorschemes used properly
}

vim.opt.shortmess:append "c"

for k, v in pairs(options) do
  vim.opt[k] = v
end

vim.cmd "set whichwrap+=<,>,[,],h,l"
vim.cmd [[set iskeyword+=-]]
vim.cmd [[set formatoptions-=cro]] -- TODO: this doesn't seem to work
vim.cmd "hi LineNr guifg=#d17b49"
vim.cmd "hi Normal guibg=#171717"
vim.cmd "hi signcolumn guibg=#171717"
-- vim.cmd "hi CursorLine term=underline cterm=NONE gui=NONE ctermbg=black"
-- vim.cmd "hi TabLineFill ctermfg=black"
-- vim.cmd "highlight Pmenu ctermfg=yellow"
-- vim.cmd "highlight Pmenu ctermbg=black"
vim.cmd "hi LspReferenceRead ctermbg=237 guibg=#303030"
vim.cmd "hi LspReferenceText ctermbg=237 guibg=#303030"
vim.cmd "hi LspReferenceWrite ctermbg=237 guibg=#303030"
