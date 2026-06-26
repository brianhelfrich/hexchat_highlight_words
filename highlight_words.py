# hexchat_highlight_words/highlight_words.py
"""Highlight configured words in HexChat messages by recoloring just the match.

Install:
  1. Copy this file into your HexChat addons folder:
       Linux:   ~/.config/hexchat/addons/
       Windows: %APPDATA%\\HexChat\\addons\\
  2. Load it in HexChat:  /load highlight_words.py
  3. Edit HIGHLIGHT_WORDS / COLOR_CODE / USE_WORD_BOUNDARIES below.

How it works: the relevant text events are hooked, each matched word is wrapped
in mIRC color codes, and the *same* event is re-emitted with the modified text.
A module-level recursion guard (`_emitting`) suppresses the hook while our own
re-emit is in flight. Re-emitting the original event (rather than a generic one)
keeps HexChat's native rendering — nick color, mode char, timestamp — so only
the matched word changes color instead of the whole line.
"""

import re

import hexchat

__module_name__ = "Highlight Words"
__module_version__ = "0.6"
__module_description__ = "Highlight identified words in red font"

# === Configuration ===
HIGHLIGHT_WORDS = ["example", "highlight"]
COLOR_CODE = "04"  # Red (mIRC/HexChat color code)
USE_WORD_BOUNDARIES = False  # Set True to match whole words only

# mIRC/HexChat control codes
COLOR = "\003"  # Start a color (followed by a 2-digit code)
RESET = "\017"  # Reset all formatting

# Newer builds expose the *_attrs print hook, which carries server-time.
HAS_ATTRS = hasattr(hexchat, "hook_print_attrs")

# The text payload is field 1 (right after the nick) for every event we hook.
MESSAGE_INDEX = 1

# Recursion guard: our own emit_print re-triggers the hook we registered.
_emitting = False


def _build_patterns(
    words: list[str], whole_words: bool = False
) -> list[re.Pattern[str]]:
    pats = []
    for w in words:
        # \b handles most latin words; adjust for unicode boundaries if needed.
        body = rf"\b({re.escape(w)})\b" if whole_words else rf"({re.escape(w)})"
        pats.append(re.compile(body, re.IGNORECASE))
    return pats


PATTERNS = _build_patterns(HIGHLIGHT_WORDS, USE_WORD_BOUNDARIES)


def _highlight_text(text: str) -> str:
    # Wrap each match in color + reset so the color never bleeds past the word.
    new_text = text
    for pat in PATTERNS:
        new_text = pat.sub(rf"{COLOR}{COLOR_CODE}\1{RESET}", new_text)
    return new_text


def _relay(event_name: str, word: list[str], time: float = 0.0) -> int:
    global _emitting

    # Ignore the echo of our own re-emit, and bail when there's nothing to match.
    if _emitting or not PATTERNS:
        return hexchat.EAT_NONE

    try:
        message = word[MESSAGE_INDEX]
    except IndexError:
        return hexchat.EAT_NONE

    # Leave already-colored messages alone: inserting a reset mid-line would
    # truncate the existing coloring of the rest of the message.
    if COLOR in message:
        return hexchat.EAT_NONE

    highlighted = _highlight_text(message)
    if highlighted == message:
        return hexchat.EAT_NONE

    # Re-emit the full event so the mode char / identified flag survive.
    new_word = list(word)
    new_word[MESSAGE_INDEX] = highlighted

    _emitting = True
    try:
        if time:
            hexchat.emit_print(event_name, *new_word, time=time)
        else:
            hexchat.emit_print(event_name, *new_word)
    finally:
        _emitting = False

    # Swallow the original, unmodified print; our re-emit replaces it.
    return hexchat.EAT_HEXCHAT


def cb_attrs(word, word_eol, userdata, attributes) -> int:
    # Newer builds: preserve server-time by threading it into the re-emit.
    return _relay(userdata, word, time=attributes.time)


def cb_plain(word, word_eol, userdata) -> int:
    return _relay(userdata, word)


# === Hooks ===
HOOK = hexchat.hook_print_attrs if HAS_ATTRS else hexchat.hook_print
CB = cb_attrs if HAS_ATTRS else cb_plain

# Pass each event name as userdata so the callback knows which event to re-emit.
EVENTS = [
    "Channel Message",
    "Channel Msg Hilight",
    "Channel Action",
    "Channel Action Hilight",
    "Your Message",
]
for event in EVENTS:
    HOOK(event, CB, event)

# On some installs the private-message event is named differently.
for evt in ("Private Message to Dialog", "Private Message"):
    try:
        HOOK(evt, CB, evt)
        break
    except Exception:
        continue

hexchat.prnt(f"{__module_name__} {__module_version__} loaded (attrs={HAS_ATTRS})")
