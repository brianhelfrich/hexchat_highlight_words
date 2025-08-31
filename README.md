# HexChat Highlight Words

A simple Python plugin for [HexChat](https://hexchat.github.io/) that highlights specified words in chat messages.

## Features
- Highlights configured words in **red** (default), using mIRC color codes.
- Works in:
  - Channel messages
  - Highlighted channel messages
  - Channel actions (`/me`)
  - Private messages
  - Your own messages
- Case-insensitive matching
- Optional whole-word matching
- Compatible with both newer and older HexChat builds:
  - Uses `hook_print_attrs` / `emit_print_attrs` if available
  - Falls back to `hook_print` / `emit_print` when attrs API is missing

## Installation
1. Copy `highlight_words.py` into your HexChat addons directory:
   - **Linux**: `~/.config/hexchat/addons/`
   - **Windows**: `%APPDATA%\HexChat\addons\`

2. In HexChat, load the script:
```text
/load highlight_words.py
```
3. Edit the script and adjust these variables:
```python
HIGHLIGHT_WORDS = ["example", "highlight"]   # Words to highlight
COLOR_CODE = "04"             # mIRC color code (default: red)
USE_WORD_BOUNDARIES = False   # True = match whole words only
```

## Example
With 'example' and 'highlight' are in your highlight list with USE_WORD_BOUNDARIES = False:

```text
<jack> this is an example of highlighted text
```

Becomes:
```text
<jack> this is an [red]example[/reset] of [red]highlight[/reset]ed text
```

## Notes
- If USE_WORD_BOUNDARIES = True, only exact words are highlighted (e.g., highlight ≠ highlighted, ignored and remains untouched).
- Color bleeding is prevented by automatically resetting formatting after each match.
- The script auto-detects whether your HexChat build supports the attrs API:
   - With attrs: highlights preserve timestamps, markers, and formatting.
   - Without attrs: highlights still work correctly, but without extra metadata.