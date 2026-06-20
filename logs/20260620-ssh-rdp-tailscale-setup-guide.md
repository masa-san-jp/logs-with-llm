# 外出先MacBook Pro・職場Windows・自宅GB10をSSHとリモートデスクトップで相互接続する手順書

作成日: 2026-06-20  
対象読者: 初心者  
目的: 3拠点がすべて別ネットワークでも、SSHターミナル接続とリモートデスクトップ接続を安全に使える状態にする。

---

## 0. 結論: 採用する構成

この手順書では、**Tailscale + SSH + RDP / RustDesk** の構成にする。

```text
外出先MacBook Pro ─┐
                    ├─ Tailscaleの仮想プライベートネットワーク ─ 自宅GB10
職場Windows ────────┘

外出先MacBook Pro ─ Tailscale ─ 職場Windows
```

### なぜこの構成にするか

- 自宅ルーターや職場ルーターの**ポート開放をしない**。
- IPアドレスが変わっても接続できる。
- 外出先・職場・自宅が別ネットワークでも接続できる。
- SSHとリモートデスクトップを同じ考え方で扱える。
- 初心者でも再現しやすい。

### 使うもの

| 用途 | 採用ツール |
|---|---|
| 拠点間の安全な通信経路 | Tailscale |
| ターミナル接続 | SSH |
| Windowsへのリモートデスクトップ | Windows標準RDP |
| Linux GB10へのリモートデスクトップ | RustDesk over Tailscale |
| MacからWindows RDP接続 | Windows App / Microsoft Remote Desktop系クライアント |

---

## 1. 前提条件

### 1.1 機器

この手順書では、以下の3台を想定する。

| 機器 | 想定OS | 役割 |
|---|---|---|
| 外出先MacBook Pro | macOS | 接続元 |
| 職場Windows | Windows 11 Pro / Windows 10 Pro | 接続元・接続先 |
| 自宅GB10 | Ubuntu系Linux | 接続先 |

GB10がUbuntu系Linuxでない場合でも、Linuxであれば大筋は同じ。ただし、パッケージ管理コマンドはOSに合わせて読み替える。

### 1.2 アカウント

- Tailscaleアカウントを1つ用意する。
- Google / Microsoft / GitHub / Apple IDなどでログインできる。
- 3台すべてを**同じTailscaleアカウント**に参加させる。

### 1.3 Windowsの注意点

WindowsをRDPの接続先にするには、通常 **Windows Pro / Enterprise / Education** が必要。

Windows Homeの場合:

- RDPの接続元にはなれる。
- RDPの接続先には基本的になれない。
- 代替としてRustDeskを使う。

---

## 2. 全体の作業順序

以下の順で進める。

```text
1. 3台すべてにTailscaleを入れる
2. 3台すべてがTailscale上で見えることを確認する
3. 自宅GB10にSSHサーバーを入れる
4. 職場WindowsにSSHサーバーを入れる
5. MacBook ProからGB10へSSH接続する
6. 職場WindowsからGB10へSSH接続する
7. MacBook Proから職場WindowsへSSH接続する
8. 職場WindowsのRDPを有効化する
9. MacBook Proから職場WindowsへRDP接続する
10. GB10にRustDeskを入れる
11. MacBook Pro / 職場WindowsからGB10へリモートデスクトップ接続する
12. 起動時に自動接続されることを確認する
```

---

## 3. Tailscaleの導入

## 3.1 Tailscaleとは

Tailscaleは、複数の端末を安全な仮想プライベートネットワークに参加させるツール。端末同士はTailscale上の専用IPアドレスまたは端末名で通信できる。

この手順では、以下のような名前を使う。

| 機器 | Tailscale上の名前例 |
|---|---|
| 外出先MacBook Pro | `macbook-pro` |
| 職場Windows | `work-windows` |
| 自宅GB10 | `home-gb10` |

実際の名前は、Tailscale管理画面で確認する。

---

## 3.2 MacBook ProにTailscaleを入れる

1. MacBook Proでブラウザを開く。
2. Tailscaleのダウンロードページを開く。  
   <https://tailscale.com/download>
