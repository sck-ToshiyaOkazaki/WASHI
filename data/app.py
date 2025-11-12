import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date
import traceback

st.set_page_config(
    page_title="データ読み込み - DB管理システム",
    page_icon="📊",
    layout="wide"
)

# セッション状態の初期化
if 'file_upload_error' not in st.session_state:
    st.session_state.file_upload_error = None

# データベースパス
DB_PATH = "./load/SONY.db"

def safe_read_csv(uploaded_file):
    """安全にCSVファイルを読み込む"""
    try:
        # ファイルを一度バイト形式で読み込む
        if uploaded_file is not None:
            file_content = uploaded_file.read()
            
            # ファイルポインタを先頭に戻す
            uploaded_file.seek(0)
            
            # pandasでCSVを読み込み
            df = pd.read_csv(uploaded_file)
            
            return df, None
    except UnicodeDecodeError:
        try:
            # エンコーディングエラーの場合、異なるエンコーディングを試す
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='shift_jis')
            return df, None
        except Exception as e:
            return None, f"エンコーディングエラー: {str(e)}"
    except Exception as e:
        return None, f"ファイル読み込みエラー: {str(e)}"

def init_database():
    """データベースを初期化"""
    # 絶対パスで確実にデータベースを作成
    db_dir = os.path.abspath(os.path.dirname(DB_PATH))
    db_file = os.path.abspath(DB_PATH)
    
    # ディレクトリ作成
    os.makedirs(db_dir, exist_ok=True)
    
    # データベースファイル作成
    conn = sqlite3.connect(db_file)
    conn.close()
    
    # 作成確認のためのデバッグ情報
    if os.path.exists(db_file):
        st.info(f"✅ データベースが作成されました: {db_file}")
    else:
        st.error(f"❌ データベースの作成に失敗: {db_file}")
    
    return db_file

def create_indexes_for_log_table():
    """LOGテーブルにインデックスを作成"""
    try:
        db_file = os.path.abspath(DB_PATH)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # インデックス作成（存在しない場合のみ）
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_log_sub_lot_type ON LOG(SUB_LOT_TYPE)",
            "CREATE INDEX IF NOT EXISTS idx_log_lot_id ON LOG(LOT_ID)", 
            "CREATE INDEX IF NOT EXISTS idx_log_eqp_id ON LOG(EQP_ID)",
            "CREATE INDEX IF NOT EXISTS idx_log_stime ON LOG(STIME)",
            "CREATE INDEX IF NOT EXISTS idx_log_prod_grp_id ON LOG(PROD_GRP_ID)",
            "CREATE INDEX IF NOT EXISTS idx_log_prod_type ON LOG(PROD_TYPE)",
            "CREATE INDEX IF NOT EXISTS idx_log_ope_no ON LOG(OPE_NO)",
            "CREATE INDEX IF NOT EXISTS idx_log_run_time ON LOG(RUN_TIME)",
            "CREATE INDEX IF NOT EXISTS idx_log_wait_time ON LOG(WAIT_TIME)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"インデックス作成エラー: {str(e)}")
        return False

def save_data_to_db(df, table_name, replace=True):
    """データをSQLiteに保存"""
    try:
        db_file = os.path.abspath(DB_PATH)
        print(f"[DEBUG] データ保存開始: テーブル={table_name}, DB={db_file}")
        print(f"[DEBUG] データサイズ: {len(df)}行, {len(df.columns)}列")
        
        conn = sqlite3.connect(db_file)
        
        if replace:
            # 既存テーブルを削除して新規作成
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"[DEBUG] テーブル {table_name} を置換保存しました")
        else:
            # データを追加
            df.to_sql(table_name, conn, if_exists='append', index=False)
            print(f"[DEBUG] テーブル {table_name} にデータを追加しました")
        
        conn.close()
        
        # 保存確認
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        
        print(f"[DEBUG] 保存確認: テーブル {table_name} に {count} 行のデータ")
        st.success(f"✅ データベース保存成功: {table_name} ({count}行)")
        
        return True
    except Exception as e:
        error_msg = f"データ保存エラー: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        st.error(error_msg)
        return False

def get_existing_tables():
    """既存のテーブル一覧を取得"""
    try:
        db_file = os.path.abspath(DB_PATH)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        st.error(f"テーブル取得エラー: {str(e)}")
        return []

