# ~/.config/hexchat/addons/highlight_words.py
#
# To use:
# 1. Save this script as "highlight_words.py" in your HexChat addons folder
# 2. Load the script in HexChat: /load highlight_words.py
# 3. Set the words you want to highlight in the "HIGHLIGHT_WORDS" list below

import hexchat
import re

__module_name__ = "Highlight Words"
__module_version__ = "0.5"
__module_description__ = "Highlight identified words in red font"

# === Configuration ===
HIGHLIGHT_WORDS = ["example", "highlight"]
COLOR_CODE = "04"  # Red (mIRC/HexChat color code)
USE_WORD_BOUNDARIES = False  # Set True to match whole words only

# Feature detection: some builds lack the *_attrs APIs
HAS_ATTRS = hasattr(hexchat, "hook_print_attrs") and hasattr(hexchat, "emit_print_attrs")

# Precompile patterns for speed
def _build_patterns(words, whole_words=False):
    pats = []
    for w in words:
        if whole_words:
            # \b is OK for most latin words; if you need unicode boundaries, adjust here.
            pat = re.compile(rf"\b({re.escape(w)})\b", re.IGNORECASE)
        else:
            pat = re.compile(rf"({re.escape(w)})", re.IGNORECASE)
        pats.append(pat)
    return pats

PATTERNS = _build_patterns(HIGHLIGHT_WORDS, USE_WORD_BOUNDARIES)

# mIRC/HexChat control codes
COLOR = "\003"
RESET = "\017"  # Reset all formatting (safer than bare \003)

# Fast precheck: bail if no patterns or no matches
def _would_match(text):
    return any(p.search(text) for p in PATTERNS)

def _already_colored(text):
    # skip highlighting if the message already contains color codes
    return "\003" in text

# Main functions
def _highlight_text(text):
    new_text = text
    for pat in PATTERNS:
        # Wrap match with color + reset to avoid bleeding color to rest of line
        new_text = pat.sub(rf"{COLOR}{COLOR_CODE}\1{RESET}", new_text)
    return new_text

# --- Callbacks ---
def _cb_common(word):
    try:
        nick = word[0]
        message = word[1]
    except IndexError:
        return None, None, hexchat.EAT_NONE

    if not PATTERNS or not _would_match(message):
        return None, None, hexchat.EAT_NONE
    if _already_colored(message):
        return None, None, hexchat.EAT_NONE

    highlighted = _highlight_text(message)
    if highlighted == message:
        return None, None, hexchat.EAT_NONE

    return nick, highlighted, None

def cb_attrs(word, word_eol, userdata, attributes):
    nick, highlighted, eat = _cb_common(word)
    if eat is not None:
        return eat
    # Re-emit with attributes (newer HexChat builds)
    hexchat.emit_print_attrs("Generic Message", attributes, nick, highlighted)
    return hexchat.EAT_HEXCHAT

def cb_plain(word, word_eol, userdata):
    nick, highlighted, eat = _cb_common(word)
    if eat is not None:
        return eat
    # Re-emit without attributes (older HexChat builds)
    hexchat.emit_print("Generic Message", nick, highlighted)
    return hexchat.EAT_HEXCHAT

# --- Hooks ---
HOOK = hexchat.hook_print_attrs if HAS_ATTRS else hexchat.hook_print
CB   = cb_attrs if HAS_ATTRS else cb_plain

HOOK("Channel Message", CB)
HOOK("Channel Msg Hilight", CB)
HOOK("Channel Action", CB)
HOOK("Channel Action Hilight", CB)
# On some installs this is "Private Message" rather than "... to Dialog"
for evt in ("Private Message to Dialog", "Private Message"):
    try:
        HOOK(evt, CB)
        break
    except Exception:
        continue
HOOK("Your Message", CB)

hexchat.prnt(f"{__module_name__} {__module_version__} loaded (attrs={HAS_ATTRS})")