3. macOS版をダウンロードする。
4. インストーラーを開いてインストールする。
5. Tailscaleアプリを起動する。
6. `Log in` を押す。
7. 使用するアカウントでログインする。
8. macOSの確認画面が出たら、VPN構成の追加を許可する。
9. メニューバーにTailscaleアイコンが出れば完了。

確認:

```bash
tailscale status
```

上記コマンドが使えない場合は、Tailscaleアプリの画面で接続状態を確認する。

---

## 3.3 職場WindowsにTailscaleを入れる

1. 職場Windowsでブラウザを開く。
2. Tailscaleのダウンロードページを開く。  
   <https://tailscale.com/download>
3. Windows版インストーラーをダウンロードする。
4. インストーラーを実行する。
5. Tailscaleを起動する。
6. タスクトレイのTailscaleアイコンを右クリックする。
7. `Log in` を選ぶ。
8. MacBook Proと同じアカウントでログインする。
9. 接続状態が `Connected` になれば完了。

確認:

PowerShellを開いて実行する。

```powershell
tailscale status
```

---

## 3.4 自宅GB10にTailscaleを入れる

GB10でターミナルを開く。

Ubuntu系Linuxの場合:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Tailscaleを起動する。

```bash
sudo tailscale up
```

ブラウザでログインURLが表示されるので、MacBook ProやWindowsのブラウザで開いてログインする。

確認:

```bash
tailscale status
```

3台が表示されれば成功。

---

## 3.5 Tailscale管理画面で端末名を確認する

1. ブラウザでTailscale管理画面を開く。  
   <https://login.tailscale.com/admin/machines>
2. 3台が表示されていることを確認する。
3. それぞれの名前とTailscale IPを控える。

記入欄:

| 機器 | Tailscale名 | Tailscale IP |
|---|---|---|
| 外出先MacBook Pro |  |  |
| 職場Windows |  |  |
| 自宅GB10 |  |  |

---

## 4. SSH接続の準備

SSHには以下の2つがある。

| 役割 | 説明 |
|---|---|
| SSHクライアント | 接続する側 |
| SSHサーバー | 接続される側 |

今回必要なSSH接続は以下。

| 接続 | 接続元 | 接続先 | 接続先に必要なもの |
|---|---|---|---|
| 外出先MacBook Pro → 自宅GB10 | Mac | GB10 | SSHサーバー |
| 職場Windows → 自宅GB10 | Windows | GB10 | SSHサーバー |
| 外出先MacBook Pro → 職場Windows | Mac | Windows | OpenSSH Server |

---

## 5. 自宅GB10にSSHサーバーを設定する

GB10で以下を実行する。

```bash
sudo apt update
sudo apt install -y openssh-server
```

SSHサーバーを有効化する。

```bash
sudo systemctl enable --now ssh
```

状態確認:

```bash
systemctl status ssh
```

`active (running)` と表示されれば成功。

GB10のユーザー名を確認する。

```bash
whoami
```

例:

```text
masa
```

この場合、SSH接続時のユーザー名は `masa`。

---

## 6. MacBook ProからGB10へSSH接続する

MacBook Proでターミナルを開く。

接続コマンド:

```bash
ssh GB10ユーザー名@home-gb10
```

例:

```bash
ssh masa@home-gb10
```

Tailscale名で接続できない場合は、Tailscale IPで接続する。

```bash
ssh masa@100.xxx.xxx.xxx
```

初回接続時に以下のような確認が出る。

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

`yes` と入力してEnter。

パスワードを求められたら、GB10のログインパスワードを入力する。

接続できたら、以下を実行する。

```bash
hostname
```

`home-gb10` またはGB10のホスト名が表示されれば成功。

---

## 7. 職場WindowsからGB10へSSH接続する

職場WindowsでWindows TerminalまたはPowerShellを開く。

接続コマンド:

```powershell
ssh GB10ユーザー名@home-gb10
```

例:

```powershell
ssh masa@home-gb10
```

Tailscale名で接続できない場合:

```powershell
ssh masa@100.xxx.xxx.xxx
```

接続できたら、以下を実行する。

```bash
hostname
```

GB10のホスト名が表示されれば成功。

---

