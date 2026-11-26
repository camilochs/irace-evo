"""A stand-in for the OpenAI and Anthropic APIs, for testing irace-evo offline.

It answers every request with a variant of the function named in the prompt,
so the whole pipeline (prompt, reply, replacement, compilation, racing) runs
without an API key and without cost. Every request body is appended to
REQUESTS_LOG as one JSON line, so a test can check what was sent: the model,
the temperature, top_p, max_tokens, and the prompt itself.

The variant it returns is the function from the prompt with a marker comment,
so it always compiles and each one is distinct.

    python3 fake_llm.py 8765 requests.jsonl order_chromosome
    OPENAI_BASE_URL=http://127.0.0.1:8765/v1 ANTHROPIC_BASE_URL=http://127.0.0.1:8765 ...
"""
import itertools
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
REQUESTS_LOG = sys.argv[2]
counter = itertools.count(1)


FUNCTION = sys.argv[3] if len(sys.argv) > 3 else "order_chromosome"


def function_from(prompt: str) -> str:
    """Return the definition of FUNCTION from the first code block that has it.

    In full-context mode that block is the whole source file, so the
    definition is cut out by matching braces from its signature line."""
    for block in re.findall(r"```[a-zA-Z+]*\n(.*?)```", prompt, re.S):
        lines = block.splitlines()
        for i, line in enumerate(lines):
            if re.search(rf"\b{FUNCTION}\s*\(", line) and not line.rstrip().endswith(";"):
                text = "\n".join(lines[i:])
                depth, opened = 0, False
                for j, ch in enumerate(text):
                    if ch == "{":
                        depth, opened = depth + 1, True
                    elif ch == "}":
                        depth -= 1
                        if opened and depth == 0:
                            return text[: j + 1]
    raise ValueError("no function in the prompt")


def answer(prompt: str) -> str:
    code = function_from(prompt)
    n = next(counter)
    # Put the marker inside the body, after the first brace, so a variant stays
    # a single function definition whatever surrounds it.
    brace = code.index("{")
    code = code[: brace + 1] + f"\n    // fake-llm variant {n}" + code[brace + 1 :]
    return f"```cpp\n{code}\n```"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with open(REQUESTS_LOG, "a") as f:
            f.write(json.dumps({"path": self.path, "body": body}) + "\n")
        # FAKE_REFUSE_SAMPLING=1 behaves like a model that takes no
        # temperature or top_p: the request is refused with a 400.
        if os.environ.get("FAKE_REFUSE_SAMPLING") == "1" and ("temperature" in body or "top_p" in body):
            data = json.dumps({"type": "error", "error": {"type": "invalid_request_error",
                               "message": "temperature and top_p are not supported for this model"}}).encode()
            self.send_response(400)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        prompt = body["messages"][-1]["content"]
        if isinstance(prompt, list):
            prompt = " ".join(p.get("text", "") for p in prompt)
        try:
            text = answer(prompt)
        except ValueError as e:
            text = str(e)
        if self.path.endswith("/chat/completions"):
            reply = {
                "id": "fake", "object": "chat.completion", "created": 0, "model": body["model"],
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": text}}],
                "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": len(text) // 4,
                          "total_tokens": (len(prompt) + len(text)) // 4},
            }
        else:
            reply = {
                "id": "fake", "type": "message", "role": "assistant", "model": body["model"],
                "content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                "usage": {"input_tokens": len(prompt) // 4, "output_tokens": len(text) // 4},
            }
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
