local opts = { noremap = true, silent = true }
local optsc = { cnoremap = true }
local term_opts = { silent = true }

-- Shorten function name
local keymap = vim.api.nvim_set_keymap

--Remap space as leader key
keymap("", "<Space>", "<Nop>", opts)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Modes
--   normal_mode = "n",
--   insert_mode = "i",
--   visual_mode = "v",
--   visual_block_mode = "x",
--   term_mode = "t",
--   command_mode = "c",

-- Better window navigation
keymap("n", "<C-h>", "<C-w>h", opts)
keymap("n", "<C-j>", "<C-w>j", opts)
keymap("n", "<C-k>", "<C-w>k", opts)
keymap("n", "<C-l>", "<C-w>l", opts)

-- Resize with arrows
keymap("n", "<S-J>", ":resize +2<CR>", opts)
keymap("n", "<S-K>", ":resize -2<CR>", opts)
keymap("n", "<S-H>", ":vertical resize +2<CR>", opts)
keymap("n", "<S-L>", ":vertical resize -2<CR>", opts)

-- Compile document, be it groff/LaTeX/markdown/etc
keymap("","<leader>c",":w! !compiler <c-r>%<CR>",opts)

-- Goyo plugin activation for prose
keymap("","<leader>f",":Goyo | set linebreak<CR>",opts)

-- Open corresponding .pdf/.html or preview
keymap("","<leader>p",":!opout <c-r>%<CR><CR>",opts)

-- Spell-check set to <leader>o, 'o' for 'orthography'
keymap("n","<leader>o",":setlocal spell!<CR>", opts)

-- Enable css colors
keymap("","<leader>h",":ColorizerToggle<CR>", opts)