## 8. 職場WindowsにSSHサーバーを設定する

MacBook Proから職場WindowsへSSH接続したい場合、職場Windows側にOpenSSH Serverを入れる。

### 8.1 OpenSSH Serverをインストールする

職場Windowsで以下を操作する。

1. `設定` を開く。
2. `システム` を開く。
3. `オプション機能` を開く。
4. `機能を表示` を押す。
5. `OpenSSH Server` を検索する。
6. `OpenSSH Server` を選択する。
7. `次へ` → `追加` を押す。

PowerShellで確認する。

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
```

`State : Installed` になっていれば成功。

### 8.2 SSHサーバーを起動する

PowerShellを**管理者として実行**し、以下を実行する。

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

状態確認:

```powershell
Get-Service sshd
```

`Running` になっていれば成功。

### 8.3 Windowsのユーザー名を確認する

PowerShellで以下を実行する。

```powershell
whoami
```

例:

```text
work-pc\masa
```

SSH接続では通常、ユーザー名部分の `masa` を使う。

---

## 9. MacBook Proから職場WindowsへSSH接続する

MacBook Proでターミナルを開く。

```bash
ssh Windowsユーザー名@work-windows
```

例:

```bash
ssh masa@work-windows
```

Tailscale名で接続できない場合:

```bash
ssh masa@100.xxx.xxx.xxx
```

接続できたら、以下を実行する。

```powershell
hostname
```

職場Windowsのコンピューター名が表示されれば成功。

---

## 10. SSHを使いやすくする設定

MacBook Proで以下のファイルを作る。

```bash
mkdir -p ~/.ssh
nano ~/.ssh/config
```

以下を入力する。

```sshconfig
Host gb10
  HostName home-gb10
  User GB10ユーザー名

Host workwin
  HostName work-windows
  User Windowsユーザー名
```

例:

```sshconfig
Host gb10
  HostName home-gb10
  User masa

Host workwin
  HostName work-windows
  User masa
```

保存後、以下で接続できる。

```bash
ssh gb10
ssh workwin
```

Windows側でも同じように設定できる。

WindowsのSSH設定ファイル:

```text
C:\Users\ユーザー名\.ssh\config
```

例:

```sshconfig
Host gb10
  HostName home-gb10
  User masa
