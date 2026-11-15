"""Real-model access. ONLY via the Z.ai Coding Plan, ONLY glm-5.3-flash.

OWNER RULES (baked in, do not weaken):
- Base URL: https://api.z.ai/api/coding/paas/v4 (OpenAI-compatible).
- Model: glm-5.3-flash ONLY. Never another model or variant.
- API key: env var COMPACT_BENCH_ZAI_KEY.
- Flat subscription: on a billing/endpoint error, STOP and report. NEVER fall
  back to pay-per-call or another provider.
- Real-model runs are owner-approval-gated (see ROADMAP.md item 1).
"""

import os

DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-5.3-flash"


class CompactBenchError(RuntimeError):
    pass


class BillingOrEndpointError(CompactBenchError):
    """Raised on billing/quota/endpoint failures. STOP — do not fall back."""


class ZaiClient:
    """Minimal OpenAI-compatible chat client over urllib (stdlib, zero-dep)."""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.environ.get("COMPACT_BENCH_ZAI_KEY")
        self.base_url = (
            base_url
            or os.environ.get("COMPACT_BENCH_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        model = model or os.environ.get("COMPACT_BENCH_MODEL") or DEFAULT_MODEL
        if model != DEFAULT_MODEL:
            raise CompactBenchError(
                "model is pinned to %s by repo policy; other variants are not "
                "allowed" % DEFAULT_MODEL
            )
        self.model = model
        if not self.api_key:
            raise CompactBenchError(
                "COMPACT_BENCH_ZAI_KEY is not set. Real-model runs are "
                "owner-approval-gated (ROADMAP.md item 1); offline harness "
                "validation needs no key."
            )

    def chat(self, messages, max_tokens=512, temperature=0):
        import json
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            if exc.code in (401, 402, 403, 429):
                raise BillingOrEndpointError(
                    "Z.ai Coding Plan returned HTTP %d (%s). Per owner rules: "
                    "STOP and report — never fall back to pay-per-call or "
                    "another provider/model." % (exc.code, body)
                )
            raise CompactBenchError("Z.ai endpoint error HTTP %d: %s" % (exc.code, body))
        except urllib.error.URLError as exc:
            raise BillingOrEndpointError(
                "Z.ai endpoint unreachable (%s). Per owner rules: STOP and "
                "report — never fall back." % exc
            )
        return payload["choices"][0]["message"]["content"]


class LLMPolicy:
    """Policy adapter so run_task() can drive a real model.

    Each step sends the current context (task + state/history blocks) and
    expects exactly one action line back.
    """

    INSTRUCTIONS = (
        "You are the agent in a deterministic benchmark. Reply with EXACTLY "
        "one action line and nothing else. Allowed actions are listed in the "
        "task. When the task is complete, reply with 'finish: <answer>'."
    )

    def __init__(self, client: ZaiClient):
        self.client = client

    def __call__(self, context) -> str:
        content = self.INSTRUCTIONS + "\n\nCONTEXT:\n" + "\n\n".join(context)
        return self.client.chat(
            [{"role": "user", "content": content}], max_tokens=200
        ).strip()
