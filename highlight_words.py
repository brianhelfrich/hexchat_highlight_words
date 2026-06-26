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
__module_version__ = "0.7"
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


def _build_pattern(
    words: list[str], whole_words: bool = False
) -> re.Pattern[str] | None:
    cleaned = [re.escape(w) for w in words if w]
    if not cleaned:
        return None
    # \b handles most latin words; adjust for unicode boundaries if needed.
    alt = "|".join(cleaned)
    body = rf"\b({alt})\b" if whole_words else rf"({alt})"
    return re.compile(body, re.IGNORECASE)


PATTERN = _build_pattern(HIGHLIGHT_WORDS, USE_WORD_BOUNDARIES)


def _active_color(segment: str, state: str) -> str:
    """Return the color sequence in effect after `segment`, starting from `state`.

    Tracks just enough mIRC state to restore color after a highlight: the last
    `\\003fg[,bg]` wins; a bare `\\003` or a `\\017` reset clears it. Color codes
    are normalized to 2-digit fields so re-emitting them can't merge with any
    following digit. Bold/italic/underline toggles are left untouched.
    """
    i, n = 0, len(segment)
    while i < n:
        ch = segment[i]
        if ch == RESET:
            state = ""
            i += 1
        elif ch == COLOR:
            i += 1
            fg = ""
            while i < n and segment[i].isdigit() and len(fg) < 2:
                fg += segment[i]
                i += 1
            bg = ""
            if fg and i + 1 < n and segment[i] == "," and segment[i + 1].isdigit():
                i += 1  # skip the comma
                while i < n and segment[i].isdigit() and len(bg) < 2:
                    bg += segment[i]
                    i += 1
            # Bare \003 (no digits) toggles color off; otherwise set fg[,bg].
            state = (
                COLOR + fg.zfill(2) + ("," + bg.zfill(2) if bg else "") if fg else ""
            )
        else:
            i += 1
    return state


def _highlight_text(text: str) -> str:
    """Recolor each matched word, then restore the formatting that preceded it.

    Works inside already-colored messages: the color active before a match is
    re-applied afterward (or `\\017` reset if none), so the rest of the line keeps
    its original color instead of being truncated by the highlight.
    """
    if PATTERN is None:
        return text

    out = []
    state = ""  # color sequence active at the current position
    last = 0
    for m in PATTERN.finditer(text):
        pre = text[last : m.start()]
        out.append(pre)
        state = _active_color(pre, state)
        # 2-digit code so it can't merge with a leading digit of the match.
        restore = state or RESET
        out.append(f"{COLOR}{COLOR_CODE.zfill(2)}{m.group(0)}{restore}")
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def _relay(event_name: str, word: list[str], time: float = 0.0) -> int:
    global _emitting

    # Ignore the echo of our own re-emit, and bail when there's nothing to match.
    if _emitting or PATTERN is None:
        return hexchat.EAT_NONE

    try:
        message = word[MESSAGE_INDEX]
    except IndexError:
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
