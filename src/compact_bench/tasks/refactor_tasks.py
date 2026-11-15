"""File-refactoring tasks: deterministic in-memory filesystem per run.

Includes one long-input task (~2 KB config files) so threshold-triggered
compaction actually fires mid-run, mirroring the paper's long-input setting.
"""

from .base import Task


class FileEnv:
    """In-memory file store. Deterministic: fixed initial contents."""

    def __init__(self, files):
        self.files = dict(files)

    def execute(self, action: str) -> str:
        if action == "ls":
            return "\n".join(sorted(self.files)) or "(empty)"
        if action.startswith("read "):
            path = action[len("read "):].strip()
            if path in self.files:
                return self.files[path]
            return "FILE NOT FOUND: %s" % path
        if action.startswith("write "):
            rest = action[len("write "):]
            path, _, content = rest.partition("::")
            path = path.strip()
            if not path or not _:
                return "USAGE: write <path> :: <content>"
            self.files[path] = content.lstrip(" ")
            return "WROTE %s (%d chars)" % (path, len(self.files[path]))
        if action.startswith("move "):
            rest = action[len("move "):].split()
            if len(rest) != 2:
                return "USAGE: move <src> <dst>"
            src, dst = rest
            if src not in self.files:
                return "FILE NOT FOUND: %s" % src
            self.files[dst] = self.files.pop(src)
            return "MOVED %s -> %s" % (src, dst)
        if action.startswith("rm "):
            path = action[len("rm "):].strip()
            if path not in self.files:
                return "FILE NOT FOUND: %s" % path
            del self.files[path]
            return "DELETED %s" % path
        return "UNKNOWN ACTION: %s" % action[:40]


_APP_V1 = "from helpers import fmt\n\nprint(fmt(2))\n"
_HELPERS = "def fmt(x):\n    return '%.2f' % x\n"
_UTIL = (
    "def add(a, b):\n    return a + b\n\n\n"
    "def shout(s):\n    return s.upper() + '!'\n"
)
_MATH_OPS = "def add(a, b):\n    return a + b\n"
_TEXT_OPS = "def shout(s):\n    return s.upper() + '!'\n"
_CONFIG_MAIN = "import settings\n\nprint(settings.PAYMENTS_TIMEOUT_MS)\n"


def _long_config(prefix, marker_line):
    lines = ["# %s configuration (generated, deterministic)" % prefix, ""]
    for i in range(1, 61):
        lines.append("%s_SECTION_%02d = %d" % (prefix.upper(), i, i * 3))
        if i == 30:
            lines.append(marker_line)
        if i % 10 == 0:
            lines.append("")
    return "\n".join(lines) + "\n"


ALL_REFACTOR_TASKS = [
    Task(
        name="refactor-rename-module",
        category="refactor",
        prompt=(
            "REPO: app.py, helpers.py.\n"
            "Task: rename the module helpers.py to tools.py and update the\n"
            "import in app.py accordingly. Steps you may take:\n"
            '- "ls" lists files, "read <path>" prints a file,\n'
            '- "move <src> <dst>" renames a file, "write <path> :: <content>"\n'
            "  replaces a file's full content,\n"
            '- "finish: <answer>" submits.'
        ),
        plan=(
            "ls",
            "read app.py",
            "move helpers.py tools.py",
            "write app.py :: from tools import fmt\n\nprint(fmt(2))\n",
            "finish: renamed helpers.py to tools.py",
        ),
        build_env=lambda: FileEnv({"app.py": _APP_V1, "helpers.py": _HELPERS}),
        check=lambda env, answer: (
            ("tools.py" in env.files and "helpers.py" not in env.files
             and "from tools import fmt" in env.files.get("app.py", "")),
            "files=%s" % sorted(env.files),
        ),
    ),
    Task(
        name="refactor-split-file",
        category="refactor",
        prompt=(
            "REPO: util.py (contains two unrelated functions).\n"
            "Task: split util.py into math_ops.py (add) and text_ops.py (shout),\n"
            "then delete util.py. Steps: ls / read / write <path> :: <content> /\n"
            "rm <path> / finish: <answer>."
        ),
        plan=(
            "read util.py",
            "write math_ops.py :: def add(a, b):\n    return a + b\n",
            "write text_ops.py :: def shout(s):\n    return s.upper() + '!'\n",
            "rm util.py",
            "finish: split util.py into math_ops.py and text_ops.py",
        ),
        build_env=lambda: FileEnv({"util.py": _UTIL}),
        check=lambda env, answer: (
            (env.files.get("math_ops.py") == _MATH_OPS
             and env.files.get("text_ops.py") == _TEXT_OPS
             and "util.py" not in env.files),
            "files=%s" % sorted(env.files),
        ),
    ),
    Task(
        name="refactor-delete-dead",
        category="refactor",
        prompt=(
            "REPO: main.py, legacy_v1.py (deprecated, no longer imported).\n"
            "Task: delete legacy_v1.py, keep main.py untouched. Steps: ls /\n"
            "rm <path> / finish: <answer>."
        ),
        plan=(
            "ls",
            "rm legacy_v1.py",
            "finish: removed legacy_v1.py",
        ),
        build_env=lambda: FileEnv(
            {"main.py": _CONFIG_MAIN, "legacy_v1.py": "# deprecated\nprint('v1')\n"}
        ),
        check=lambda env, answer: (
            ("legacy_v1.py" not in env.files
             and env.files.get("main.py") == _CONFIG_MAIN),
            "files=%s" % sorted(env.files),
        ),
    ),
    Task(
        name="refactor-rename-symbol",
        category="refactor",
        prompt=(
            "REPO: settings.py, main.py.\n"
            "Task: rename the symbol DEBUG_MODE to VERBOSE_MODE in BOTH files.\n"
            "Steps: ls / read <path> / write <path> :: <content> / finish: <answer>."
        ),
        plan=(
            "read settings.py",
            "read main.py",
            "write settings.py :: VERBOSE_MODE = True\n",
            "write main.py :: import settings\n\nprint(settings.VERBOSE_MODE)\n",
            "finish: renamed DEBUG_MODE to VERBOSE_MODE",
        ),
        build_env=lambda: FileEnv(
            {
                "settings.py": "DEBUG_MODE = True\n",
                "main.py": "import settings\n\nprint(settings.DEBUG_MODE)\n",
            }
        ),
        check=lambda env, answer: (
            ("DEBUG_MODE" not in "\n".join(env.files.values())
             and "VERBOSE_MODE" in env.files.get("settings.py", "")
             and "VERBOSE_MODE" in env.files.get("main.py", "")),
            "files=%s" % sorted(env.files),
        ),
    ),
    Task(
        name="refactor-long-config-read",
        category="refactor",
        prompt=(
            "LONG INPUT: payments_config.py and shipping_config.py are large\n"
            "generated config files. Task: find the value of PAYMENTS_RETRY_LIMIT\n"
            "in payments_config.py. You do NOT need shipping_config.py. Steps:\n"
            'ls / read <path> / finish: <answer> (just the value).'
        ),
        plan=(
            "read payments_config.py",
            "finish: 7",
        ),
        build_env=lambda: FileEnv(
            {
                "payments_config.py": _long_config(
                    "payments", "PAYMENTS_RETRY_LIMIT = 7"
                ),
                "shipping_config.py": _long_config(
                    "shipping", "SHIPPING_RETRY_LIMIT = 3"
                ),
            }
        ),
        check=lambda env, answer: ((answer or "").strip() == "7", "answer=%r" % answer),
    ),
]
