import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import webbrowser
import time
import os
import sys
from PIL import Image, ImageTk
import signal

class WASIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("WASI - Wafer-line Analysis SImulation")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # アプリケーション情報
        self.apps = {
            'data': {
                'name': 'データの読み込み',
                'description': 'データの読み込み（製造ログ，品質基準表，バッチ情報）',
                'icon': 'icon/data.png',
                'folder': 'data',
                'port': 8501,
                'process': None,
                'status': '停止中'
            },
            'vis_b': {
                'name': '製造ログデータの可視化',
                'description': '製造ログデータの可視化',
                'icon': 'icon/vis_b.png',
                'folder': 'vis_b',
                'port': 8502,
                'process': None,
                'status': '停止中'
            },
            'param': {
                'name': '製造パラメータ推定',
                'description': '製造パラメータ推定',
                'icon': 'icon/param.png',
                'folder': 'param',
                'port': 8503,
                'process': None,
                'status': '停止中'
            },
            'setting': {
                'name': '装置汎用化設定',
                'description': '装置汎用化設定',
                'icon': 'icon/setting.png',
                'folder': 'setting',
                'port': 8504,
                'process': None,
                'status': '停止中'
            },
            'sim': {
                'name': '装置汎用化シミュレーション',
                'description': '装置汎用化シミュレーション',
                'icon': 'icon/sim.png',
                'folder': 'sim',
                'port': 8505,
                'process': None,
                'status': '停止中'
            },
            'vis_a': {
                'name': 'シミュレーション結果可視化',
                'description': 'シミュレーション結果可視化',
                'icon': 'icon/vis_a.png',
                'folder': 'vis_a',
                'port': 8506,
                'process': None,
                'status': '停止中'
            }
        }
        
        self.setup_ui()
        self.check_dependencies()
        
        # 終了時の処理を設定
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """UIの初期設定"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ロゴとタイトル
        logo_title_frame = ttk.Frame(main_frame)
        logo_title_frame.grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # ロゴ画像を表示
        try:
            if os.path.exists('icon/logo.png'):
                logo_image = Image.open('icon/logo.png')
                logo_image = logo_image.resize((80, 80), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label = tk.Label(logo_title_frame, image=self.logo_photo)
                logo_label.pack(pady=(0, 10))
        except Exception as e:
            print(f"ロゴ読み込みエラー: {e}")
        
        # タイトル
        title_label = tk.Label(logo_title_frame, text="Wafer-line Analysis SImulation ", 
                              font=("Arial", 20, "bold"), fg="black")
        title_label.pack()
        
        wasi_label = tk.Label(logo_title_frame, text="WASI", 
                             font=("Arial", 24, "bold"), fg="red")
        wasi_label.pack()
        
        # ヘッダー
        ttk.Label(main_frame, text="アイコン", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=5)
        ttk.Label(main_frame, text="説明", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=10, pady=5)
        ttk.Label(main_frame, text="状態", font=("Arial", 10, "bold")).grid(row=1, column=2, padx=10, pady=5)
        ttk.Label(main_frame, text="操作", font=("Arial", 10, "bold")).grid(row=1, column=3, padx=10, pady=5)
        
        # 区切り線
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=2, column=0, columnspan=4, sticky="ew", pady=10)
        
        # アプリケーション行を作成
        self.status_labels = {}
        self.start_buttons = {}
        self.stop_buttons = {}
        
        row = 3
        for app_key, app_info in self.apps.items():
            self.create_app_row(main_frame, row, app_key, app_info)
            row += 1
        
        # 全体操作ボタン
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=row, column=0, columnspan=4, pady=20)
        
        ttk.Button(control_frame, text="全て起動", command=self.start_all_apps).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="全て停止", command=self.stop_all_apps).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="状態更新", command=self.update_all_status).pack(side=tk.LEFT, padx=5)
        
        # ログエリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.grid(row=row+1, column=0, columnspan=4, sticky="ew", pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        self.log("WASI システムを起動しました")
    
    def create_app_row(self, parent, row, app_key, app_info):
        """アプリケーション行を作成"""
        # アイコン
        icon_frame = ttk.Frame(parent)
        icon_frame.grid(row=row, column=0, padx=10, pady=5)
        
        try:
            # アイコン画像を読み込み
            if os.path.exists(app_info['icon']):
                image = Image.open(app_info['icon'])
                image = image.resize((40, 40), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                icon_label = ttk.Label(icon_frame, image=photo)
                icon_label.image = photo  # 参照を保持
                icon_label.pack()
            else:
                # アイコンがない場合はテキストで表示
                icon_label = ttk.Label(icon_frame, text="📊", font=("Arial", 20))
                icon_label.pack()
        except Exception as e:
            # エラーの場合はデフォルトアイコン
            icon_label = ttk.Label(icon_frame, text="📊", font=("Arial", 20))
            icon_label.pack()
        
        # 説明
        desc_frame = ttk.Frame(parent)
        desc_frame.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        
        name_label = ttk.Label(desc_frame, text=app_info['name'], font=("Arial", 11, "bold"))
        name_label.pack(anchor="w")
        
        desc_label = ttk.Label(desc_frame, text=app_info['description'], font=("Arial", 9))
        desc_label.pack(anchor="w")
        
        port_label = ttk.Label(desc_frame, text=f"ポート: {app_info['port']}", font=("Arial", 8))
        port_label.pack(anchor="w")
        
        # 状態
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=row, column=2, padx=10, pady=5)
        
        self.status_labels[app_key] = ttk.Label(status_frame, text=app_info['status'], 
                                              foreground="red", font=("Arial", 10, "bold"))
        self.status_labels[app_key].pack()
        
        # 操作ボタン
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=3, padx=10, pady=5)
        
        self.start_buttons[app_key] = ttk.Button(button_frame, text="起動", 
                                               command=lambda k=app_key: self.start_app(k))
        self.start_buttons[app_key].pack(side=tk.LEFT, padx=2)
        
        self.stop_buttons[app_key] = ttk.Button(button_frame, text="停止", 
                                              command=lambda k=app_key: self.stop_app(k),
                                              state="disabled")
        self.stop_buttons[app_key].pack(side=tk.LEFT, padx=2)
        
        open_button = ttk.Button(button_frame, text="開く", 
                               command=lambda k=app_key: self.open_app(k))
        open_button.pack(side=tk.LEFT, padx=2)
    
    def log(self, message):
        """ログメッセージを表示"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def check_dependencies(self):
        """依存関係をチェック"""
        try:
            subprocess.run([sys.executable, "-c", "import streamlit"], 
                          check=True, capture_output=True)
            self.log("Streamlit が利用可能です")
        except subprocess.CalledProcessError:
            self.log("警告: Streamlit がインストールされていません")
            messagebox.showwarning("警告", 
                                 "Streamlit がインストールされていません。\n"
                                 "pip install streamlit でインストールしてください。")
    
    def start_app(self, app_key):
        """アプリケーションを起動"""
        app_info = self.apps[app_key]
        
        if app_info['process'] is not None:
            self.log(f"{app_info['name']} は既に起動中です")
            return
        
        try:
            # Streamlitアプリを起動
            app_path = os.path.join(app_info['folder'], 'app.py')
            
            if not os.path.exists(app_path):
                self.log(f"エラー: {app_path} が見つかりません")
                messagebox.showerror("エラー", f"アプリケーションファイルが見つかりません:\n{app_path}")
                return
            
            cmd = [
                sys.executable, "-m", "streamlit", "run", app_path,
                "--server.port", str(app_info['port']),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ]
            
            self.log(f"{app_info['name']} を起動中... (ポート: {app_info['port']})")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, 
                                     universal_newlines=True)
            
            app_info['process'] = process
            app_info['status'] = '起動中'
            
            # 起動確認を別スレッドで実行
            threading.Thread(target=self.check_app_startup, args=(app_key,), daemon=True).start()
            
            self.update_ui_state(app_key)
            
        except Exception as e:
            self.log(f"エラー: {app_info['name']} の起動に失敗しました - {str(e)}")
            messagebox.showerror("エラー", f"アプリケーションの起動に失敗しました:\n{str(e)}")
    
    def check_app_startup(self, app_key):
        """アプリケーションの起動を確認"""
        app_info = self.apps[app_key]
        
        # 最大30秒待機
        for _ in range(30):
            if app_info['process'] is None:
                return
                
            if app_info['process'].poll() is not None:
                # プロセスが終了している
                self.log(f"エラー: {app_info['name']} が異常終了しました")
                app_info['process'] = None
                app_info['status'] = 'エラー'
                self.root.after(0, lambda: self.update_ui_state(app_key))
                return
            
            try:
                # ポートに接続してみる（簡易チェック）
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', app_info['port']))
                sock.close()
                
                if result == 0:
                    # 接続成功
                    app_info['status'] = '実行中'
                    self.log(f"{app_info['name']} の起動が完了しました")
                    self.root.after(0, lambda: self.update_ui_state(app_key))
                    return
                    
            except Exception:
                pass
            
            time.sleep(1)
        
        # タイムアウト
        self.log(f"警告: {app_info['name']} の起動確認がタイムアウトしました")
        app_info['status'] = '起動中'
        self.root.after(0, lambda: self.update_ui_state(app_key))
    
    def stop_app(self, app_key):
        """アプリケーションを停止"""
        app_info = self.apps[app_key]
        
        if app_info['process'] is None:
            self.log(f"{app_info['name']} は既に停止中です")
            return
        
        try:
            self.log(f"{app_info['name']} を停止中...")
            
            # プロセスを終了
            if os.name == 'nt':  # Windows
                app_info['process'].terminate()
            else:  # Unix/Linux
                app_info['process'].send_signal(signal.SIGTERM)
            
            # 5秒待って強制終了
            try:
                app_info['process'].wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.log(f"{app_info['name']} を強制終了します")
                app_info['process'].kill()
                app_info['process'].wait()
            
            app_info['process'] = None
            app_info['status'] = '停止中'
            
            self.log(f"{app_info['name']} を停止しました")
            self.update_ui_state(app_key)
            
        except Exception as e:
            self.log(f"エラー: {app_info['name']} の停止に失敗しました - {str(e)}")
    
    def open_app(self, app_key):
        """アプリケーションをブラウザで開く"""
        app_info = self.apps[app_key]
        url = f"http://localhost:{app_info['port']}"
        
        try:
            webbrowser.open(url)
            self.log(f"{app_info['name']} をブラウザで開きました: {url}")
        except Exception as e:
            self.log(f"エラー: ブラウザでの起動に失敗しました - {str(e)}")
            messagebox.showerror("エラー", f"ブラウザでの起動に失敗しました:\n{str(e)}")
    
    def update_ui_state(self, app_key):
        """UIの状態を更新"""
        app_info = self.apps[app_key]
        
        # 状態ラベルの更新
        status = app_info['status']
        if status == '実行中':
            color = "green"
        elif status == '起動中':
            color = "orange"
        elif status == 'エラー':
            color = "red"
        else:
            color = "red"
        
        self.status_labels[app_key].config(text=status, foreground=color)
        
        # ボタンの状態更新
        if app_info['process'] is not None:
            self.start_buttons[app_key].config(state="disabled")
            self.stop_buttons[app_key].config(state="normal")
        else:
            self.start_buttons[app_key].config(state="normal")
            self.stop_buttons[app_key].config(state="disabled")
    
    def start_all_apps(self):
        """全てのアプリケーションを起動"""
        self.log("全てのアプリケーションを起動中...")
        for app_key in self.apps.keys():
            if self.apps[app_key]['process'] is None:
                self.start_app(app_key)
                time.sleep(2)  # 起動間隔を空ける
    
    def stop_all_apps(self):
        """全てのアプリケーションを停止"""
        self.log("全てのアプリケーションを停止中...")
        for app_key in self.apps.keys():
            if self.apps[app_key]['process'] is not None:
                self.stop_app(app_key)
    
    def update_all_status(self):
        """全ての状態を更新"""
        self.log("状態を更新中...")
        for app_key in self.apps.keys():
            self.update_ui_state(app_key)
    
    def on_closing(self):
        """ウィンドウ終了時の処理"""
        if messagebox.askokcancel("終了", "全てのアプリケーションを停止して終了しますか？"):
            self.stop_all_apps()
            self.root.destroy()

