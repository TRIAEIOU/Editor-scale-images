###########################################################################
# INLINE MEDIA
###########################################################################
import sys, os, subprocess, tempfile, re
import distutils.spawn
from urllib.parse import unquote
from urllib.request import urlopen
from aqt import gui_hooks, mw
from anki.hooks import addHook
from aqt.editor import Editor
from aqt.utils import showWarning
from aqt.qt import QApplication, QClipboard
from anki.notes import Note

if distutils.spawn.find_executable('ffmpeg'):
    FFMPEG = 'ffmpeg'
else:
    if sys.platform == 'win32' or sys.platform == 'cygwin':
        FFMPEG = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg.exe')
    elif sys.platform == 'darwin':  
        FFMPEG = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg')
    elif sys.platform == 'linux':
        showWarning(text=f"""<p>Inline media depends on ffmpeg (https://ffmpeg.org/) for media conversion and was unable to find it in the system path. Please install ffmpeg through "sudo apt install ffmpeg" or similar.</p>""", parent=mw, title="Inline media", textFormat="rich")

CFG = {} # Default config
CFG_AUDIO = 'Audio format'
CFG_VIDEO = 'Video format'
CFG_AUTOPLAY = 'Autoplay'
CFG_LOOP = 'Loop'
CFG_MUTE = 'Mute'
CFG_HEIGHT = 'Height'
CFG_WIDTH = 'width'

###########################################################################
# Only create one instance of functions to ensure as few event handlers
# being registered as possible (duplicates in same DOM to same handler are
# ignored according to spec)
###########################################################################
def on_init(editor: Editor):
    editor.web.eval(rf"""
        /* Addon Inline media - begin */
        function im_ctrl(file, opts, index) {{
            let attr = '';
            if(opts.autoplay) {{ attr += ' autoplay'; }}
            if(opts.loop) {{ attr += ' loop'; }}
            if(opts.mute) {{ attr += ' muted'; }}
            if(opts.height > -1) {{attr += ` height="${{opts.height}}"`; }}
            if(opts.width > -1) {{attr += ` width="${{opts.width}}"`; }}
            return `&nbsp;<span id="IM-${{index}}"><${{opts.type}} id="IM-ctrl-${{index}}" controls ${{attr}}><source id="IM-src-${{index}}" src="${{file}}" type="${{opts.type}}/${{opts.ext}}"></${{opts.type}}></span>&nbsp;`;
        }}
        
        function im_update(src, dest) {{
            let res = "";
            let display = dest.innerHTML.split(/(?:&nbsp;)?<span id="IM-\d+".*?<\/span>(?:&nbsp;)?/);

            let i = -1;
            for(const line of src.innerHTML.split(/<[ /]*br[ /]*>/)) {{
                let match = line.match(/^\[sound:([^\]]+\.({CFG[CFG_AUDIO]}|{CFG[CFG_VIDEO]}))\](.*)$/);
                if(match) {{
                    i++;
                    let opts = {{
                        ext: match[2],
                        type: match[2] === '{CFG[CFG_AUDIO]}' ? 'audio' : 'video',
                        autoplay: {'true' if CFG[CFG_AUTOPLAY] else 'false'},
                        loop: {'true' if CFG[CFG_LOOP] else 'false'},
                        mute: {'true' if CFG[CFG_MUTE] else 'false'},
                        height: {CFG[CFG_HEIGHT]},
                        width: {CFG[CFG_WIDTH]}
                    }}
                    for(const opt of match[3].split(/(?:\s|&nbsp;)+/g)) {{
                        let tmp;
                        if(opt.match(/^(a|audio)$/)) {{ opts.type = "audio"; }}
                        else if(opt.match(/^(v|video)$/)) {{ opts.type = "video"; }}
                        else if(opt.match(/^(auto|autoplay)$/)) {{ opts.autoplay = true; }}
                        else if(opt.match(/^(na|noauto|noautoplay)$/)) {{ opts.autoplay = false; }}
                        else if(opt.match(/^(l|loop)$/)) {{ opts.loop = true; }}
                        else if(opt.match(/^(nl|noloop)$/)) {{ opts.loop = false; }}
                        else if(opt.match(/^(m|mute)$/)) {{ opts.mute = true; }}
                        else if(opt.match(/^(nm|nomute)$/)) {{ opts.mute = false; }}
                        else if(tmp = opt.match(/^(h|height)(:|=)?(\d+)$/)) {{ opts.height = parseInt(tmp[3]); }}
                        else if(tmp = opt.match(/^(w|width)(:|=)?(\d+)$/)) {{ opts.width = parseInt(tmp[3]); }}
                    }}
                    
                    if(i < display.length) {{ res += display[i]; }}
                    res += im_ctrl(match[1], opts, i);
                }}
            }}
            i++;
            if(i < display.length) {{ res += display.slice(i).join(''); }}

            if(res != dest.innerHTML) {{
                dest.innerHTML = res;
                for(const el of dest.querySelectorAll('[id^=IM-ctrl-]')) {{ el.pause(); }}
            }}
        }}
        /* Addon Inline media - end */
    """)


