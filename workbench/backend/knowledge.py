"""Small JSON-lines bridge; no duplicate rule table or search vocabulary."""
import json
import queue
import shutil
import subprocess
import threading
from pathlib import Path


class KnowledgeError(ValueError):
    pass


class Knowledge:
    def __init__(self, bundle: Path):
        self.bundle = Path(bundle).resolve()
        self.lock = threading.RLock()
        self.process = None
        self.messages = queue.Queue()
        self.bundle_signature = None

    def _start(self):
        node = shutil.which('node')
        if not node:
            raise KnowledgeError('需要 Node.js 22+ 来复用正式检索模块')
        if not (self.bundle / 'site-manifest.json').is_file():
            raise KnowledgeError('请先运行 python -m workbench prepare 构建正式知识包')
        self.messages = queue.Queue()
        self.process = subprocess.Popen(
            [node, str(Path(__file__).with_name('knowledge_bridge.mjs')), str(self.bundle)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', bufsize=1,
        )
        messages, process = self.messages, self.process

        def reader():
            for line in process.stdout:
                messages.put(line)
            messages.put(None)

        threading.Thread(target=reader, daemon=True).start()
        ready = self._read()
        if not ready.get('ready'):
            self.close()
            raise KnowledgeError('知识包初始化失败')

    def _read(self):
        try:
            line = self.messages.get(timeout=30)
        except queue.Empty as exc:
            self.close()
            raise KnowledgeError('知识包读取超时，请核对发布包') from exc
        if line is None:
            error = self.process.stderr.read(2000) if self.process else ''
            self.close()
            raise KnowledgeError('知识包校验或检索失败：' + error[-800:])
        return json.loads(line)

    def call(self, op, **kwargs):
        with self.lock:
            manifest = self.bundle / 'site-manifest.json'
            try:
                stat = manifest.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                signature = None
            if self.process is not None and signature != self.bundle_signature:
                self.close()
            if self.process is None or self.process.poll() is not None:
                self._start()
                self.bundle_signature = signature
            self.process.stdin.write(json.dumps({'op': op, **kwargs}, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            response = self._read()
            if not response.get('ok'):
                raise KnowledgeError(response.get('error', '知识库读取失败'))
            return response['result']

    def close(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                stream.close()
        self.process = None