def main():
    # 現在のディレクトリをスクリプトがあるディレクトリに変更
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # ロード画面を表示
    show_loading_screen()
    
    # メインアプリケーションを起動
    root = tk.Tk()
    app = WASIManager(root)
    root.mainloop()

def show_loading_screen():
    """ロード画面を表示"""
    loading_root = tk.Tk()
    loading_root.title("WASI - Loading...")
    loading_root.geometry("600x400")
    loading_root.resizable(False, False)
    
    # 画面中央に配置
    loading_root.eval('tk::PlaceWindow . center')
    
    # 背景色を設定
    loading_root.configure(bg='white')
    
    # メインフレーム
    main_frame = tk.Frame(loading_root, bg='white')
    main_frame.pack(expand=True, fill='both')
    
    # ロゴ画像を表示
    try:
        if os.path.exists('icon/logo.png'):
            logo_image = Image.open('icon/logo.png')
            logo_image = logo_image.resize((150, 150), Image.Resampling.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(main_frame, image=logo_photo, bg='white')
            logo_label.pack(pady=(50, 20))
            # 参照を保持
            logo_label.image = logo_photo
    except Exception as e:
        print(f"ロゴ読み込みエラー: {e}")
        # ロゴがない場合はテキストで代替
        logo_label = tk.Label(main_frame, text="🔬", font=("Arial", 80), bg='white')
        logo_label.pack(pady=(50, 20))
    
    # タイトル
    title_label = tk.Label(main_frame, text="Wafer-line Analysis SImulation", 
                          font=("Arial", 20, "bold"), fg="black", bg='white')
    title_label.pack(pady=(10, 5))
    
    wasi_label = tk.Label(main_frame, text="WASI", 
                         font=("Arial", 28, "bold"), fg="red", bg='white')
    wasi_label.pack(pady=(0, 30))
    
    # プログレスバー
    progress_frame = tk.Frame(main_frame, bg='white')
    progress_frame.pack(pady=20)
    
    progress = ttk.Progressbar(progress_frame, length=300, mode='determinate')
    progress.pack()
    
    status_label = tk.Label(progress_frame, text="システムを初期化中...", 
                           font=("Arial", 10), fg="gray", bg='white')
    status_label.pack(pady=(10, 0))
    
    # プログレスバーのアニメーション
    def update_progress():
        messages = [
            "システムを初期化中...",
            "コンポーネントを読み込み中...",
            "データベースに接続中...",
            "インターフェースを準備中...",
            "準備完了"
        ]
        
        for i in range(101):
            progress['value'] = i
            if i < 20:
                status_label.config(text=messages[0])
            elif i < 40:
                status_label.config(text=messages[1])
            elif i < 60:
                status_label.config(text=messages[2])
            elif i < 80:
                status_label.config(text=messages[3])
            else:
                status_label.config(text=messages[4])
            
            loading_root.update_idletasks()  # update_idletasksに変更
            time.sleep(0.03)  # 3秒間のアニメーション (0.03 * 100 = 3秒)
        
        # ロード画面を閉じる
        loading_root.destroy()
    
    # ロード画面表示後、プログレスバーを開始
    loading_root.after(100, update_progress)  # 100msに短縮
    loading_root.mainloop()

if __name__ == "__main__":
    main()