def delete_tables(table_names):
    """指定されたテーブルを削除"""
    try:
        db_file = os.path.abspath(DB_PATH)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        for table_name in table_names:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"テーブル削除エラー: {str(e)}")
        return False

def get_table_info(table_name):
    """テーブルの情報を取得"""
    try:
        db_file = os.path.abspath(DB_PATH)
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query(f"SELECT COUNT(*) as row_count FROM {table_name}", conn)
        row_count = df.iloc[0]['row_count']
        
        # カラム情報を取得
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        col_count = len(columns)
        
        conn.close()
        return row_count, col_count
    except Exception as e:
        return 0, 0

# アプリケーション開始
st.title("📊 データ読み込み - DB管理システム")

# エラー状態の表示
if st.session_state.get('file_upload_error'):
    st.error(f"⚠️ ファイルアップロードエラー: {st.session_state.file_upload_error}")
    st.info("💡 解決方法: ブラウザを更新するか、ファイルサイズを小さくしてお試しください")
    if st.button("エラーをクリア"):
        st.session_state.file_upload_error = None
        st.rerun()

st.markdown("---")

# データベース初期化
init_database()

# 機能1: データ読み込みとDB格納
st.header("🔄データ読み込みとDB格納")

# タブで7種類のデータを分離
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "品質基準表", "同時着工数", "制約時間", "処理実績", "投入計画", "合同フロー", "レイアウト"
])

