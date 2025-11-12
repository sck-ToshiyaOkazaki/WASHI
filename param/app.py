import streamlit as st
import os
import pickle
import sys

# ページ設定
st.set_page_config(
    page_title="パラメータ推定",
    page_icon="🔧",
    layout="wide"
)

def main():
    st.title("🔧 パラメータ推定")
    st.markdown("---")
    
    # セッション状態の初期化
    if 'file_selected' not in st.session_state:
        st.session_state.file_selected = False
    if 'file_path' not in st.session_state:
        st.session_state.file_path = ""
    
    # データ指定ステップ
    st.header("📁 データ指定")
    
    # loadフォルダのパス
    load_folder = "./load"
    
    # loadフォルダ内のファイル一覧を取得
    if os.path.exists(load_folder):
        files = [f for f in os.listdir(load_folder) if os.path.isfile(os.path.join(load_folder, f))]
        
        if files:
            # デフォルトファイルの設定（SONY.dbが存在する場合）
            default_index = 0
            if "SONY.db" in files:
                default_index = files.index("SONY.db")
            
            # ファイル選択
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_file = st.selectbox(
                    "loadフォルダ内のファイルを選択:",
                    files,
                    index=default_index,
                    key="file_selector"
                )
            
            with col2:
                if st.button("📂 ファイル設定", type="primary"):
                    st.session_state.file_path = os.path.join(load_folder, selected_file)
                    st.session_state.file_selected = True
                    st.success(f"ファイルが設定されました: {selected_file}")
                    st.rerun()
            
            # 選択されたファイルの表示
            if st.session_state.file_selected and st.session_state.file_path:
                st.info(f"📄 選択されたファイル: {os.path.basename(st.session_state.file_path)}")
                st.code(f"ファイルパス: {st.session_state.file_path}")
    
    st.markdown("---")
    
    # パラメータ推定ステップ
    st.header("🔬 パラメータ推定ステップ")
    
    if st.session_state.file_selected and st.session_state.file_path:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("ファイルが設定されています。パラメータ推定を実行できます。")
        
        with col2:
            if st.button("🚀 パラメータ推定", type="primary"):
                try:
                    # プログレスバーの表示
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("パラメータ推定モジュールをインポート中...")
                    progress_bar.progress(20)
                    
                    # param_encモジュールのインポート
                    try:
                        import param_enc
                        status_text.text("パラメータ推定を実行中...")
                        progress_bar.progress(50)
                        
                        # パラメータ推定の実行
                        parameter = param_enc.param_estimate(st.session_state.file_path)
                        
                        status_text.text("結果を保存中...")
                        progress_bar.progress(80)
                        
                        # 結果をloadフォルダに保存
                        output_path = os.path.join(load_folder, "parameter.pkl")
                        with open(output_path, 'wb') as f:
                            pickle.dump(parameter, f)
                        
                        progress_bar.progress(100)
                        status_text.text("完了!")
                        
                        st.success("✅ パラメータ推定が正常に完了しました！")
                        st.info(f"📁 結果は以下に保存されました: {output_path}")
                        
                        # 結果の簡単な表示（可能な場合）
                        if hasattr(parameter, '__len__') and len(parameter) > 0:
                            st.write("**推定されたパラメータの概要:**")
                            if isinstance(parameter, dict):
                                st.json(parameter)
                            elif hasattr(parameter, 'shape'):
                                st.write(f"- 形状: {parameter.shape}")
                                st.write(f"- データ型: {type(parameter).__name__}")
                            else:
                                st.write(f"- データ型: {type(parameter).__name__}")
                                st.write(f"- 値: {str(parameter)[:200]}...")
                    
                    except ImportError as e:
                        st.error(f"❌ param_encモジュールのインポートに失敗しました: {str(e)}")
                        st.info("param_enc.pyまたはparam_enc.pydファイルがpythonパスに存在することを確認してください。")
                    
                    except Exception as e:
                        st.error(f"❌ パラメータ推定中にエラーが発生しました: {str(e)}")
                        st.info("詳細なエラー情報:")
                        st.code(f"エラータイプ: {type(e).__name__}\nエラーメッセージ: {str(e)}")
                
                except Exception as e:
                    st.error(f"❌ 予期しないエラーが発生しました: {str(e)}")
    else:
        st.warning("⚠️ まず「データ指定ステップ」でファイルを設定してください。")
    
    # サイドバーに情報表示
    with st.sidebar:
        st.header("📋 アプリ情報")
        st.info("""
        **使用方法:**
        1. loadフォルダからファイルを選択
        2. 「ファイル設定」ボタンをクリック
        3. 「パラメータ推定」ボタンをクリック
        
        **出力:**
        - parameter.pkl (loadフォルダに保存)
        """)
        
        if st.session_state.file_selected:
            st.success("✅ ファイル設定済み")
        else:
            st.warning("⚠️ ファイル未設定")
        
        # システム情報
        st.markdown("---")
        st.subheader("🔧 システム情報")
        st.write(f"Python: {sys.version.split()[0]}")
        st.write(f"Streamlit: {st.__version__}")
        
        # loadフォルダの内容表示
        st.markdown("---")
        st.subheader("📂 loadフォルダの内容")
        if os.path.exists(load_folder):
            files = os.listdir(load_folder)
            if files:
                for file in sorted(files):
                    file_path = os.path.join(load_folder, file)
                    file_size = os.path.getsize(file_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024*1024:
                        size_str = f"{file_size/1024:.1f} KB"
                    else:
                        size_str = f"{file_size/(1024*1024):.1f} MB"
                    st.write(f"📄 {file} ({size_str})")
            else:
                st.write("フォルダが空です")
        else:
            st.write("フォルダが見つかりません")

if __name__ == "__main__":
    main()
