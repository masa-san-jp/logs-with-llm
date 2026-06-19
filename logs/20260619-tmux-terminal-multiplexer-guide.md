英語mdファイル名提案: 20260619-tmux-terminal-multiplexer-guide.md

tmuxとは

tmux は terminal multiplexer、つまり「1つのターミナル画面の中で複数の仮想端末を管理するツール」です。複数のプログラムを1つの端末内で切り替えたり、画面分割したり、SSH切断後も作業セッションを生かしたまま再接続できます。公式説明でも、tmuxは複数の端末を1つの画面から作成・操作でき、detachしてバックグラウンドで継続し、後でreattachできるものとされています。 

2026年6月時点で、GitHub上の最新安定版は tmux 3.6b です。3.7-rc はリリース候補であり、通常利用なら安定版を使うのが無難です。 

⸻

何が便利なのか

tmuxの価値は、単なる「ターミナル分割」ではなく、作業状態をプロセスとして保持できることにあります。

典型的な用途は次の通りです。

用途	内容
SSH作業の保険	接続が切れてもサーバー側で作業が継続する
長時間処理	学習、ビルド、バックアップ、ログ監視などを放置できる
開発環境の固定化	editor / shell / logs / tests を1画面に配置
複数プロジェクト管理	projectごとにsessionを分ける
CLI中心の高速作業	マウスやGUIタブへの依存を減らせる
ペア作業・監視	同じsessionへ複数clientで接続できる

⸻

基本構造

tmuxは次の階層で理解すると速いです。

tmux server
└── session
    ├── window
    │   ├── pane
    │   └── pane
    └── window
        └── pane

公式マニュアルでは、sessionはtmuxが管理するpseudo terminalの集合で、sessionは1つ以上のwindowを持ち、windowは画面全体を占め、さらにpaneへ分割できると説明されています。 

用語

用語	意味	例
server	tmuxの裏側で動く管理プロセス	tmux全体
client	今表示している端末側の接続	あなたのTerminal.app / iTerm2 / SSH端末
session	作業単位	project-a, infra, blog
window	session内のタブ相当	editor, server, logs
pane	window内の分割領域	左: vim、右: logs、下: shell

⸻

インストール

主要環境ではパッケージマネージャから入れられます。公式Installingページでは、Debian/Ubuntuは apt install tmux、Fedoraは dnf install tmux、RHEL/CentOSは yum install tmux、macOS Homebrewは brew install tmux が例示されています。ただし、ディストリビューション付属パッケージは古い場合があります。 

# macOS
brew install tmux
# Ubuntu / Debian
sudo apt install tmux
# Fedora
sudo dnf install tmux
# Arch Linux
sudo pacman -S tmux
# バージョン確認
tmux -V

⸻

最初に覚える操作

tmuxでは、tmux自身を操作するために prefix key を先に押します。デフォルトは Ctrl-b です。公式Getting Startedでも、tmux制御用の特別なキーがprefix keyで、デフォルトは C-b と説明されています。 

表記上はこう読みます。

C-b c

これは、

Ctrl-b を押す → 離す → c を押す

という意味です。

最小操作セット

操作	キー
ヘルプ表示	C-b ?
新しいwindow	C-b c
window一覧	C-b w
次のwindow	C-b n
前のwindow	C-b p
window番号へ移動	C-b 0〜C-b 9
左右分割	C-b %
上下分割	C-b "
pane移動	C-b + 矢印
pane番号表示	C-b q
pane拡大・解除	C-b z
sessionから離脱	C-b d
コマンド入力	C-b :
copy mode	C-b [
paste	C-b ]

C-b ? でデフォルトキーバインド一覧を表示できます。公式Getting Startedでも、すべてのデフォルトkey bindingは短い説明付きで表示でき、C-b ? で一覧を見られると説明されています。 

⸻

基本コマンド

sessionを作る

tmux

名前付きsessionを作るなら：

tmux new -s work

または正式名：

tmux new-session -s work

sessionから離脱する

tmux内で：

C-b d

離脱しても、session内のプロセスは終了しません。

session一覧を見る

tmux ls

sessionへ再接続する

tmux attach -t work

省略形：

tmux a -t work

sessionを終了する

tmux kill-session -t work

すべて終了：

tmux kill-server

⸻

windowとpaneの使い分け

window

windowは「タブ」に近い概念です。

例：

session: project-a
├── window 0: editor
├── window 1: server
├── window 2: db
└── window 3: logs

window作成：

C-b c

window名変更：

C-b ,

window終了：

C-b &

pane

paneは「画面分割」です。公式Getting Startedでは、paneはwindowを分割して作り、C-b % は左右分割、C-b " は上下分割と説明されています。 

左右分割：

C-b %

上下分割：

C-b "

pane終了：

exit

または：

C-b x

pane拡大：

C-b z

⸻

実用的なワークフロー例

開発用session

tmux new -s app

window構成例：

0: editor
1: server
2: logs
3: git

操作例：

