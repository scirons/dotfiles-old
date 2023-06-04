local status_ok, orgmode = pcall(require, "orgmode")
if not status_ok then
  return
end

-- Load custom tree-sitter grammar for org filetype


require('orgmode').setup{
  org_capture_float = true,
  org_todo_keywords = {'TODO(t)', 'NEXT(n)', 'WAITING(w)', 'SOMEDAY(s)', 'PROJ(p)', '|', 'DONE(d)', 'CANCELLED(c)'},
  org_indent_mode = 'noindent',
  org_agenda_files = '~/.local/src/org/agenda/*',
  org_default_notes_file = '~/.local/src/org/refile.org',
}
