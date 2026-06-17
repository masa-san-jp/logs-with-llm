# ASUS GX10へのCodex App導入可否検証

## 結論

ASUS Ascent GX10にCodex CLIを入れることは高確度で可能。GX10はUbuntu LinuxかつARM v9.2-A CPU構成で、Codex CLIはLinux arm64向けバイナリが公開されているため。

一方、Codex App（GUIデスクトップアプリ）をGX10単体のLinuxホストとして使い、ChatGPTモバイルから直接操作する構成は、公式対応ではない。OpenAI公式のCodex AppはmacOS/Windows対応で、Linuxは通知待ち扱い。Zenn記事の方法は、非公式Linuxビルド/移植を利用する実験構成と見るべき。

したがって判定は以下。

| 対象 | 判定 | 備考 |
|---|---:|---|
| Codex CLI on GX10 | ◎ | Linux ARM64対応。まずここから入れるべき |
| Codex App公式版 on GX10 | × | 公式AppはmacOS/Windowsのみ |
| 非公式Codex Desktop Linux on GX10 | △ | Ubuntuなので導入余地あり。ただしARM64/Electron/ネイティブモジュール/remote mobile controlがリスク |
| スマホからGX10を使う実用構成 | ○ | 公式にはMac/Windows上のCodex AppからGX10へSSH接続する構成が堅い |

## GX10側の前提

ASUS Ascent GX10の公式仕様はUbuntu Linux、ARM v9.2-A CPU、NVIDIA Blackwell GPU、128GB LPDDR5x unified memory。性能面は十分で、制約は主にOS/CPUアーキテクチャと公式サポート範囲。

## Codex CLI導入手順

```bash
uname -m
lsb_release -a || cat /etc/os-release

curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
codex
```

`uname -m` が `aarch64` なら想定通り。初回起動時にChatGPTアカウントまたはAPI keyで認証する。

## Codex App導入方針

### 推奨: 公式サポート寄り構成

1. MacまたはWindowsにCodex Appを入れる。
2. GX10にCodex CLIを入れて認証する。
3. Mac/Windows側Codex AppからGX10をSSH hostとして追加する。
4. スマホはMac/Windows側Codex Appホストへ接続する。

この構成ならGX10上のファイルシステムとshellをCodexが使えるが、モバイル接続ホストは公式対応OS側に置ける。

### 実験: GX10単体をCodex Appホストにする

Zenn記事の流れに沿う場合の基本形。

```bash
sudo apt update
sudo apt install -y git curl build-essential

git clone -b feat/install-latest-installer --single-branch https://github.com/robustonian/codex-desktop-linux.git
cd codex-desktop-linux
bash scripts/install-latest.sh

mkdir -p ~/.codex
cat >> ~/.codex/config.toml <<'EOF_CONFIG'
[features]
remote_connections = true
remote_control = true
EOF_CONFIG

codex-desktop
```

ただし、robustonian/codex-desktop-linux側のREADMEでは、Phone/Android host accessは上流ではmacOS-onlyで、Linuxでは `linux-features/remote-mobile-control` による実験的パッチ扱い。`Set up Codex mobile` が表示されない場合は、以下のようにremote-mobile-controlを有効にして再ビルドする方針が必要。

```bash
cd codex-desktop-linux
CODEX_LINUX_FEATURES=remote-mobile-control \
CODEX_BOOTSTRAP_INSTALL_DEPS=1 \
CODEX_BOOTSTRAP_INSTALL_NATIVE=1 \
make setup-native
```

## リスク

- OpenAI公式AppではLinuxホストが対象外。
- 非公式移植はmacOS版DMGをLinux Electron Appへ変換する構成で、アップストリーム変更に弱い。
- GX10はARM64なので、x64前提のバイナリ、Electron native module、AppImage/パッケージ生成の一部で失敗する可能性がある。
- モバイルremote controlは非公式側でも実験扱い。
- 外部から使う場合、app-serverを直接インターネット公開しない。VPN/Tailscale等のmesh/VPN越しにする。

## 最短の検証順

1. GX10でCodex CLI導入: `codex --version` と簡単なローカルrepo操作まで確認。
2. Mac/Windows Codex AppからGX10へSSH接続: 公式寄りルートで実用性確認。
3. どうしてもGX10単体ホスト化したい場合だけ、非公式Linux Desktopを入れる。
4. `remote-mobile-control` featureを有効化し、ChatGPT mobileにGX10 hostが表示されるか確認。

## 判定

GX10に「Codexを入れて開発用に使う」なら可。

GX10に「Codex App公式版を入れる」なら不可。

GX10に「非公式Codex Desktop Linuxを入れて、スマホから直接操作する」なら実験導入は可能性あり。ただし実運用の第一候補にはしない。まずはCodex CLI + SSH remote host構成で始めるのが堅い。

## 参照元

- ASUS Ascent GX10 公式仕様
- OpenAI Codex CLI 公式ドキュメント
- OpenAI Codex App 公式ドキュメント
- OpenAI Codex Remote connections 公式ドキュメント
- openai/codex GitHub README
- robustonian Zenn記事「CodexモバイルからUbuntuのCodex Appを操作する」
- robustonian/codex-desktop-linux README