###########################################################################
# Pair up fields appropriately
###########################################################################
def on_load(js: str, note: Note, editor: Editor):
    js += r'''
        /* Addon Inline media - begin */
        {
            let flds = {};
            let flds_title = document.getElementsByClassName("fieldname");
            let flds_content = document.getElementsByClassName("field");
            
            for(let i = 0; i < flds_title.length; i++) {
                let match = null;
                if(match = flds_title[i].innerText.match(/^(.*?)(\/media)?$/)) {
                    if(match[2]) {
                        if(!(match[1] in flds)) { flds[match[1]] = { media: flds_content[i].shadowRoot.querySelector("anki-editable") }; }
                        else if('display' in flds[match[1]]) {
                            let tmp = flds_content[i].shadowRoot.querySelector("anki-editable");
                            tmp.addEventListener("focusout", function() { im_update(tmp, fields[match[1]].display); });
                        }
                    } else {
                        if(!(match[1] in flds)) { flds[match[1]] = { display: flds_content[i].shadowRoot.querySelector("anki-editable") }; }
                        else if('media' in flds[match[1]]) {
                            flds[match[1]].media.addEventListener("focusout", function() {
                                im_update(flds[match[1]].media, flds_content[i].shadowRoot.querySelector("anki-editable"));
                            });                                
                        }
                    }
                }
            }
        }
        /* Addon Inline media - end */
    '''
    return js

###########################################################################
# Parse clipboard
###########################################################################
def parse_clipboard():
    files = []

    for url in QApplication.clipboard().mimeData(QClipboard.Mode.Clipboard).urls():
        if url.isLocalFile():
            files.append({'url': None, 'path': url.toLocalFile()})
        else:
            files.append({'url': url.toString(), 'path': None})

    if not files and QApplication.clipboard().mimeData(QClipboard.Mode.Clipboard).hasText():
        url_re = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        for line in QApplication.clipboard().mimeData(QClipboard.Mode.Clipboard).text().split('\n'):
            if re.match(url_re, line):
                files.append({'url': line, 'path': None})
            elif os.path.exists(line):
                files.append({'url': None, 'path': line})

    return files


###########################################################################
# Convert file in clipboard, add to media and insert in field
###########################################################################
def insert(wedit, fmt, files):
    tmp_dir = tempfile.TemporaryDirectory()
    for src in files:
        if(src['url'] and not src['path']):
            fr = urlopen(src['url'])
            src['path'] = os.path.join(tmp_dir.name, unquote(fr.url.rsplit('/', 1)[-1]))
            with open(src['path'], 'b+w') as fw:
                fw.write(fr.read())
        
        (root, ext) = os.path.splitext(src['path'])
        root = os.path.basename(root)
        ext = (ext[1:] if ext[0] == os.extsep else ext).lower()
        if (fmt == "audio" and ext == CFG[CFG_AUDIO]) or (fmt == "video" and ext == CFG[CFG_VIDEO]):
            file = mw.col.media.add_file(src['path'])
        else:
            if fmt == "audio":
                dest = os.path.join(tmp_dir.name, f'{root}.{CFG[CFG_AUDIO]}')
                cmd = [FFMPEG, "-i", src['path'], "-vn", dest]
            else:
                dest = os.path.join(tmp_dir.name, f'{root}.{CFG[CFG_VIDEO]}')
                cmd = [FFMPEG, "-i", src['path'], dest]
            proc_info = subprocess.run(cmd, stdout=subprocess.PIPE, universal_newlines=True, shell=True)
            if not os.path.exists(dest):
                showWarning(text=f"""<p>Failed to convert "{src['url'] or src['path']}" to {fmt}, skipping.</p>""", parent=mw, title="Inline media", textFormat="rich")
                continue
            file = mw.col.media.add_file(dest)
            os.remove(dest)
        
        tag = f'[sound:{file}]'
        wedit.eval(f"""
            var sel = document.activeElement.shadowRoot.getSelection();
            var rng = sel.getRangeAt(0);
            sel.removeAllRanges();
            rng.insertNode(rng.createContextualFragment('{tag}'));
            sel.addRange(rng);
        """)


###########################################################################
# Take config and recursively parse and add shortcuts
###########################################################################
def register_shortcuts(scuts, editor):
    scuts.append(["Ctrl+Alt+F1", lambda files=parse_clipboard(): insert(editor.web, "audio", files)])
    scuts.append(["Ctrl+Alt+F2", lambda files=parse_clipboard(): insert(editor.web, "video", files)])


###########################################################################
# Context menu activation - build and append IM menu items
###########################################################################
def mouse_context(wedit, menu):
    if files:= parse_clipboard():
        menu.addSeparator()
        menu.addAction("Insert clipboard as audio", lambda: insert(wedit, "audio", files), "Ctrl+Alt+F1")
        menu.addAction("Insert cliboard as video", lambda: insert(wedit, "video", files), "Ctrl+Alt+F2")
        menu.addSeparator()


###########################################################################
# "Main" - load config and set up hooks
###########################################################################
CFG = mw.addonManager.getConfig(__name__)
if not CFG.get(CFG_AUDIO):
    CFG[CFG_AUDIO] = 'ogg'
if not CFG.get(CFG_VIDEO):
    CFG[CFG_VIDEO] = 'webm'
CFG[CFG_AUTOPLAY] = False if CFG.get(CFG_AUTOPLAY) and CFG.get(CFG_AUTOPLAY).lower() ==  'false' else True
CFG[CFG_LOOP] = False if CFG.get(CFG_LOOP) and CFG.get(CFG_LOOP).lower() ==  'false' else True
CFG[CFG_MUTE] = True if CFG.get(CFG_MUTE) and CFG.get(CFG_MUTE).lower() ==  'true' else False
if not CFG.get(CFG_HEIGHT):
    CFG[CFG_HEIGHT] = -1
if not CFG.get(CFG_WIDTH):
    CFG[CFG_WIDTH] = -1

gui_hooks.editor_did_init.append(on_init)
gui_hooks.editor_will_load_note.append(on_load)
gui_hooks.editor_did_init_shortcuts.append(register_shortcuts)
addHook('EditorWebView.contextMenuEvent', mouse_context) # Legacy hook but it does fire
#gui_hooks.editor_will_show_context_menu.append(mouse_context) # New style hooks doesn't fire until Image Occlusion Enhanced is fixed