with tab1:
    st.subheader("品質基準表の読み込み")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "品質基準表のCSVファイルを選択してください",
            type=['csv'],
            key="flowinfo"
        )
    
    with col2:
        selected_date = st.date_input(
            "年月日を選択してください",
            value=date.today(),
            key="flowinfo_date"
        )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_flowinfo")
        
        if load_data or "flowinfo_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.flowinfo_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "flowinfo_df" in st.session_state:
                    df = st.session_state.flowinfo_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 品質基準表をDBに保存", key="save_flowinfo"):
                            date_str = selected_date.strftime("%Y%m%d")
                            table_name = f"FlowInfo_{date_str}"
                            
                            if save_data_to_db(df, table_name, replace=True):
                                st.success(f"✅ テーブル '{table_name}' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab2:
    st.subheader("同時着工数の読み込み")
    
    uploaded_file = st.file_uploader(
        "同時着工数のCSVファイルを選択してください",
        type=['csv'],
        key="eqp_batch"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_eqp_batch")
        
        if load_data or "eqp_batch_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.eqp_batch_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "eqp_batch_df" in st.session_state:
                    df = st.session_state.eqp_batch_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 同時着工数をDBに保存", key="save_eqp_batch"):
                            if save_data_to_db(df, "eqp_batch", replace=True):
                                st.success("✅ テーブル 'eqp_batch' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab3:
    st.subheader("制約時間の読み込み")
    
    uploaded_file = st.file_uploader(
        "制約時間のCSVファイルを選択してください",
        type=['csv'],
        key="qtime"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_qtime")
        
        if load_data or "qtime_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.qtime_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "qtime_df" in st.session_state:
                    df = st.session_state.qtime_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 制約時間をDBに保存", key="save_qtime"):
                            if save_data_to_db(df, "Qtime", replace=True):
                                st.success("✅ テーブル 'Qtime' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab4:
    st.subheader("処理実績の読み込み")
    
    uploaded_file = st.file_uploader(
        "処理実績のCSVファイルを選択してください",
        type=['csv'],
        key="log"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_log")
        
        if load_data or "log_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.log_df = df
                        
                        # インデックス対象カラムの確認
                        required_columns = [
                            'SUB_LOT_TYPE', 'LOT_ID', 'EQP_ID', 'STIME', 
                            'PROD_GRP_ID', 'PROD_TYPE', 'OPE_NO', 'RUN_TIME', 'WAIT_TIME'
                        ]
                        existing_columns = [col for col in required_columns if col in df.columns]
                        st.session_state.log_index_columns = existing_columns
                        
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "log_df" in st.session_state:
                    df = st.session_state.log_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    if hasattr(st.session_state, 'log_index_columns') and st.session_state.log_index_columns:
                        st.info(f"インデックス対象カラム: {', '.join(st.session_state.log_index_columns)}")
                    
                    with col2:
                        if st.button("💾 処理実績をDBに保存", key="save_log"):
                            if save_data_to_db(df, "LOG", replace=True):
                                # インデックス作成
                                if create_indexes_for_log_table():
                                    st.success("✅ テーブル 'LOG' に保存し、インデックスを作成しました")
                                else:
                                    st.success("✅ テーブル 'LOG' に保存しました（インデックス作成は失敗）")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab5:
    st.subheader("投入計画の読み込み")
    
    uploaded_file = st.file_uploader(
        "投入計画のCSVファイルを選択してください",
        type=['csv'],
        key="plan"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_plan")
        
        if load_data or "plan_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.plan_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "plan_df" in st.session_state:
                    df = st.session_state.plan_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 投入計画をDBに保存", key="save_plan"):
                            if save_data_to_db(df, "plan", replace=True):
                                st.success("✅ テーブル 'plan' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab6:
    st.subheader("合同フローの読み込み")
    
    uploaded_file = st.file_uploader(
        "合同フローのCSVファイルを選択してください",
        type=['csv'],
        key="uflow"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_uflow")
        
        if load_data or "uflow_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.uflow_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "uflow_df" in st.session_state:
                    df = st.session_state.uflow_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 合同フローをDBに保存", key="save_uflow"):
                            if save_data_to_db(df, "uflow", replace=True):
                                st.success("✅ テーブル 'uflow' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

with tab7:
    st.subheader("レイアウトの読み込み")
    
    uploaded_file = st.file_uploader(
        "レイアウトのCSVファイルを選択してください",
        type=['csv'],
        key="layout"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            load_data = st.button("📂 ファイルを読み込み", key="load_layout")
        
        if load_data or "layout_df" in st.session_state:
            try:
                if load_data:
                    df, error = safe_read_csv(uploaded_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.layout_df = df
                        st.success(f"✅ データを読み込みました（{len(df)}行, {len(df.columns)}列）")
                
                if "layout_df" in st.session_state:
                    df = st.session_state.layout_df
                    st.dataframe(df.head(), use_container_width=True)
                    
                    with col2:
                        if st.button("💾 レイアウトをDBに保存", key="save_layout"):
                            if save_data_to_db(df, "layout", replace=True):
                                st.success("✅ テーブル 'layout' に保存しました")
                                st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                st.error("ブラウザを更新して再度お試しください")

# 機能2: テーブル削除機能
st.markdown("---")
st.header("🗑️DBテーブル管理")

# テーブル一覧の更新ボタン
col1, col2 = st.columns([1, 4])
with col1:
    refresh_tables = st.button("🔄 テーブル一覧を更新", key="refresh_tables")

# 既存テーブル一覧を取得
if refresh_tables or "existing_tables" not in st.session_state:
    st.session_state.existing_tables = get_existing_tables()

existing_tables = st.session_state.existing_tables

if existing_tables:
    st.subheader("既存テーブル一覧")
    
    # テーブル情報を表示
    table_info = []
    for table in existing_tables:
        row_count, col_count = get_table_info(table)
        table_info.append({
            "テーブル名": table,
            "データ行数": row_count,
            "カラム数": col_count
        })
    
    df_tables = pd.DataFrame(table_info)
    st.dataframe(df_tables, use_container_width=True)
    
    # テーブル削除機能
    st.subheader("テーブル削除")
    selected_tables = st.multiselect(
        "削除するテーブルを選択してください",
        existing_tables
    )
    
    if selected_tables:
        if st.button("🗑️ 選択したテーブルを削除", type="secondary"):
            if delete_tables(selected_tables):
                st.success(f"✅ {len(selected_tables)}個のテーブルを削除しました")
                # テーブル一覧を更新
                st.session_state.existing_tables = get_existing_tables()
                st.rerun()
            else:
                st.error("❌ テーブル削除に失敗しました")
else:
    st.info("📋 現在データベースにテーブルは存在しません")

# データベース情報
st.markdown("---")
st.subheader("📋 データベース情報")
col1, col2 = st.columns(2)

db_file = os.path.abspath(DB_PATH)

with col1:
    st.metric("データベースパス", db_file)

with col2:
    if os.path.exists(db_file):
        file_size = os.path.getsize(db_file)
        st.metric("ファイルサイズ", f"{file_size:,} bytes")
    else:
        st.metric("ファイルサイズ", "0 bytes (未作成)")

# フッター
st.markdown("---")
st.markdown("**SONY DB管理システム** | データの読み込み・保存・管理")
