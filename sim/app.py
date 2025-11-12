import streamlit as st
import os
import pickle
import sys

# ページ設定
st.set_page_config(
    page_title="装置汎用化シミュレーション",
    page_icon="🔬",
    layout="wide"
)

def main():
    st.title("🔬 装置汎用化シミュレーション")
    st.markdown("---")
    
    # セッション状態の初期化
    if 'database_selected' not in st.session_state:
        st.session_state.database_selected = False
    if 'parameter_selected' not in st.session_state:
        st.session_state.parameter_selected = False
    if 'equipment_selected' not in st.session_state:
        st.session_state.equipment_selected = False
    if 'database_path' not in st.session_state:
        st.session_state.database_path = ""
    if 'parameter_path' not in st.session_state:
        st.session_state.parameter_path = ""
    if 'equipment_path' not in st.session_state:
        st.session_state.equipment_path = ""
    
    # データ指定ステップ
    st.header("📁 データ指定ステップ")
    
    # loadフォルダのパス
    load_folder = "./load"
    
    if not os.path.exists(load_folder):
        st.error("loadフォルダが見つかりません。")
        return
    
    # 3つのカラムでデータ種別を分割
    col1, col2, col3 = st.columns(3)
    
    # データベース選択
    with col1:
        st.subheader("🗄️ データベース")
        
        # loadフォルダ内のファイル一覧を取得
        files = [f for f in os.listdir(load_folder) if os.path.isfile(os.path.join(load_folder, f))]
        
        if files:
            # デフォルトファイルの設定（SONY.dbが存在する場合）
            default_index = 0
            if "SONY.db" in files:
                default_index = files.index("SONY.db")
            
            # ファイル選択
            selected_db_file = st.selectbox(
                "データベースファイルを選択:",
                files,
                index=default_index,
                key="db_selector"
            )
            
            # アップロード機能
            uploaded_db_file = st.file_uploader(
                "または新しいファイルをアップロード:",
                type=None,
                key="db_uploader",
                help="loadフォルダにファイルをアップロードします"
            )
            
            if st.button("📂 データベース設定", type="primary", key="db_button"):
                if uploaded_db_file is not None:
                    # アップロードされたファイルを保存
                    upload_path = os.path.join(load_folder, uploaded_db_file.name)
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_db_file.getvalue())
                    st.session_state.database_path = upload_path
                    st.success(f"アップロード完了: {uploaded_db_file.name}")
                else:
                    st.session_state.database_path = os.path.join(load_folder, selected_db_file)
                    st.success(f"データベース設定完了: {selected_db_file}")
                
                st.session_state.database_selected = True
                st.rerun()
            
            if st.session_state.database_selected:
                st.info(f"✅ 設定済み: {os.path.basename(st.session_state.database_path)}")
        else:
            st.warning("loadフォルダ内にファイルが見つかりません。")
    
    # パラメータ選択
    with col2:
        st.subheader("⚙️ パラメータ")
        
        # loadフォルダ内のファイル一覧を取得
        files = [f for f in os.listdir(load_folder) if os.path.isfile(os.path.join(load_folder, f))]
        
        if files:
            # デフォルトファイルの設定（parameter.pklが存在する場合）
            default_index = 0
            if "parameter.pkl" in files:
                default_index = files.index("parameter.pkl")
            
            # ファイル選択
            selected_param_file = st.selectbox(
                "パラメータファイルを選択:",
                files,
                index=default_index,
                key="param_selector"
            )
            
            # アップロード機能
            uploaded_param_file = st.file_uploader(
                "または新しいファイルをアップロード:",
                type=None,
                key="param_uploader",
                help="loadフォルダにファイルをアップロードします"
            )
            
            if st.button("📂 パラメータ設定", type="primary", key="param_button"):
                if uploaded_param_file is not None:
                    # アップロードされたファイルを保存
                    upload_path = os.path.join(load_folder, uploaded_param_file.name)
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_param_file.getvalue())
                    st.session_state.parameter_path = upload_path
                    st.success(f"アップロード完了: {uploaded_param_file.name}")
                else:
                    st.session_state.parameter_path = os.path.join(load_folder, selected_param_file)
                    st.success(f"パラメータ設定完了: {selected_param_file}")
                
                st.session_state.parameter_selected = True
                st.rerun()
            
            if st.session_state.parameter_selected:
                st.info(f"✅ 設定済み: {os.path.basename(st.session_state.parameter_path)}")
        else:
            st.warning("loadフォルダ内にファイルが見つかりません。")
    
    # 装置汎用化設定選択
    with col3:
        st.subheader("🔧 装置汎用化設定")
        
        # loadフォルダ内のファイル一覧を取得
        files = [f for f in os.listdir(load_folder) if os.path.isfile(os.path.join(load_folder, f))]
        
        if files:
            # デフォルトファイルの設定（equipment_data.csvが存在する場合）
            default_index = 0
            if "equipment_data.csv" in files:
                default_index = files.index("equipment_data.csv")
            
            # ファイル選択
            selected_eq_file = st.selectbox(
                "装置設定ファイルを選択:",
                files,
                index=default_index,
                key="eq_selector"
            )
            
            # アップロード機能
            uploaded_eq_file = st.file_uploader(
                "または新しいファイルをアップロード:",
                type=None,
                key="eq_uploader",
                help="loadフォルダにファイルをアップロードします"
            )
            
            if st.button("📂 装置設定", type="primary", key="eq_button"):
                if uploaded_eq_file is not None:
                    # アップロードされたファイルを保存
                    upload_path = os.path.join(load_folder, uploaded_eq_file.name)
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_eq_file.getvalue())
                    st.session_state.equipment_path = upload_path
                    st.success(f"アップロード完了: {uploaded_eq_file.name}")
                else:
                    st.session_state.equipment_path = os.path.join(load_folder, selected_eq_file)
                    st.success(f"装置設定完了: {selected_eq_file}")
                
                st.session_state.equipment_selected = True
                st.rerun()
            
            if st.session_state.equipment_selected:
                st.info(f"✅ 設定済み: {os.path.basename(st.session_state.equipment_path)}")
        else:
            st.warning("loadフォルダ内にファイルが見つかりません。")
    
    st.markdown("---")
    
    # シミュレーションステップ
    st.header("🚀 シミュレーションステップ")
    
    # 全てのデータが設定されているかチェック
    all_data_ready = (
        st.session_state.database_selected and 
        st.session_state.parameter_selected and 
        st.session_state.equipment_selected
    )
    
    if all_data_ready:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("すべてのデータが設定されています。シミュレーションを実行できます。")
            
            # 設定されたファイルの表示
            st.write("**設定されたファイル:**")
            st.write(f"- データベース: `{os.path.basename(st.session_state.database_path)}`")
            st.write(f"- パラメータ: `{os.path.basename(st.session_state.parameter_path)}`")
            st.write(f"- 装置設定: `{os.path.basename(st.session_state.equipment_path)}`")
        
        with col2:
            if st.button("🚀 シミュレーション実行", type="primary", key="sim_button"):
                try:
                    # プログレスバーの表示
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("シミュレーションモジュールをインポート中...")
                    progress_bar.progress(20)
                    
                    # sim_encモジュールのインポート
                    try:
                        import sim_enc
                        status_text.text("シミュレーションを実行中...")
                        progress_bar.progress(50)
                        
                        # シミュレーションの実行
                        simres = sim_enc.sim(
                            st.session_state.database_path,
                            st.session_state.parameter_path,
                            st.session_state.equipment_path
                        )
                        
                        status_text.text("結果を保存中...")
                        progress_bar.progress(80)
                        
                        # 結果をloadフォルダに保存
                        output_path = os.path.join(load_folder, "simres.pkl")
                        with open(output_path, 'wb') as f:
                            pickle.dump(simres, f)
                        
                        progress_bar.progress(100)
                        status_text.text("完了!")
                        
                        st.success("✅ シミュレーションが正常に完了しました！")
                        st.info(f"📁 結果は以下に保存されました: {output_path}")
                        
                        # 結果の簡単な表示（可能な場合）
                        if hasattr(simres, '__len__') and len(simres) > 0:
                            st.write("**シミュレーション結果の概要:**")
                            if isinstance(simres, dict):
                                st.json(simres)
                            elif hasattr(simres, 'shape'):
                                st.write(f"- 形状: {simres.shape}")
                                st.write(f"- データ型: {type(simres).__name__}")
                            else:
                                st.write(f"- データ型: {type(simres).__name__}")
                                st.write(f"- 値: {str(simres)[:200]}...")
                    
                    except ImportError as e:
                        st.error(f"❌ sim_encモジュールのインポートに失敗しました: {str(e)}")
                        st.info("sim_enc.pyまたはsim_enc.pydファイルがpythonパスに存在することを確認してください。")
                    
                    except Exception as e:
                        st.error(f"❌ シミュレーション中にエラーが発生しました: {str(e)}")
                        st.info("詳細なエラー情報:")
                        st.code(f"エラータイプ: {type(e).__name__}\nエラーメッセージ: {str(e)}")
                
                except Exception as e:
                    st.error(f"❌ 予期しないエラーが発生しました: {str(e)}")
    else:
        st.warning("⚠️ シミュレーションを実行するには、すべてのデータを設定してください。")
        
        # 設定状況の表示
        st.write("**設定状況:**")
        st.write(f"- データベース: {'✅' if st.session_state.database_selected else '❌'}")
        st.write(f"- パラメータ: {'✅' if st.session_state.parameter_selected else '❌'}")
        st.write(f"- 装置汎用化設定: {'✅' if st.session_state.equipment_selected else '❌'}")
    
    # サイドバーに情報表示
    with st.sidebar:
        st.header("📋 アプリ情報")
        st.info("""
        **使用方法:**
        1. データベースファイルを選択/アップロード
        2. パラメータファイルを選択/アップロード
        3. 装置汎用化設定ファイルを選択/アップロード
        4. 「シミュレーション実行」ボタンをクリック
        
        **出力:**
        - simres.pkl (loadフォルダに保存)
        """)
        
        # 設定状況の表示
        st.markdown("---")
        st.subheader("📊 設定状況")
        if st.session_state.database_selected:
            st.success("✅ データベース設定済み")
        else:
            st.warning("⚠️ データベース未設定")
            
        if st.session_state.parameter_selected:
            st.success("✅ パラメータ設定済み")
        else:
            st.warning("⚠️ パラメータ未設定")
            
        if st.session_state.equipment_selected:
            st.success("✅ 装置設定済み")
        else:
            st.warning("⚠️ 装置設定未設定")
        
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
