# WASI.py リファレンス（WASI_Wiki）

## 概要
WASI.py は GUI（tkinter）ベースのランチャーで、個別の機能モジュールを streamlit プロセスとして起動・停止・表示する役割を持ちます。各モジュールは独立プロセスで localhost:port にて提供されます。

## 主要な役割（ファイル内の振る舞い）
- メインクラス: `WASIManager`
  - GUI 初期化（ロゴ、一覧、ログ、操作ボタン）
  - サブアプリ管理（start/stop/open/status）
  - 終了時のクリーンアップ（全停止）
- エントリポイント: `main()`  
  - スクリプトの作業ディレクトリを `__file__` のある場所に変更
  - ロード画面を表示してからメインウィンドウを起動

## 依存関係・起動手順
1. Python 3.8+
2. 依存パッケージをインストール:
   ```bash
   pip install -r requirements.txt
   ```
3. 実行:
   ```bash
   python sonyapp\WASI.py
   ```

## apps 定義（WASI.py 内）
- 各アプリは `self.apps` に辞書で定義:
  - キー例: `data`, `vis_b`, `param`, `setting`, `sim`, `vis_a`
  - 各エントリ: name, description, icon, folder, port, process, status
- デフォルト割当ポート: 8501〜8506（フォルダ名とポートの対応を参照）

## サブアプリの起動手順（コードの挙動）
- `start_app(app_key)`:
  - `folder/app.py` の存在チェック（無ければエラー表示）
  - 実行コマンド:
    ```
    python -m streamlit run app.py --server.port <port> --server.headless true --browser.gatherUsageStats false
    ```
  - subprocess を Popen(stdout=PIPE, stderr=PIPE, text=True) で生成
  - `check_app_startup` を別スレッドで実行して起動確認

- `check_app_startup(app_key)`:
  - 最大30秒ポーリング
  - プロセスが終了していないか確認（poll）
  - socket.connect_ex で localhost:port に接続できるか確認（接続成功で `実行中`）
  - タイムアウト時は「起動中」状態のままログ出力

## 停止動作
- `stop_app(app_key)`:
  - Windows: `process.terminate()`（それ以外は `SIGTERM` を送信）
  - 5秒待って終了しない場合は `process.kill()` で強制終了
  - `process` を `None` にして状態を `停止中` に更新

## UI とログ
- 各アプリ行に「起動」「停止」「開く」ボタン、状態ラベルを表示
- ログ領域にタイムスタンプ付きでメッセージを追記（`self.log()`）
- アイコンが存在しない場合は絵文字プレースホルダーを使用

## ロード画面
- `show_loading_screen()` で簡易プログレスを表示
- プログレスは 0〜100 を 0.03s 毎に更新（合計約3秒）
- ロゴがなければ代替テキスト表示

## デバッグ・トラブルシューティング
- Streamlit 未インストール: `pip install streamlit`
- ポート競合確認（Windows 例）:
  ```bash
  netstat -ano | findstr :8501
  ```
- start_app が失敗する典型原因:
  - `folder/app.py` が存在しない
  - port が既に使用中
  - streamlit インストールや PATH 問題
- 詳細ログ: サブプロセスの stdout/stderr を参照（現状は PIPE に入れているが GUI に出力していないため、必要なら出力取り出しを追加する）

## 開発者向け: 新規サブアプリ追加手順
1. `new_app/` フォルダを作成し `app.py` を置く（Streamlit アプリ）。
2. `icon/new_app.png` を追加（任意）。
3. `WASI.py` の `self.apps` にエントリを追加（port は重複しない番号を選ぶ）。
4. 単体で streamlit 起動を確認後、WASI から起動テストを行う。

## セキュリティ・運用上の注意
- ポートは localhost に限定されるが、運用環境でのファイアウォール設定を確認すること。
- subprocess の出力は将来的にログファイルへリダイレクトすることを推奨。

## 参照ドキュメント
- プロジェクト内の `マニュアル.pdf`（操作手順、画面説明）
- `機能仕様書.pdf`（各モジュールの入出力仕様、データフォーマット）
- これらの PDF の該当ページを指定いただければ、Wiki に具体的な画面手順やパラメータ表を追加可能。
