#!/usr/bin/env python3
# 开发用预览服务器：手机尺寸窗口 + 改文件自动刷新（仅本机使用）
import http.server
import os
import socketserver
import sys
import time

PORT = 8090
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")

RELOAD_SNIPPET = b"""
<script>
(function () {
  var last = 0;
  function poll() {
    fetch('/__mtime', { cache: 'no-store' })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (!last) { last = t; return; }
        if (t !== last) location.reload();
      })
      .catch(function () {});
  }
  setInterval(poll, 700);
})();
</script>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path.split('?')[0] == '/__mtime':
            body = str(os.path.getmtime(INDEX)).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        if os.path.isfile(path) and path.lower().endswith('.html'):
            with open(path, 'rb') as f:
                data = f.read()
            if b'</body>' in data:
                data = data.replace(b'</body>', RELOAD_SNIPPET + b'</body>', 1)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_header('Cache-Control', 'no-store')
        super().do_GET()

    def end_headers(self):
        if not self.path.startswith('/__mtime'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    os.chdir(ROOT)
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print('preview server: http://127.0.0.1:%d/index.html' % PORT)
        print('serving: %s' % ROOT)
        httpd.serve_forever()