C-b c        # window作成
C-b ,        # window名変更
C-b %        # 左右分割
C-b "        # 上下分割
C-b z        # pane最大化
C-b d        # 離脱

再開：

tmux attach -t app

サーバーで長時間処理

ssh server
tmux new -s train
python train.py

通信が切れても、後で：

ssh server
tmux attach -t train

で戻れます。

ログ監視

tmux new -s monitor

paneを分割して：

tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
htop

⸻

copy mode

tmuxには独自のコピー・ペースト機構があります。公式Getting Startedでは、copy modeは C-b [ で入り、直近のコピー内容は C-b ] でpaneへ貼り付けると説明されています。 

C-b [    # copy mode
C-b ]    # paste

vi風にしたい場合は .tmux.conf に：

set -g mode-keys vi
set -g status-keys vi

⸻

.tmux.conf の基本

設定ファイルは通常：

~/.tmux.conf

反映：

C-b :
source-file ~/.tmux.conf

またはshellから：

tmux source-file ~/.tmux.conf

推奨スターター設定

# prefixをCtrl-aへ変更
set -g prefix C-a
unbind C-b
bind C-a send-prefix
# window番号を1始まりにする
set -g base-index 1
set -g pane-base-index 1
# window番号の隙間を自動で詰める
set -g renumber-windows on
# マウス操作を有効化
set -g mouse on
# 履歴行数を増やす
set -g history-limit 100000
# vi風copy mode
set -g mode-keys vi
set -g status-keys vi
# ステータスバーを上に表示
set -g status-position top
# true color対応
set -g default-terminal "tmux-256color"
set -as terminal-features ",xterm-256color:RGB"

公式Getting Startedでも、prefix変更は set -g prefix C-a、unbind C-b、bind C-a send-prefix の形で例示されています。また、base-index、history-limit、mouse、mode-keys、renumber-windows などは有用なoptionとして挙げられています。 

⸻

よく使うコマンド集

session

tmux new -s name          # session作成
tmux ls                  # session一覧
tmux a -t name            # sessionへ接続
tmux rename-session -t old new
tmux kill-session -t name

window

tmux new-window -n logs
tmux rename-window editor
tmux kill-window

tmux内では：

C-b c    # new window
C-b ,    # rename window
C-b &    # kill window
C-b n    # next
C-b p    # previous

pane

C-b %        # 左右分割
C-b "        # 上下分割
C-b 矢印     # pane移動
C-b z        # zoom
C-b x        # kill pane
C-b q        # pane番号表示

コマンドとしては：

tmux split-window -h
tmux split-window -v
tmux select-pane -L
tmux select-pane -R
tmux resize-pane -L 10
tmux resize-pane -R 10

⸻

tmuxを使うべき人

tmuxは次のタイプに特に向きます。

タイプ	理由
SSHを多用する	接続断に強い
CLI中心の開発者	editor / shell / logs / test をまとめやすい
AI・ML・バッチ処理を走らせる人	長時間ジョブと相性が良い
サーバー運用者	監視・ログ・作業状態を保持しやすい
dotfilesを育てたい人	自分の作業環境を再現しやすい

逆に、ローカルGUI中心で、VS Code統合ターミナルやiTerm2のタブ・分割だけで十分なら、tmuxの学習コストに見合わない場合もあります。

⸻

screenとの違い

screen も古典的なterminal multiplexerですが、現在新しく覚えるなら通常はtmuxでよいです。

観点	tmux	screen
設計	比較的新しい	古い
設定	分かりやすい	癖が強い
pane分割	強い	可能だがtmuxの方が扱いやすい
ステータスバー	柔軟	やや弱い
普及	開発者・SRE界隈で広い	古い環境で残る

⸻

tmuxで詰まりやすい点

C-b が押しにくい

多くの人は Ctrl-a に変えます。

set -g prefix C-a
unbind C-b
bind C-a send-prefix

ネストしたtmux

ローカルtmux内でSSH先でもtmuxを使うと、prefixが衝突します。

対策：

C-b C-b

で内側にprefixを送る、またはローカルとリモートでprefixを変える。

コピーがOSクリップボードに入らない

tmuxのcopy bufferとOSのclipboardは別物です。macOSなら reattach-to-user-namespace や pbcopy 連携、Linuxなら xclip / wl-copy、SSH越しならOSC 52などを検討します。

色が変

まず確認：

echo $TERM
tmux info | grep RGB

設定例：

set -g default-terminal "tmux-256color"
set -as terminal-features ",xterm-256color:RGB"

ただし、古いサーバーでは tmux-256color のterminfoが存在しないことがあります。その場合は screen-256color に戻すほうが安定する場合があります。

⸻

まず覚えるべき順番

1. tmux new -s work
2. C-b d
3. tmux attach -t work
4. C-b c
5. C-b n / C-b p
6. C-b % / C-b "
7. C-b z
8. C-b ?
9. .tmux.conf
10. copy mode

最初は「sessionを作る、離脱する、戻る」だけで十分です。tmuxの本質は画面分割より 作業状態の永続化 です。