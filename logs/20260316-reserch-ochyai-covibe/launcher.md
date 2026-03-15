#!/usr/bin/env python3
“””
co-vibe launcher — ユースケース選択TUI
co-vibe リポジトリのルートに置いて実行: python3 covibe-launcher.py
“””

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ──────────────────────────────────────────────

# ANSI カラー定義

# ──────────────────────────────────────────────

R  = “\033[0m”
B  = “\033[1m”
DIM= “\033[2m”
CY = “\033[96m”
GR = “\033[92m”
YL = “\033[93m”
RD = “\033[91m”
MG = “\033[95m”
BL = “\033[94m”
WH = “\033[97m”
BG_DK = “\033[48;5;234m”

def clr(code, text): return f”{code}{text}{R}”
def supports_color():
return hasattr(sys.stdout, “isatty”) and sys.stdout.isatty()

NO_COLOR = not supports_color()
def c(code, text): return text if NO_COLOR else clr(code, text)

# ──────────────────────────────────────────────

# ユースケース定義

# ──────────────────────────────────────────────

USECASES = [
{
“id”: “UC-1”,
“label”: “ペアプログラミング”,
“desc”: “自然言語でコーディング・ファイル操作を対話的に実施”,
“icon”: “⌨”,
“strategy”: “auto”,
“extra_args”: [],
“recommend”: “Anthropic APIキー推奨”,
“tip”: “実行前に確認が入るので安全に使えます。”,
“warn”: None,
},
{
“id”: “UC-2”,
“label”: “Deep Webリサーチ”,
“desc”: “テーマを分解→並列Web検索→統合レポート生成”,
“icon”: “🔬”,
“strategy”: “strong”,
“extra_args”: [],
“recommend”: “Anthropic + OpenAI APIキー推奨”,
“tip”: “複数ターン消費します。/cost で随時確認を。”,
“warn”: None,
},
{
“id”: “UC-3”,
“label”: “マルチエージェント並列開発”,
“desc”: “大規模タスクをサブエージェントに分散して並列実行”,
“icon”: “🤖”,
“strategy”: “strong”,
“extra_args”: [”-y”],
“recommend”: “Anthropic + Groq APIキー推奨”,
“tip”: None,
“warn”: “⚠ -y（自動許可）モードで起動します。必ずGitブランチを切ってから使用してください。”,
},
{
“id”: “UC-4”,
“label”: “コスト最適化（日常タスク）”,
“desc”: “Groq / Haiku などの軽量モデルでコスト・速度を最適化”,
“icon”: “⚡”,
“strategy”: “cheap”,
“extra_args”: [],
“recommend”: “Groq または Anthropic APIキー”,
“tip”: “単純な質問・短いコード生成に最適です。”,
“warn”: None,
},
{
“id”: “UC-5”,
“label”: “プライベート・オフライン（Ollama）”,
“desc”: “ローカルモデルのみ使用。APIキー不要・完全オフライン”,
“icon”: “🔒”,
“strategy”: “auto”,
“extra_args”: [],
“recommend”: “Ollama インストール + モデルpull済み必須”,
“tip”: “ollama serve が起動済みであること。モデルは qwen2.5-coder:7b 推奨。”,
“warn”: None,
},
{
“id”: “UC-6”,
“label”: “研究・デバッグ・実験”,
“desc”: “全APIコール・推論過程をトレース。エージェント研究向け”,
“icon”: “🧪”,
“strategy”: “auto”,
“extra_args”: [”–debug”],
“recommend”: “全プロバイダ登録推奨”,
“tip”: “ログは /tmp/co-vibe-tui-debug.log にも出力されます。”,
“warn”: None,
},
]

# ──────────────────────────────────────────────

# ユーティリティ

# ──────────────────────────────────────────────

def clear_screen():
os.system(“cls” if os.name == “nt” else “clear”)

def hr(char=“─”, width=60, color=DIM):
return c(color, char * width)

def banner():
lines = [
“”,
c(CY+B, “  ██████╗ ██████╗        ██╗   ██╗██╗██████╗ ███████╗”),
c(CY+B, “ ██╔════╝██╔═══██╗       ██║   ██║██║██╔══██╗██╔════╝”),
c(CY+B, “ ██║     ██║   ██║ █████╗██║   ██║██║██████╔╝█████╗  “),
c(CY+B, “ ██║     ██║   ██║ ╚════╝╚██╗ ██╔╝██║██╔══██╗██╔══╝  “),
c(CY+B, “ ╚██████╗╚██████╔╝        ╚████╔╝ ██║██████╔╝███████╗”),
c(CY+B, “  ╚═════╝ ╚═════╝          ╚═══╝  ╚═╝╚═════╝ ╚══════╝”),
“”,
c(DIM, “  Multi-Provider AI Coding Agent  ─  Launcher v1.0”),
“”,
]
print(”\n”.join(lines))

# ──────────────────────────────────────────────

# .env 読み込み・プロバイダ検出

# ──────────────────────────────────────────────

def load_env(env_path: Path) -> dict:
“”“シンプルな .env パーサー（python-dotenv 不使用）”””
result = {}
if not env_path.exists():
return result
with open(env_path) as f:
for line in f:
line = line.strip()
if not line or line.startswith(”#”) or “=” not in line:
continue
k, _, v = line.partition(”=”)
result[k.strip()] = v.strip().strip(’”’).strip(”’”)
return result

def detect_providers(env: dict) -> list[str]:
available = []
if env.get(“ANTHROPIC_API_KEY”, “”).startswith(“sk-ant”):
available.append(“Anthropic”)
if env.get(“OPENAI_API_KEY”, “”).startswith(“sk-”):
available.append(“OpenAI”)
if env.get(“GROQ_API_KEY”, “”).startswith(“gsk_”):
available.append(“Groq”)
# Ollama: サービスが起動しているか確認
if shutil.which(“ollama”):
try:
r = subprocess.run(
[“ollama”, “list”],
capture_output=True, text=True, timeout=2
)
if r.returncode == 0 and len(r.stdout.strip().splitlines()) > 1:
available.append(“Ollama”)
except Exception:
pass
return available

def provider_status_line(providers: list[str]) -> str:
all_p = [“Anthropic”, “OpenAI”, “Groq”, “Ollama”]
parts = []
for p in all_p:
if p in providers:
parts.append(c(GR, f”✓ {p}”))
else:
parts.append(c(DIM, f”✗ {p}”))
return “  “ + “  “.join(parts)

# ──────────────────────────────────────────────

# UC リスト表示

# ──────────────────────────────────────────────

def print_usecases(selected: int, providers: list[str]):
print(c(WH+B, “  ユースケースを選択してください”))
print(c(DIM, “  ↑↓ or 数字キーで選択  Enter で起動  q で終了\n”))
for i, uc in enumerate(USECASES):
is_sel = (i == selected)
prefix = c(CY+B, “▶ “) if is_sel else “  “
num    = c(YL+B, f”[{i+1}]”) if is_sel else c(DIM, f”[{i+1}]”)
icon   = uc[“icon”]
label  = c(WH+B, uc[“label”]) if is_sel else c(WH, uc[“label”])
ucid   = c(MG, uc[“id”])      if is_sel else c(DIM, uc[“id”])
print(f” {prefix}{num} {icon}  {label}  {ucid}”)
if is_sel:
print(f”      {c(DIM, uc[‘desc’])}”)
print(f”      {c(BL,  ’戦略: ’ + uc[‘strategy’])}  “
f”{c(DIM, ’推奨: ’ + uc[‘recommend’])}”)
if uc[“warn”]:
print(f”      {c(YL, uc[‘warn’])}”)
if uc[“tip”]:
print(f”      {c(DIM, ’ℹ ’ + uc[‘tip’])}”)
print()

# ──────────────────────────────────────────────

# キー入力（Windows / Unix 両対応）

# ──────────────────────────────────────────────

def get_key():
if os.name == “nt”:
import msvcrt
ch = msvcrt.getch()
if ch in (b”\x00”, b”\xe0”):
ch2 = msvcrt.getch()
if ch2 == b”H”: return “UP”
if ch2 == b”P”: return “DOWN”
return None
return ch.decode(“utf-8”, errors=“ignore”)
else:
import tty, termios
fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
try:
tty.setraw(fd)
ch = sys.stdin.read(1)
if ch == “\x1b”:
ch2 = sys.stdin.read(1)
if ch2 == “[”:
ch3 = sys.stdin.read(1)
if ch3 == “A”: return “UP”
if ch3 == “B”: return “DOWN”
return ch
finally:
termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ──────────────────────────────────────────────

# 起動確認・実行

# ──────────────────────────────────────────────

def confirm_and_launch(uc: dict, providers: list[str], covibe_path: Path):
clear_screen()
print()
print(hr())
print(c(WH+B, f”  {uc[‘icon’]}  {uc[‘id’]}: {uc[‘label’]}”))
print(hr())
print()

```
# コマンド組み立て
cmd = [sys.executable, str(covibe_path),
       "--strategy", uc["strategy"]] + uc["extra_args"]

print(c(DIM,  "  実行コマンド:"))
print(c(GR+B, "  " + " ".join(cmd)))
print()

# プロバイダ確認
print(c(DIM, "  検出済みプロバイダ:"))
print(provider_status_line(providers))
print()

# 警告
if uc["warn"]:
    print(c(YL, f"  {uc['warn']}"))
    print()

# 追加フラグの説明
if uc["extra_args"]:
    flag_notes = {
        "-y":      "-y : ツール実行を自動許可（確認なし）",
        "--debug": "--debug : 全APIコール・推論をトレース出力",
    }
    for f in uc["extra_args"]:
        note = flag_notes.get(f, f)
        print(c(BL, f"  ▸ {note}"))
    print()

# オプション追加入力
extra_prompt = input(
    c(DIM, "  追加オプション（不要なら Enter）: ")
).strip()
extra_extra = extra_prompt.split() if extra_prompt else []

final_cmd = cmd + extra_extra
print()
print(c(DIM, "  起動します: ") + c(GR, " ".join(final_cmd)))
print()

yn = input(c(WH, "  実行しますか？ [Y/n]: ")).strip().lower()
if yn in ("", "y", "yes"):
    print()
    print(c(CY, "  ▶ co-vibe を起動中..."))
    print(hr())
    print()
    try:
        subprocess.run(final_cmd)
    except KeyboardInterrupt:
        print()
        print(c(DIM, "  中断しました。"))
else:
    print(c(DIM, "  キャンセルしました。"))

print()
input(c(DIM, "  Enterキーでメニューに戻る..."))
```

# ──────────────────────────────────────────────

# メインループ

# ──────────────────────────────────────────────

def main():
# co-vibe.py の場所を特定
script_dir  = Path(**file**).parent.resolve()
covibe_path = script_dir / “co-vibe.py”

```
if not covibe_path.exists():
    print(c(RD, f"Error: co-vibe.py が見つかりません: {covibe_path}"))
    print(c(DIM, "このスクリプトは co-vibe リポジトリのルートに置いてください。"))
    sys.exit(1)

# .env 読み込み
env_path = script_dir / ".env"
env      = load_env(env_path)
providers = detect_providers(env)

selected = 0

while True:
    clear_screen()
    banner()

    # プロバイダ状態
    print(c(DIM, "  利用可能なプロバイダ:"))
    print(provider_status_line(providers))
    if not providers:
        print(c(YL, "\n  ⚠ プロバイダが検出されませんでした。.env を確認してください。"))
    print()
    print(hr())
    print()

    print_usecases(selected, providers)
    print(hr())
    print(c(DIM, "  [r] プロバイダ再検出  [q] 終了"))
    print()

    key = get_key()

    if key in ("UP", "k"):
        selected = (selected - 1) % len(USECASES)
    elif key in ("DOWN", "j"):
        selected = (selected + 1) % len(USECASES)
    elif key in ("1","2","3","4","5","6"):
        selected = int(key) - 1
    elif key in ("\r", "\n", " "):
        confirm_and_launch(USECASES[selected], providers, covibe_path)
        # プロバイダを再検出（セッション後に変わる可能性）
        env       = load_env(env_path)
        providers = detect_providers(env)
    elif key in ("r", "R"):
        env       = load_env(env_path)
        providers = detect_providers(env)
    elif key in ("q", "Q", "\x03", "\x04"):
        clear_screen()
        print(c(DIM, "\n  co-vibe launcher を終了しました。\n"))
        sys.exit(0)
```

if **name** == “**main**”:
main()