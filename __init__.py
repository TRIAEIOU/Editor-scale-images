###########################################################################
# EDITOR SCALE IMAGES
# On select wrap img in scalable div and set img to fill div. When
# deselected set img width/height from div and remove div. Leave as much
# of img attributes untouched as possible, only change inline style
# elements display, pointer-events, object-fit, height, width, min-width,
# max-width.
###########################################################################
import re
from aqt import gui_hooks, mw
from aqt.editor import Editor
from anki import hooks
from anki.notes import Note

ESI_CFG_SELECTED_BORDER = "Selected border"

###########################################################################
# Only create one instance of select/deselect functions to ensure as
# few event handlers being registered as possible (duplicates in same DOM
# to same handler are ignored according to spec)
#
# esi_select wraps clicked img in a scale div and sets img to follow div
# esi_deselect removes wrapping div and sets img height/width
###########################################################################
def on_init(editor: Editor):
    js = rf"""
        /* Addon Editor scale images - begin */
        function esi_select(evt) {{
            if(evt.target.nodeName === "IMG") {{
                esi = {{
                    div: document.createElement("div"),
                    field: null,
                    fieldcc: 'auto',
                    width: evt.target.width,
                    style: evt.target.style
                }}
                esi['div'].className = "esi_scale_div";
                esi['div'].style.cssText = `cursor: crosshair; border: {on_init.border}; overflow: hidden; resize: horizontal; display: inline-block; width: ${{evt.target.width}}px;`;
                evt.target.parentNode.insertBefore(esi['div'], evt.target);
                evt.target.style.display = "block";
                evt.target.style.pointerEvents = "none";
                evt.target.style.objectFit = "contain";
                evt.target.style.height = "auto";
                evt.target.style.width = "100%";
                evt.target.style.minWidth = null;
                evt.target.style.maxWidth = null;
                esi['div'].appendChild(evt.target);
                esi['field'] = esi['div'].getRootNode().querySelector('anki-editable');
                esi['fieldcc'] = esi['field'].style.caretColor;
                esi['field'].style.caretColor = 'transparent';
                let rng = document.createRange();
                let sel = window.getSelection();
                rng.setStart(esi['div'].nextSibling ? esi['div'].nextSibling : esi['div'], 0);
                rng.collapse(true);
                sel.removeAllRanges();
                sel.addRange(rng);
            }}
        }}

        function esi_deselect(evt) {{
            if(esi && (esi['div'] != evt.target || evt.type == "keydown")) {{
                esi['div'].firstChild.style = esi['style'];
                if(esi['width'] != esi['div'].clientWidth) {{
                    esi['div'].firstChild.style.width = "contain";
                    esi['div'].firstChild.style.height = "auto";
                    esi['div'].firstChild.style.width = `${{esi['div'].clientWidth}}px`;
                    esi['div'].firstChild.style.minWidth = `${{esi['div'].clientWidth}}px`;
                    esi['div'].firstChild.style.maxWidth = `${{esi['div'].clientWidth}}px`;
                }}
                esi['field'].style.caretColor = esi['fieldcc'];
                esi['div'].replaceWith(esi['div'].firstChild);
                esi = null;
            }}
        }}

        function esi_reset(evt) {{
            if(esi && esi['div'] === evt.target) {{
                esi['div'].firstChild.style.pointerEvents = "auto";
                esi['div'].firstChild.style.height = "auto";
                esi['div'].firstChild.style.width = null;
                esi['div'].firstChild.style.minWidth = null;
                esi['div'].firstChild.style.maxWidth = null;
                esi['field'].style.caretColor = esi['fieldcc'];
                esi['div'].replaceWith(esi['div'].firstChild);
                window.getSelection().removeAllRanges();
                esi = null;
            }}
        }}
        /* Addon Editor scale images - end */
        """
    editor.web.eval(js)
on_init.border = "2px solid #99D1FF" # function attribute as static var

###########################################################################
# On note load add event handlers to each field shadow root, the handlers
# should be removed automatically when the shadow root is destroyed (on
# loading next note). Check if ESI already setup before registering event
# handlers (shouldn't be needed).
# mousedown leads to deselect any old (unless new == old to capture resize
# mousedown), so does keydown => unable to edit but can scroll with mouse
# etc. while selected. click (i.e. on mouse up) selects any img.
# esi['div'] contains currently selected (wrapping) div or null.
###########################################################################
def on_load(js: str, note: Note, editor: Editor):
    js+= """
        /* Addon Editor scale images - begin */
        if(typeof esi === 'undefined') {{
            let fields = document.getElementsByClassName("field");
            for(let i = 0; i < fields.length; i++) {{
                fields[i].shadowRoot.addEventListener("click", esi_select);
                fields[i].shadowRoot.addEventListener("dblclick", esi_reset);
                fields[i].shadowRoot.addEventListener("keydown", esi_deselect);
                fields[i].shadowRoot.addEventListener("mousedown", esi_deselect);
            }}
            var esi = null;
        }}
        /* Addon Editor scale images - end */
    """
    return js

###########################################################################
# Intercept note save to DB to unwrap any wrapped img. Keep initial pattern
# simple as matches will be few.
###########################################################################
def on_flush(note: Note):
    def unwrap(match):
        if not unwrap.pattern:
            unwrap.pattern = re.compile(r'.*?width:\s*([0-9\.]+).*?(<img.*?style=")(.*?)(".*?>)</div>')
        wrapper = re.match(unwrap.pattern, match.group(0))
        els = [el.split(':') for el in wrapper.group(3).split(';') if el]
        styles = dict((key.strip(), val.strip()) for key, val in els)
        styles['display'] = "inline-block"
        styles['pointer-events'] = "auto"
        styles['object-fit'] = "contain"
        styles['height'] = "auto"
        styles['width'] = f"{wrapper.group(1)}px"
        styles['min-width'] = f"{wrapper.group(1)}px"
        styles['max-width'] = f"{wrapper.group(1)}px"
        style = "; ".join(f"{key}: {val}" for key, val in styles.items()) + ";"
        return f"{wrapper.group(2)}{style}{wrapper.group(4)}"
    unwrap.pattern = None # function attribute as static var to keep compiled regex

    if not on_flush.pattern:
            on_flush.pattern = re.compile(r'<div\s[^>]*class="esi_scale_div".*?</div>')
    for i, field in enumerate(note.fields):
        note.fields[i] = re.sub(on_flush.pattern, unwrap, field)
on_flush.pattern = None # function attribute as static var to keep compiled regex


###########################################################################
# "Main" - load config and set up hooks
###########################################################################
config = mw.addonManager.getConfig(__name__)
if config.get(ESI_CFG_SELECTED_BORDER):
    on_init.border = config[ESI_CFG_SELECTED_BORDER]

gui_hooks.editor_did_init.append(on_init)
gui_hooks.editor_will_load_note.append(on_load)
hooks.note_will_flush.append(on_flush)
