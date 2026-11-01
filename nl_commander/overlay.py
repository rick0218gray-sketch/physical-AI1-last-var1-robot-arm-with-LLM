#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""動画用オーバーレイ: commander.py --status-file が書く JSON を、字幕風のページとして配信する。
  python overlay.py --status-file /tmp/status.json --port 8765
  別ターミナルで: python commander.py --status-file /tmp/status.json "右を指してからお辞儀して"
  ブラウザで http://localhost:8765/ を開き、画面録画(Gazebo ウィンドウと並べる/OBS のブラウザソース等)で重ねる。
  背景は透過(?bg=black で黒帯)。標準ライブラリのみ。
"""
import argparse
import http.server
import json
import socketserver
from pathlib import Path

PAGE = """<!doctype html><meta charset="utf-8"><title>commander overlay</title>
<style>
 html,body{margin:0;background:transparent;font-family:'Yu Gothic UI','Noto Sans CJK JP',sans-serif;color:#fff}
 body.black{background:#111}
 #box{position:fixed;left:2%;right:2%;bottom:4%;padding:14px 22px;border-radius:12px;background:rgba(0,0,0,.62);
      text-shadow:0 1px 3px #000;transition:opacity .4s}
 #cmd{font-size:26px;font-weight:700} #step{font-size:22px;margin-top:6px;color:#9fe3ff}
 #msg{font-size:16px;margin-top:6px;color:#ddd} #bar{height:6px;background:#444;border-radius:3px;margin-top:10px}
 #fill{height:6px;background:#4cc3ff;border-radius:3px;width:0;transition:width .3s}
 .reject #step{color:#ff9a9a} .clarify #step{color:#ffd37a} .done #step{color:#9dffb0}
</style>
<div id="box" style="opacity:0"><div id="cmd"></div><div id="step"></div><div id="msg"></div>
<div id="bar"><div id="fill"></div></div></div>
<script>
if(location.search.includes('bg=black'))document.body.className='black';
const L={running:'実行中',done:'完了',error:'エラー',rejected:'拒否',clarify:'確認待ち'};
async function tick(){
 try{const s=await (await fetch('/status.json?'+Date.now())).json();
  const b=document.getElementById('box');b.style.opacity=(s.state==='idle')?0:1;b.className=s.state;
  document.getElementById('cmd').textContent='指令: '+(s.command||'');
  let t=L[s.state]||s.state;
  if(s.state==='running'&&s.skill)t+=` [${s.index}/${s.total}] ${s.skill}  ${s.reason||''}`;
  else if(s.state==='done')t+=` (${s.total} ステップ)`;
  document.getElementById('step').textContent=t;
  document.getElementById('msg').textContent=s.message||'';
  const done=s.state==='done'?1:(s.total?Math.max(0,(s.index-1))/s.total:0);
  document.getElementById('fill').style.width=(done*100)+'%';
 }catch(e){}
 setTimeout(tick,300);}
tick();
</script>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status-file", required=True)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    sf = Path(a.status_file)

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/status.json"):
                try:
                    body = sf.read_bytes()
                except OSError:
                    body = json.dumps({"state": "idle"}).encode()
                ctype = "application/json"
            else:
                body, ctype = PAGE.encode("utf-8"), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((a.host, a.port), H) as srv:
        print(f"overlay: http://{a.host}:{a.port}/  (status file: {sf})")
        srv.serve_forever()


if __name__ == "__main__":
    main()
