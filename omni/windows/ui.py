import json
import threading
import markdown
import webview
from omni.config import Config
from omni.ui.markdown_parser import preprocess_markdown

INDICATOR_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  body {
    background: transparent;
    overflow: hidden;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
  }
  .pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(28, 33, 46, 0.95);
    border: 1.5px solid rgba(75, 140, 255, 0.4);
    border-radius: 19px;
    padding: 6px 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(16px);
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #4B8CFF;
    box-shadow: 0 0 10px #4B8CFF;
    animation: pulse 1.2s infinite ease-in-out;
  }
  .spinner {
    width: 12px;
    height: 12px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-top-color: #4B8CFF;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: none;
  }
  .text {
    font-size: 13px;
    font-weight: 500;
    color: #E2E8F0;
    letter-spacing: 0.2px;
  }
  @keyframes pulse {
    0%, 100% { transform: scale(0.9); opacity: 0.8; }
    50% { transform: scale(1.2); opacity: 1; }
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
</head>
<body>
  <div class="pill">
    <div id="dot" class="dot"></div>
    <div id="spinner" class="spinner"></div>
    <span id="label" class="text">Listening...</span>
  </div>
  <script>
    function setState(state) {
      const dot = document.getElementById('dot');
      const spinner = document.getElementById('spinner');
      const label = document.getElementById('label');
      if (state === 'listening') {
        dot.style.display = 'block';
        spinner.style.display = 'none';
        label.innerText = 'Listening...';
      } else if (state === 'thinking') {
        dot.style.display = 'none';
        spinner.style.display = 'block';
        label.innerText = 'Thinking...';
      }
    }
  </script>
</body>
</html>
"""

HUD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: transparent;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #F3F4F6;
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  .container {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: rgba(18, 22, 31, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(24px);
    overflow: hidden;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.02);
  }
  .title {
    font-size: 13px;
    font-weight: 600;
    color: #94A3B8;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .badge {
    background: #3B82F6;
    color: white;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 700;
  }
  .actions {
    display: flex;
    gap: 8px;
  }
  button {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #E2E8F0;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
  }
  button:hover {
    background: rgba(255, 255, 255, 0.12);
  }
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    font-size: 14.5px;
    line-height: 1.6;
  }
  .content h1, .content h2, .content h3 {
    color: #FFFFFF;
    margin: 12px 0 6px 0;
  }
  .content p {
    margin-bottom: 10px;
  }
  .content code {
    font-family: Consolas, "Courier New", monospace;
    background: rgba(255, 255, 255, 0.1);
    color: #FBBF24;
    padding: 2px 5px;
    border-radius: 4px;
    font-size: 13px;
  }
  .content pre {
    background: #0F1219;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 10px 0;
    overflow-x: auto;
  }
  .content pre code {
    background: transparent;
    padding: 0;
    color: #34D399;
  }
  .content ul, .content ol {
    margin-left: 20px;
    margin-bottom: 10px;
  }
  .footer {
    display: flex;
    justify-content: space-between;
    padding: 8px 16px;
    font-size: 11px;
    color: #64748B;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(0, 0, 0, 0.15);
  }
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">
        <span class="badge">OMNI</span>
        <span id="statusText">Ready</span>
      </div>
      <div class="actions">
        <button onclick="copyContent()">Copy (Ctrl+C)</button>
        <button onclick="closeHud()">Close (Esc)</button>
      </div>
    </div>
    <div id="content" class="content"></div>
    <div class="footer">
      <span>Omni Ambient Desktop AI</span>
      <span>Press <b>Esc</b> to dismiss</span>
    </div>
  </div>

  <script>
    let rawText = "";

    function setHtml(htmlText, raw) {
      rawText = raw || "";
      const el = document.getElementById('content');
      el.innerHTML = htmlText;
      el.scrollTop = el.scrollHeight;
    }

    function setStatus(text) {
      document.getElementById('statusText').innerText = text;
    }

    function copyContent() {
      navigator.clipboard.writeText(rawText);
      const btn = document.querySelector('button');
      btn.innerText = "Copied!";
      setTimeout(() => { btn.innerText = "Copy (Ctrl+C)"; }, 1200);
    }

    function closeHud() {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.dismiss();
      }
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeHud();
      } else if (e.ctrlKey && (e.key === 'c' || e.key === 'C')) {
        copyContent();
      }
    });
  </script>
</body>
</html>
"""

class WindowsHUD:
    """Windows Raycast-style floating HUD."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.window = None
        self.raw_text = ""
        self._is_visible = False

    def show(self):
        self._is_visible = True
        if self.window:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass

    def hide(self):
        self._is_visible = False
        if self.window:
            try:
                self.window.hide()
            except Exception:
                pass

    def set_content(self, text: str):
        self.raw_text = text
        processed = preprocess_markdown(text)
        rendered_html = markdown.markdown(processed, extensions=['fenced_code', 'tables', 'nl2br'])
        if self.window:
            try:
                js_code = f"setHtml({json.dumps(rendered_html)}, {json.dumps(text)});"
                self.window.evaluate_js(js_code)
            except Exception:
                pass

    def append_token(self, token: str):
        self.raw_text += token
        self.set_content(self.raw_text)

    def set_status(self, status: str):
        if self.window:
            try:
                self.window.evaluate_js(f"setStatus({json.dumps(status)});")
            except Exception:
                pass

class WindowsIndicator:
    """Windows discreet Siri-style pill indicator."""

    def __init__(self):
        self.window = None

    def start_listening(self):
        if self.window:
            try:
                self.window.show()
                self.window.evaluate_js("setState('listening');")
            except Exception:
                pass

    def start_processing(self):
        if self.window:
            try:
                self.window.show()
                self.window.evaluate_js("setState('thinking');")
            except Exception:
                pass

    def hide(self):
        if self.window:
            try:
                self.window.hide()
            except Exception:
                pass
