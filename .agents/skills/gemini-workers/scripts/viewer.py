"""Live, read-only view of every Gemini worker, for the human. The lead never calls it.

    double-click viewer.cmd, or: py -3 viewer.py [--port 7380] [--no-browser] [--db <state.sqlite3>]
    It opens http://localhost:7380 and runs until its console window is closed.

Reads the antigravity broker's SQLite store in read-only mode, so it cannot change,
slow down or be seen by any worker or by the lead. Binds to 127.0.0.1 only. Its one write is
the pin list (~/.gemini-workers/pinned.json): pinned workers are never deleted by prune.py.
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import contextmanager
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from prune import find_db, load_pins, save_pins

DB = find_db()
USAGE = {"groups": None, "error": None, "at": None}


def watch_usage(every=120):
    """Keep the account quota fresh. `agy -p /usage` is a slash command: it reads the quota
    without calling a model or saving a conversation, in about 2 seconds."""
    agy = shutil.which("agy")
    while True:
        try:
            if not agy:
                raise RuntimeError("agy is not on PATH")
            out = subprocess.run([agy, "--output-format", "json", "-p", "/usage"], capture_output=True,
                                 text=True, encoding="utf-8", timeout=90,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            data = json.loads(out.stdout)
            groups = data["command"]["data"]["groups"]
            USAGE.update(groups=groups, error=None, at=time.time())
        except Exception as exc:  # keep the last good reading, report why this one failed
            USAGE.update(error=str(exc) or type(exc).__name__)
        time.sleep(every)
SHOWN = ("turn_started", "steer", "thought", "message", "tool_call", "tool_update", "file_change",
         "request_opened", "request_resolved", "turn_completed", "background_started",
         "background_settled", "process_exited", "system")


@contextmanager
def connect():
    """Read-only connection. Falls back to a query-only one when SQLite cannot open the file
    read-only (it can fail on a WAL database whose -shm file it is not allowed to create)."""
    if not os.path.exists(DB):
        raise sqlite3.OperationalError(f"no broker database at {DB}")
    try:
        c = sqlite3.connect(Path(DB).as_uri() + "?mode=ro", uri=True, timeout=5)
        c.execute("select 1 from tasks limit 1")
    except sqlite3.OperationalError:
        c = sqlite3.connect(DB, timeout=5)
        c.execute("pragma query_only = on")
    try:
        yield c
    finally:
        c.close()


def tasks():
    pins = load_pins()
    with connect() as c:
        rows = c.execute("select id, status, created, data from tasks order by created desc").fetchall()
        out = []
        for tid, status, created, data in rows:
            d = json.loads(data)
            last = c.execute("select max(seq), max(ts) from events where task=?", (tid,)).fetchone()
            usage = c.execute("select data from events where task=? and kind='turn_completed' "
                              "order by seq desc limit 1", (tid,)).fetchone()
            u = json.loads(usage[0]) if usage else {}
            out.append({
                "id": tid, "status": status, "created": created, "name": d.get("name") or tid[:8],
                "workdir": d.get("workdir") or d.get("cwd"), "model": d.get("model"),
                "turn": d.get("turn_id"), "turn_status": d.get("turn_status"), "activity": d.get("activity"),
                "last_seq": last[0] or 0, "last_ts": last[1], "context": u.get("context"),
                "tokens": (u.get("usage") or {}).get("totalTokens"), "pinned": tid in pins,
            })
        return out


def events(task, after):
    marks = ",".join("?" * len(SHOWN))
    with connect() as c:
        rows = c.execute(f"select seq, turn, ts, kind, origin, data from events where task=? and seq>? "
                         f"and kind in ({marks}) order by seq limit 2000", (task, after, *SHOWN)).fetchall()
        out = []
        for s, t, ts, k, o, d in rows:
            data = json.loads(d)
            if k == "request_opened":  # say what is being asked, from the request record
                req = c.execute("select data from requests where id=?", (data.get("request_id"),)).fetchone()
                if req:
                    r = json.loads(req[0])
                    data["what"] = r.get("command") or r.get("title") or r.get("tool_name")
            out.append({"seq": s, "turn": t, "ts": ts, "kind": k, "origin": o, "data": data})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, body, ctype):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/":
                self.send(200, PAGE, "text/html; charset=utf-8")
            elif url.path == "/api/usage":
                self.send(200, json.dumps(USAGE), "application/json")
            elif url.path == "/api/tasks":
                self.send(200, json.dumps(tasks()), "application/json")
            elif url.path == "/api/events":
                self.send(200, json.dumps(events(q["task"][0], int(q.get("after", ["0"])[0]))), "application/json")
            else:
                self.send(404, "not found", "text/plain")
        except (sqlite3.Error, KeyError, ValueError) as exc:
            sys.stderr.write(f"{url.path}: {exc} (database: {DB})\n")
            self.send(503, json.dumps({"error": f"{exc} (database: {DB})"}), "application/json")

    def do_POST(self):
        # The only write: the pin list, never the broker's database. Same-origin JSON only,
        # so another web page cannot pin or unpin through the browser.
        origin = self.headers.get("Origin", "")
        if urlparse(self.path).path != "/api/pin" or not origin.startswith(("http://localhost:", "http://127.0.0.1:")) \
                or self.headers.get("Content-Type") != "application/json":
            self.send(403, "forbidden", "text/plain")
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            pins = load_pins()
            (pins.add if body["pinned"] else pins.discard)(str(body["task"]))
            save_pins(pins)
            self.send(200, json.dumps({"pinned": bool(body["pinned"])}), "application/json")
        except (KeyError, ValueError, OSError) as exc:
            self.send(400, json.dumps({"error": str(exc)}), "application/json")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gemini workers</title>
<style>
:root{--bg:#f7f7f5;--panel:#fff;--ink:#1d1d1b;--dim:#76766f;--line:#e4e4df;--accent:#2f6fde;--ok:#1f8a4c;--warn:#b7791f;--bad:#c53030;--code:#f1f1ee}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--panel:#1c1c1a;--ink:#ecece8;--dim:#93938b;--line:#2c2c29;--accent:#6ea0ff;--ok:#4cc27e;--warn:#e0a84a;--bad:#f07070;--code:#24241f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;height:100vh;display:flex}
#pick{display:flex;align-items:center;gap:6px;font:inherit;font-weight:600;font-size:15px;color:var(--ink);background:transparent;border:1px solid var(--line);border-radius:8px;padding:4px 10px;cursor:pointer;max-width:min(60vw,420px)}
#pick:hover{background:var(--bg)}#pick .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#pick .caret{color:var(--dim);font-size:11px}
#menu{position:fixed;inset:auto;top:52px;left:12px;margin:0;padding:6px;width:min(380px,calc(100vw - 24px));max-height:70vh;overflow:auto;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 28px rgb(0 0 0/.18)}
.task{padding:7px 10px;border-radius:7px;cursor:pointer}.task:hover{background:var(--bg)}
.fin{margin-top:4px;border-top:1px solid var(--line);padding-top:4px}.fin>summary{cursor:pointer;padding:6px 10px;font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.04em}
.none{padding:6px 10px}.pin{font-size:11px;margin-right:4px}
.task.sel{background:color-mix(in srgb,var(--accent) 12%,transparent)}.task b{display:block;font-weight:600;word-break:break-all}
.meta{color:var(--dim);font-size:12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--dim)}
.dot.live{background:var(--ok);box-shadow:0 0 0 3px color-mix(in srgb,var(--ok) 25%,transparent)}.dot.wait{background:var(--warn)}.dot.fail{background:var(--bad)}
main{flex:1;display:flex;flex-direction:column;min-width:0}
header{padding:8px 12px;border-bottom:1px solid var(--line);background:var(--panel);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header .meta{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
label{color:var(--dim);font-size:12px;user-select:none}
#feed{flex:1;overflow:auto;padding:12px 20px 100px}
#chin{flex:none;display:flex;align-items:center;padding:6px 14px;border-top:1px solid var(--line);background:var(--panel);font-size:12px;color:var(--dim)}
#usage{display:flex;gap:24px;cursor:default}#usage>span{display:flex;gap:10px}
.ev{margin:6px 0;padding:8px 12px;border-radius:8px;background:var(--panel);border:1px solid var(--line);white-space:pre-wrap;word-break:break-word}
.ev .k{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--dim);margin-right:8px}
.ev.thought{background:transparent;border:none;padding:6px 2px;font-size:14.5px}
.acts{margin:4px 0 8px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}
.acts>summary{cursor:pointer;padding:6px 12px;font-size:12.5px;color:var(--dim);list-style-position:inside;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.acts>summary .n{font-weight:600;color:var(--ink);margin-right:6px}
.acts>summary code{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:var(--code);padding:1px 6px;border-radius:5px;margin-right:4px}
.acts>summary code.failed{color:var(--bad)}.acts>summary code.req{color:var(--warn)}
.acts>.body{padding:0 8px 6px}.acts .ev{margin:4px 0}
.ev.message{border-left:3px solid var(--accent)}
.ev.prompt{border-left:3px solid var(--warn);background:color-mix(in srgb,var(--warn) 8%,var(--panel))}
.ev.cmd code{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
.ev details{margin-top:6px}.ev pre{margin:6px 0 0;padding:8px;background:var(--code);border-radius:6px;overflow:auto;max-height:320px;font:12px/1.45 ui-monospace,Consolas,monospace}
.st{font-size:11px;padding:1px 6px;border-radius:9px;margin-left:6px;border:1px solid var(--line)}
.st.completed{color:var(--ok)}.st.failed{color:var(--bad)}.st.in_progress{color:var(--warn)}
.ev.file{padding:4px 12px;font-size:12.5px}.ev.req{font-size:12.5px}.ev.sys{font-size:12px;color:var(--dim);background:transparent;border:none;padding:2px 12px}
.time{float:right;color:var(--dim);font-size:11px;margin-left:8px}
.empty{color:var(--dim);padding:40px;text-align:center}
@media (max-width:720px){header .meta{flex-basis:100%;order:3}}
</style></head><body>
<div id="menu" popover><div id="tasks"></div></div>
<main><header><button id="pick" popovertarget="menu" title="Switch worker"><span id="pdot" class="dot"></span><span class="name" id="title">Gemini workers</span><span class="caret">▾</span></button><span class="meta" id="sub"></span>
<label title="Show the worker's thinking. Untick to see only its messages and actions."><input type="checkbox" id="thoughts" checked> thoughts</label>
<label title="Scroll to new activity as it arrives. Scrolling up pauses it until you are back at the bottom."><input type="checkbox" id="follow" checked> follow</label>
<label title="Keep this worker and its transcript. Unpinned workers are deleted 7 days after their last message."><input type="checkbox" id="keep"> do not delete after 7 days</label></header>
<div id="feed"><div class="empty">Live view of the antigravity broker. Read-only.</div></div>
<footer id="chin"><span>Reading quota…</span></footer></main>
<script>
const $=s=>document.querySelector(s);let sel=null,after=0,tools={},list=[],lastMsg=null,lastThought=null;
const live=t=>t.status!=='closed'&&(t.turn_status==='in_progress'||t.turn_status==='running'||t.activity==='background'||t.status==='working'||t.status==='running');
const ago=ts=>{if(!ts)return'';const s=Math.round(Date.now()/1000-ts);return s<60?s+'s ago':s<3600?Math.round(s/60)+'m ago':s<86400?Math.round(s/3600)+'h ago':Math.round(s/86400)+'d ago'};
const hhmm=ts=>new Date(ts*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e}
function dot(t){const d=el('span','dot');if(live(t))d.classList.add('live');else if(t.status==='waiting'||t.status==='needs_resume')d.classList.add('wait');else if(/fail|error/.test(t.turn_status||''))d.classList.add('fail');return d}
const finished=t=>['closed','archived','interrupted'].includes(t.status);let finOpen=false,keepBusy=false;
async function loadTasks(){let got;try{got=await (await fetch('/api/tasks')).json()}catch(e){$('#sub').textContent='viewer not reachable';return}
 if(!Array.isArray(got)){$('#sub').textContent='cannot read workers: '+(got.error||'unknown error');return}list=got;
 if(!list.length){$('#title').textContent='No workers yet'}
 const box=$('#tasks');box.textContent='';list.sort((a,b)=>(live(b)-live(a))||((b.last_ts||0)-(a.last_ts||0)));
 if(!sel&&list.length)pick(list[0].id);
 const done=list.filter(finished);let fin=null;
 if(done.length){fin=el('details','fin');fin.open=finOpen;fin.ontoggle=()=>{finOpen=fin.open};fin.append(el('summary',null,`Finished (${done.length})`))}
 for(const t of list){const d=el('div','task'+(t.id===sel?' sel':''));d.onclick=()=>{$('#menu').hidePopover();if(t.id!==sel)pick(t.id)};const b=el('b');b.append(dot(t));if(t.pinned)b.append(el('span','pin','📌'));b.append(t.name);d.append(b);
  const where=(t.workdir||'').split(/[\\/]/).filter(Boolean).pop()||'';
  d.append(el('div','meta',`${t.status}${t.activity==='background'?' · background':''} · ${t.turn||''} ${t.turn_status||''} · ${ago(t.last_ts)}`));
  d.append(el('div','meta',[where,t.model,t.context?Math.round(100*t.context.used/t.context.size)+'% context':''].filter(Boolean).join(' · ')));(finished(t)?fin:box).append(d)}
 if(fin){if(done.length===list.length)box.append(el('div','meta none','No active workers'));box.append(fin)}
 const t=list.find(x=>x.id===sel);if(t){$('#title').textContent=t.name;if(!keepBusy)$('#keep').checked=!!t.pinned;$('#pdot').replaceWith(Object.assign(dot(t),{id:'pdot'}));const c=t.context?` · context ${Math.round(100*t.context.used/t.context.size)}%`:'';
  $('#sub').textContent=`${t.status}${t.activity==='background'?' (background)':''} · ${t.workdir||''}${t.tokens?' · '+(t.tokens/1e6).toFixed(1)+'M tokens':''}${c}`}}
function pick(id){sel=id;after=0;tools={};lastMsg=lastThought=group=null;$('#feed').textContent='';loadTasks();poll()}
function card(cls,kind,text,ts){const e=el('div','ev '+cls);if(ts)e.append(el('span','time',hhmm(ts)));e.append(el('span','k',kind));if(text!=null)e.append(document.createTextNode(text));return e}
function add(e){$('#feed').append(e)}
// Follow: after each poll, jump to the end unless the user has scrolled up since the last
// jump (the view sits above where it was left). Scrolling back near the end resumes it.
// Content that grows in place (streamed text, output) leaves the position alone, so it is followed too.
let leftAt=0;
function atBottom(){const f=$('#feed');return f.scrollHeight-f.scrollTop-f.clientHeight<120}
function follow(force){const f=$('#feed');if(!$('#follow').checked)return;
 if(!force&&f.scrollTop<leftAt-10&&!atBottom())return;f.scrollTop=f.scrollHeight;leftAt=f.scrollTop}
// Tool calls, edits and requests between two pieces of text share one collapsible group.
// Only the current group (nothing written after it yet) stays open.
let group=null;
const short=s=>{s=(s||'').replace(/^\/([A-Za-z]:)/,'$1').replace(/\s+/g,' ').trim();return s.length>70?s.slice(0,67)+'…':s};
function closeGroup(){if(group){group.open=false;group=null}}
function inGroup(e,label,cls){if(!group){group=el('details','acts');group.open=true;group._n=0;
  const s=el('summary');group._count=el('span','n');s.append(group._count);group._chips=el('span');s.append(group._chips);group.append(s);
  group._body=el('div','body');group.append(group._body);add(group)}
 group._n++;group._count.textContent=group._n+(group._n>1?' actions':' action');
 const chip=el('code',cls||null,short(label));group._chips.append(chip);
 group._body.append(e);
 return chip}
function grow(c,text){c._raw=(c._raw||'')+(text||'');c.lastChild.textContent=c._raw.trim()}
function render(ev){const d=ev.data,k=ev.kind;
 if(k!=='message')lastMsg=null;if(k!=='thought')lastThought=null;
 if(k==='turn_started'||k==='steer'){closeGroup();add(card('prompt',k==='steer'?'lead steers':'lead · '+ev.turn,d.prompt_preview||'',ev.ts));return}
 if(k==='thought'){closeGroup();if(lastThought){grow(lastThought,d.text);return}const c=card('thought','thinking','',ev.ts);grow(c,d.text);c.hidden=!$('#thoughts').checked;lastThought=c;add(c);return}
 if(k==='message'){closeGroup();if(lastMsg){grow(lastMsg,d.text);return}lastMsg=card('message','worker','',ev.ts);grow(lastMsg,d.text);add(lastMsg);return}
 if(k==='tool_call'||k==='tool_update'){let t=tools[d.tool_call_id];
  if(!t){const label=d.command||d.title||d.name;t=card('cmd',d.kind==='execute'?'run':d.kind||d.name,null,ev.ts);t.append(el('code',null,label));t._st=el('span','st');t.append(t._st);tools[d.tool_call_id]=t;t._chip=inGroup(t,label)}
  if(d.status){t._st.textContent=d.status.replace('_',' ');t._st.className='st '+d.status;if(d.status==='failed')t._chip.classList.add('failed')}
  if(d.output_preview&&!t._out){const det=el('details');det.append(el('summary','meta','output'));t._out=el('pre',null,d.output_preview);det.append(t._out);t.append(det)}
  else if(d.output_preview)t._out.textContent=d.output_preview;return}
 if(k==='file_change'){const p=(d.path||'').replace(/^\/([A-Za-z]:)/,'$1');inGroup(card('file','changed',p,ev.ts),'changed '+p.split(/[\\/]/).pop());return}
 if(k==='request_opened'){inGroup(card('req','asks '+(d.kind||'request'),d.what||'',ev.ts),'asks: '+(d.what||d.kind||'request'),'req');return}
 if(k==='request_resolved'){const o=(d.decision&&(d.decision.option_id||(d.decision.outcome||{}).optionId))||d.status;inGroup(card('req','answered',`${o} by ${(d.decision||{}).by||'?'}`,ev.ts),`${o} by ${(d.decision||{}).by||'?'}`,'req');return}
 if(k==='turn_completed'){closeGroup();const u=d.usage||{};add(card('sys','turn',`${d.status||''} · ${d.stop_reason||''}${u.totalTokens?' · '+(u.totalTokens/1e6).toFixed(2)+'M tokens':''}`,ev.ts));return}
 add(card('sys',k.replace('_',' '),d.reason||d.action||'',ev.ts))}
async function poll(){if(!sel)return;const id=sel;try{const evs=await (await fetch(`/api/events?task=${id}&after=${after}`)).json();
 if(id!==sel)return;const first=after===0;for(const ev of evs){render(ev);after=ev.seq}
 if(evs.length)follow(first)}catch(e){}}
$('#follow').addEventListener('change',e=>{if(e.target.checked)follow(true)});
$('#thoughts').onchange=e=>document.querySelectorAll('.ev.thought').forEach(t=>t.hidden=!e.target.checked);
$('#keep').onchange=async e=>{if(!sel)return;keepBusy=true;const want=e.target.checked;
 try{const r=await fetch('/api/pin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:sel,pinned:want})});if(!r.ok)throw 0}
 catch(_){e.target.checked=!want;$('#sub').textContent='could not save the pin'}
 keepBusy=false;loadTasks()};
// Usage of the Gemini models, the ones the workers run on. The 5-hour window is the session.
// Each reads: label, percentage used, reset time ("00:00", or "Fri. 06:00" when not today), time left.
const two=n=>String(n).padStart(2,'0');
function resets(iso){const t=new Date(iso),now=new Date(),s=Math.max(0,(t-now)/1000);
 const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
 const clock=two(t.getHours())+':'+two(t.getMinutes());
 const at=t.toDateString()===now.toDateString()?clock:t.toLocaleDateString('en-US',{weekday:'short'})+'. '+clock;
 return `${at} (${d?`${d}d ${h}h`:h?`${h}h${two(m)}`:`${m}m`})`}
function quota(label,b){const q=el('span');q.append(el('span',null,label),el('b',null,Math.round(100*(1-(b.remaining_fraction??1)))+'%'));
 if(b.reset_time)q.append(el('span',null,resets(b.reset_time)));return q}
async function loadUsage(){let u;try{u=await (await fetch('/api/usage')).json()}catch(e){return}const box=el('span');box.id='usage';
 const g=(u.groups||[]).find(x=>/^gemini models$/i.test(x.name))||(u.groups||[]).find(x=>/gemini/i.test(x.name));
 if(!g){box.textContent=u.error?'Usage unavailable':'Reading usage…';$('#chin').replaceChildren(box);return}
 const by=w=>(g.buckets||[]).find(b=>b.window===w);
 if(by('5h'))box.append(quota('Session',by('5h')));if(by('weekly'))box.append(quota('Week',by('weekly')));
 if(u.at)box.title='Updated '+ago(u.at);$('#chin').replaceChildren(box)}
loadTasks();loadUsage();setInterval(poll,1500);setInterval(loadTasks,4000);setInterval(loadUsage,30000);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7380)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--db", help="the broker's state.sqlite3, when the automatic search picks the wrong one")
    a = ap.parse_args()
    if a.db:
        global DB
        DB = os.path.abspath(a.db)
    url = f"http://localhost:{a.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError:
        from urllib.request import urlopen
        try:
            urlopen(f"http://127.0.0.1:{a.port}/api/tasks", timeout=2).read()
        except Exception:
            sys.stderr.write(f"port {a.port} is taken by another program; pass --port\n")
            return 1
        print(f"The viewer is already running at {url}")
        if not a.no_browser:
            webbrowser.open(url)
        return 0
    print(f"Gemini workers viewer at {url} (read-only). Close this window or press Ctrl+C to stop.")
    print(f"database: {DB}" + ("" if os.path.exists(DB) else "  (missing: start a worker first)"))
    threading.Thread(target=watch_usage, daemon=True).start()
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