```

接続:

```powershell
ssh gb10
```

---

## 11. SSH鍵認証を設定する

パスワード入力を減らし、安全性を上げるため、SSH鍵認証を設定する。

### 11.1 MacBook ProでSSH鍵を作る

MacBook Proで実行する。

```bash
ssh-keygen -t ed25519 -C "macbook-pro-to-remote"
```

質問が出たら、基本はEnterでよい。

秘密鍵:

```text
~/.ssh/id_ed25519
```

公開鍵:

```text
~/.ssh/id_ed25519.pub
```

**秘密鍵 `id_ed25519` は絶対に他人に渡さない。**

### 11.2 MacBook Proの公開鍵をGB10へ登録する

```bash
ssh-copy-id GB10ユーザー名@home-gb10
```

例:

```bash
ssh-copy-id masa@home-gb10
```

再接続確認:

```bash
ssh masa@home-gb10
```

パスワードなしで入れれば成功。

### 11.3 職場WindowsからGB10へ鍵認証したい場合

職場WindowsのPowerShellで実行する。

```powershell
ssh-keygen -t ed25519 -C "work-windows-to-gb10"
```

公開鍵の中身を表示する。

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

表示された1行をコピーする。

GB10にSSH接続し、以下を実行する。

```bash
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
```

コピーした公開鍵を1行として貼り付ける。

権限を整える。

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Windowsから再接続する。

```powershell
ssh masa@home-gb10
```

---

## 12. 職場Windowsのリモートデスクトップを有効化する

職場WindowsをRDPの接続先にする。

### 12.1 Windowsエディション確認

職場Windowsで以下を開く。

```text
設定 → システム → バージョン情報
```

`Windows 11 Pro` や `Windows 10 Pro` であればRDPホストにできる。

Windows Homeの場合は、この章を飛ばし、RustDeskを使う。

### 12.2 RDPを有効化する

1. `設定` を開く。
2. `システム` を開く。
3. `リモート デスクトップ` を開く。
4. `リモート デスクトップ` をオンにする。
5. 確認画面で `確認` を押す。
6. PC名を控える。

この手順では、PC名ではなくTailscale名 `work-windows` を使う。

### 12.3 RDP接続を許可するユーザーを確認する

1. `設定 → システム → リモート デスクトップ` を開く。
2. `リモート デスクトップ ユーザー` を開く。
3. 接続に使うWindowsユーザーが許可されていることを確認する。

管理者アカウントなら通常は接続可能。

---

## 13. MacBook Proから職場Windowsへリモートデスクトップ接続する

### 13.1 MacにWindows Appを入れる

1. Mac App Storeを開く。
2. `Windows App` を検索する。
3. Microsoft提供のアプリをインストールする。

### 13.2 RDP接続を追加する

1. Windows Appを開く。
2. `+` を押す。
3. `PCを追加` を選ぶ。
4. `PC name` に以下を入れる。

```text
work-windows
```

Tailscale名で接続できない場合は、Tailscale IPを入れる。

```text
100.xxx.xxx.xxx
```

5. `Credentials` は最初は `Ask when required` にする。
6. 保存する。
7. 作成した接続を開く。
8. Windowsユーザー名とパスワードを入力する。

接続できれば成功。

---

## 14. GB10へリモートデスクトップ接続する方針

GB10がLinuxの場合、Windows RDPだけではそのまま扱いにくい。初心者向けには以下の方針が現実的。

| 方法 | 評価 |
|---|---|
| RustDesk over Tailscale | 推奨。GUI操作が簡単 |
| xrdp | Linuxデスクトップ環境依存。つまずきやすい |
| VNC | 設定は可能だがセキュリティ管理が必要 |
| Chrome Remote Desktop | Googleアカウント前提。環境依存あり |

この手順書では **RustDesk over Tailscale** を使う。

---

## 15. GB10にRustDeskを入れる

### 15.1 GB10側の準備

GB10にデスクトップ環境があることを確認する。

以下のどちらかが使える状態ならよい。

- GNOME
- KDE
- XFCE
- Ubuntu Desktop

サーバー版UbuntuなどでGUIがない場合、RustDeskで画面操作はできない。この場合はSSH運用を基本にするか、Ubuntu DesktopなどのGUI環境を導入する。

### 15.2 RustDeskをダウンロードする

GB10でブラウザを開き、RustDeskの公式サイトからLinux版をダウンロードする。

<https://rustdesk.com/>

Ubuntu系なら `.deb` パッケージを使う。

例:

```bash
cd ~/Downloads
sudo apt install ./rustdesk-*.deb
```

依存関係でエラーが出た場合:

```bash
sudo apt --fix-broken install
```

### 15.3 RustDeskを起動する

GB10でRustDeskを起動する。

```bash
rustdesk
```

またはアプリケーション一覧からRustDeskを起動する。

### 15.4 Direct IP Accessを有効化する

RustDeskの画面で以下を設定する。

1. `Settings` を開く。
2. `Security` を開く。
3. `Enable direct IP access` をオンにする。
4. `Permanent password` を設定する。

注意:

- 一時パスワードだけだと、無人状態のGB10に接続しづらい。
- Permanent passwordは長く強いものにする。
- 使い回しのパスワードは避ける。

---

## 16. MacBook ProからGB10へRustDesk接続する

MacBook ProにもRustDeskを入れる。

1. RustDesk公式サイトを開く。  
   <https://rustdesk.com/>
2. macOS版をダウンロードする。
3. インストールする。
4. RustDeskを起動する。
5. 接続先にGB10のTailscale IPを入力する。

例:

```text
100.xxx.xxx.xxx
```

6. 接続する。
7. GB10側で設定したPermanent passwordを入力する。

接続できれば成功。

---

## 17. 職場WindowsからGB10へRustDesk接続する

職場WindowsにもRustDeskを入れる。

1. RustDesk公式サイトを開く。  
   <https://rustdesk.com/>
2. Windows版をダウンロードする。
3. インストールする。
4. RustDeskを起動する。
5. 接続先にGB10のTailscale IPを入力する。

```text
100.xxx.xxx.xxx
```

6. GB10側で設定したPermanent passwordを入力する。

接続できれば成功。

---

## 18. 職場WindowsがWindows Homeの場合の代替

職場WindowsがWindows Homeの場合、RDPの接続先にはできない。

この場合は、職場WindowsにもRustDeskを入れ、MacBook ProからRustDeskで接続する。

手順:

1. 職場WindowsにTailscaleを入れる。
2. 職場WindowsにRustDeskを入れる。
3. RustDeskで `Enable direct IP access` をオンにする。
4. Permanent passwordを設定する。
5. MacBook ProのRustDeskから、職場WindowsのTailscale IPへ接続する。

---

## 19. 自動起動設定

「いつでも接続できる」状態にするには、再起動後もTailscale / SSH / RustDesk / RDPが動く必要がある。

### 19.1 GB10

Tailscale:

```bash
sudo systemctl enable --now tailscaled
```

SSH:

```bash
sudo systemctl enable --now ssh
```

RustDesk:

RustDeskの設定画面で以下を有効化する。

```text
Start RustDesk on boot
```

項目名はバージョンにより多少異なる場合がある。

### 19.2 職場Windows

Tailscale:

- 通常はインストール後、自動起動する。
- タスクトレイにTailscaleアイコンが出ることを確認する。

OpenSSH Server:

```powershell
Set-Service -Name sshd -StartupType Automatic
```

RDP:

- `設定 → システム → リモート デスクトップ` がオンであることを確認する。

RustDeskを使う場合:

- RustDeskの設定で自動起動をオンにする。

### 19.3 MacBook Pro

Tailscale:

- メニューバーにTailscaleアイコンが出ることを確認する。
- ログイン時にTailscaleが起動する設定にしておく。

---

## 20. 接続テスト表

以下を1つずつ確認する。

| No | 接続 | 方法 | 成功条件 |
|---:|---|---|---|
| 1 | MacBook Pro → GB10 | SSH | `ssh gb10` で入れる |
| 2 | 職場Windows → GB10 | SSH | `ssh gb10` で入れる |
| 3 | MacBook Pro → 職場Windows | SSH | `ssh workwin` で入れる |
| 4 | MacBook Pro → 職場Windows | RDP | Windowsデスクトップが表示される |
| 5 | MacBook Pro → GB10 | RustDesk | GB10の画面が表示される |
| 6 | 職場Windows → GB10 | RustDesk | GB10の画面が表示される |

---

## 21. よく使う接続コマンド

### MacBook ProからGB10

```bash
ssh gb10
```

または:

```bash
ssh masa@home-gb10
```

### 職場WindowsからGB10

```powershell
ssh gb10
```

または:

```powershell
ssh masa@home-gb10
```

### MacBook Proから職場Windows

```bash
ssh workwin
```

または:

```bash
ssh masa@work-windows
```

---

## 22. セキュリティ設定

### 22.1 やるべきこと

- Tailscaleアカウントに2要素認証を設定する。
- 各PCのログインパスワードを強くする。
- SSH鍵認証を使う。
- RustDeskのPermanent passwordを長くする。
- 使わない端末はTailscale管理画面から削除する。
- 退職・紛失・売却した端末は必ずTailscaleから外す。

### 22.2 やらない方がよいこと

- 自宅ルーターでSSHの22番ポートをインターネットに開ける。
- RDPの3389番ポートをインターネットに開ける。
- RustDeskのパスワードを短くする。
- すべての端末で同じパスワードを使い回す。
- Tailscaleに知らない端末を参加させたままにする。

---

## 23. トラブルシュート

### 23.1 `ssh: Could not resolve hostname home-gb10` と出る

原因:

- Tailscale名が違う。
- MagicDNSが無効。
- Tailscaleにログインしていない。

対応:

1. Tailscale管理画面で正しい端末名を確認する。
2. Tailscale IPで接続する。

```bash
ssh masa@100.xxx.xxx.xxx
```

### 23.2 `Connection timed out` と出る

原因:

- 接続先のTailscaleがオフ。
- 接続先PCがスリープしている。
- SSHサーバーが起動していない。

対応:

GB10で確認:

```bash
sudo systemctl status ssh
sudo systemctl status tailscaled
```

Windowsで確認:

```powershell
Get-Service sshd
```

### 23.3 パスワードが通らない

原因:

- 接続先OSのユーザー名が違う。
- パスワードが違う。
- Microsoftアカウントとローカルアカウントの扱いで混乱している。

対応:

Windows側でユーザー名確認:

```powershell
whoami
```

Linux側でユーザー名確認:

```bash
whoami
```

### 23.4 RDPで職場Windowsに接続できない

確認項目:

- WindowsがPro以上か。
- RDPが有効か。
- TailscaleがConnectedか。
- 接続先をPC名ではなくTailscale IPにして試したか。
- Windowsがスリープしていないか。

### 23.5 RustDeskでGB10に接続できない

確認項目:

- GB10でRustDeskが起動しているか。
- GB10がGUIログイン済みか。
- RustDeskのDirect IP accessが有効か。
- 接続先にRustDesk IDではなくTailscale IPを入れているか。
- Tailscale上でGB10にpingできるか。

確認:

```bash
ping home-gb10
```

または:

```bash
ping 100.xxx.xxx.xxx
```

---

## 24. 最小構成チェックリスト

### Tailscale

- [ ] MacBook ProにTailscaleを入れた
- [ ] 職場WindowsにTailscaleを入れた
- [ ] 自宅GB10にTailscaleを入れた
- [ ] 3台が同じTailscaleアカウントに見えている
- [ ] 3台のTailscale名とIPを控えた

### SSH

- [ ] GB10にOpenSSH Serverを入れた
- [ ] GB10のSSHが自動起動する
- [ ] MacBook ProからGB10へSSHできる
- [ ] 職場WindowsからGB10へSSHできる
- [ ] 職場WindowsにOpenSSH Serverを入れた
- [ ] MacBook Proから職場WindowsへSSHできる

### リモートデスクトップ

- [ ] 職場WindowsのRDPを有効にした
- [ ] MacBook Proから職場WindowsへRDPできる
- [ ] GB10にRustDeskを入れた
- [ ] GB10でDirect IP accessを有効にした
- [ ] MacBook ProからGB10へRustDesk接続できる
- [ ] 職場WindowsからGB10へRustDesk接続できる

### セキュリティ

- [ ] Tailscaleアカウントに2要素認証を設定した
- [ ] SSH鍵認証を設定した
- [ ] RustDeskのPermanent passwordを強くした
- [ ] ルーターのポート開放をしていない

---

## 25. 推奨運用

日常的には以下の使い分けにする。

| やりたいこと | 推奨手段 |
|---|---|
| GB10でコマンド実行・AI環境操作 | SSH |
| GB10のGUIアプリを操作 | RustDesk |
| 職場Windowsを画面操作 | RDP |
| 職場Windowsで軽いコマンド実行 | SSH |
| ファイル転送 | scp / rsync / Tailscale経由の共有 |

### ファイル転送例: MacBook ProからGB10へ送る

```bash
scp ./local-file.txt gb10:~/
```

### ファイル転送例: GB10からMacBook Proへ持ってくる

```bash
scp gb10:~/remote-file.txt ./
```

---

## 26. 完了状態

この手順が完了すると、以下が可能になる。

| 接続 | SSH | リモートデスクトップ |
|---|---:|---:|
| 外出先MacBook Pro → 自宅GB10 | 可能 | RustDeskで可能 |
| 職場Windows → 自宅GB10 | 可能 | RustDeskで可能 |
| 外出先MacBook Pro → 職場Windows | 可能 | RDPで可能 |

最終的に覚える接続先は以下だけでよい。

```text
gb10      = 自宅GB10
workwin   = 職場Windows
```

SSH:

```bash
ssh gb10
ssh workwin
```

リモートデスクトップ:

```text
MacBook Pro → 職場Windows: Windows Appで work-windows または Tailscale IPへ接続
MacBook Pro / 職場Windows → GB10: RustDeskでGB10のTailscale IPへ接続
```
