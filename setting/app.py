import streamlit as st
import sqlite3
import pandas as pd
import re
from typing import Dict, List, Tuple, Set

# データベース接続
def get_db_connection():
    return sqlite3.connect('./load/SONY.db')

# FlowInfoテーブル一覧を取得
def get_flowinfo_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'FlowInfo_%'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sorted(tables, reverse=True)  # 最新のテーブルが先頭になるようにソート

# データを読み込み、前処理を実行
@st.cache_data
def load_and_preprocess_data(table_name: str):
    conn = get_db_connection()
    
    # 必要なカラムのみ読み込み
    query = f"""
    SELECT TYPE, OPE_NO, EQP_GRP_CONV, ALL_EQP_ID, INHIBIT_EQP_ID, EQP_ID 
    FROM {table_name}
    WHERE TYPE IS NOT NULL AND OPE_NO IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 1. 全設備とそれに紐づくTYPE、OPE_NO情報の作成
    equipment_mapping = {}
    
    for _, row in df.iterrows():
        type_val = row['TYPE']
        ope_no = row['OPE_NO']
        all_eqp = row['ALL_EQP_ID'] if pd.notna(row['ALL_EQP_ID']) else ""
        
        # スペース区切りで設備を分割
        equipment_list = all_eqp.split() if all_eqp else []
        
        for equipment in equipment_list:
            if equipment not in equipment_mapping:
                equipment_mapping[equipment] = []
            equipment_mapping[equipment].append({
                'TYPE': type_val,
                'OPE_NO': ope_no,
                'EQP_GRP_CONV': row['EQP_GRP_CONV'],
                'INHIBIT_EQP_ID': row['INHIBIT_EQP_ID'] if pd.notna(row['INHIBIT_EQP_ID']) else "",
                'EQP_ID': row['EQP_ID'] if pd.notna(row['EQP_ID']) else ""
            })
    
    # 2. EQP_GRP_CONVに紐づくALL_EQP_ID情報の作成
    group_equipment_mapping = {}
    for _, row in df.iterrows():
        group_name = row['EQP_GRP_CONV']
        all_eqp = row['ALL_EQP_ID'] if pd.notna(row['ALL_EQP_ID']) else ""
        equipment_list = all_eqp.split() if all_eqp else []
        
        if group_name not in group_equipment_mapping:
            group_equipment_mapping[group_name] = set()
        group_equipment_mapping[group_name].update(equipment_list)
    
    # 3. 各TYPE、OPE_NOにおける設備の使用状況情報の作成
    equipment_usage = {}
    for _, row in df.iterrows():
        type_val = row['TYPE']
        ope_no = row['OPE_NO']
        inhibit_eqp = row['INHIBIT_EQP_ID'] if pd.notna(row['INHIBIT_EQP_ID']) else ""
        inhibit_list = inhibit_eqp.split() if inhibit_eqp else []
        
        key = (type_val, ope_no)
        if key not in equipment_usage:
            equipment_usage[key] = set(inhibit_list)
    
    return equipment_mapping, group_equipment_mapping, equipment_usage, df

# メイン関数
def main():
    st.title("装置汎用化設定")
    
    # テーブル選択
    tables = get_flowinfo_tables()
    if not tables:
        st.error("FlowInfoテーブルが見つかりません")
        return
    
    selected_table = st.selectbox("使用するFlowInfoテーブルを選択してください", tables)
    
    # データの読み込み
    equipment_mapping, group_equipment_mapping, equipment_usage, df = load_and_preprocess_data(selected_table)
    
    # セッション状態の初期化
    if 'selected_equipment' not in st.session_state:
        st.session_state.selected_equipment = None
    if 'equipment_data' not in st.session_state:
        st.session_state.equipment_data = []
    if 'new_records' not in st.session_state:
        st.session_state.new_records = []
    
    # 新規設備か既存設備かの選択
    equipment_type = st.radio("設備タイプを選択してください", ["新規設備", "既存設備"])
    
    # 設備グループの選択
    available_groups = sorted(list(group_equipment_mapping.keys()))
    selected_group = st.selectbox("設備グループを選択してください", available_groups)
    
    if selected_group:
        # 選択された設備グループに紐づく設備の表示
        group_equipment = sorted(list(group_equipment_mapping[selected_group]))
        
        # 設備名でのフィルタ
        filter_text = st.text_input("設備名でフィルタ", "")
        if filter_text:
            group_equipment = [eq for eq in group_equipment if filter_text in eq]
        
        # 設備一覧を表形式で表示
        if group_equipment:
            st.subheader("設備一覧")
            
            equipment_data = []
            for equipment in group_equipment:
                equipment_data.append({
                    "設備名": equipment,
                    "Fab": 1,
                    "Bay": 1
                })
            
            equipment_df = pd.DataFrame(equipment_data)
            
            # データフレームを表示し、選択された行を取得
            for idx, row in equipment_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(row['設備名'])
                with col2:
                    st.write(row['Fab'])
                with col3:
                    st.write(row['Bay'])
                with col4:
                    if st.button(f"コピー", key=f"copy_{idx}"):
                        st.session_state.selected_equipment = row['設備名']
                        # 選択された設備のデータを準備
                        if row['設備名'] in equipment_mapping:
                            equipment_details = []
                            for detail in equipment_mapping[row['設備名']]:
                                # INHIBITの判定
                                key = (detail['TYPE'], detail['OPE_NO'])
                                inhibit_equipment = equipment_usage.get(key, set())
                                is_inhibited = row['設備名'] in inhibit_equipment
                                
                                equipment_details.append({
                                    '設備名': row['設備名'],
                                    'TYPE': detail['TYPE'],
                                    'OPE_NO': detail['OPE_NO'],
                                    'INHIBIT': is_inhibited
                                })
                            st.session_state.equipment_data = equipment_details
                        st.session_state.new_records = []
        
        # 選択された設備の詳細表示
        if st.session_state.selected_equipment:
            st.subheader(f"選択された設備: {st.session_state.selected_equipment}")
            
            # 既存レコードの表示・編集
            if st.session_state.equipment_data:
                st.write("**既存レコード:**")
                
                # フィルタリングオプション
                st.write("**フィルタ設定:**")
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    # TYPEフィルタ
                    available_types_in_records = sorted(list(set([record['TYPE'] for record in st.session_state.equipment_data])))
                    selected_type_filter = st.selectbox(
                        "TYPE フィルタ", 
                        ["すべて"] + available_types_in_records, 
                        key="type_filter"
                    )
                
                with filter_col2:
                    # OPE_NOフィルタ
                    available_ope_nos_in_records = sorted(list(set([record['OPE_NO'] for record in st.session_state.equipment_data])))
                    selected_ope_no_filter = st.selectbox(
                        "OPE_NO フィルタ", 
                        ["すべて"] + available_ope_nos_in_records, 
                        key="ope_no_filter"
                    )
                
                with filter_col3:
                    # INHIBITフィルタ
                    selected_inhibit_filter = st.selectbox(
                        "INHIBIT フィルタ", 
                        ["すべて", "有効 (True)", "無効 (False)"], 
                        key="inhibit_filter"
                    )
                
                # フィルタリング実行
                filtered_records = []
                for idx, record in enumerate(st.session_state.equipment_data):
                    # TYPEフィルタ
                    if selected_type_filter != "すべて" and record['TYPE'] != selected_type_filter:
                        continue
                    
                    # OPE_NOフィルタ
                    if selected_ope_no_filter != "すべて" and record['OPE_NO'] != selected_ope_no_filter:
                        continue
                    
                    # INHIBITフィルタ
                    if selected_inhibit_filter == "有効 (True)" and not record['INHIBIT']:
                        continue
                    elif selected_inhibit_filter == "無効 (False)" and record['INHIBIT']:
                        continue
                    
                    filtered_records.append((idx, record))
                
                # フィルタリング結果表示
                st.write(f"**表示中: {len(filtered_records)} / {len(st.session_state.equipment_data)} レコード**")
                
                for original_idx, record in filtered_records:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    
                    with col1:
                        st.write(record['設備名'])
                    with col2:
                        st.write(record['TYPE'])
                    with col3:
                        st.write(record['OPE_NO'])
                    with col4:
                        # INHIBITチェックボックス
                        new_inhibit = st.checkbox(
                            "INHIBIT", 
                            value=record['INHIBIT'], 
                            key=f"inhibit_{original_idx}"
                        )
                        st.session_state.equipment_data[original_idx]['INHIBIT'] = new_inhibit
            
            # 新規レコード追加セクション
            st.write("**新規レコード追加:**")
            
            # 品質基準表掲載ありチェックボックス
            quality_standard_filter = st.checkbox("品質基準表掲載あり", key="quality_standard_filter")
            
            # TYPE と OPE_NO の選択肢を取得
            if quality_standard_filter:
                # 選択された設備グループに関連するTYPE、OPE_NOのみを取得
                group_related_df = df[df['EQP_GRP_CONV'] == selected_group]
                available_types = sorted(group_related_df['TYPE'].unique())
                available_ope_nos = sorted(group_related_df['OPE_NO'].unique())
            else:
                # 全てのTYPE、OPE_NOを取得
                available_types = sorted(df['TYPE'].unique())
                available_ope_nos = sorted(df['OPE_NO'].unique())
            
            col1, col2 = st.columns(2)
            with col1:
                new_type = st.selectbox("TYPE", available_types, key="new_type")
            with col2:
                # TYPEが選択されたら、そのTYPEに関連するOPE_NOのみを表示
                if quality_standard_filter:
                    # 品質基準表フィルタがオンの場合、選択されたグループ内でのみフィルタ
                    filtered_ope_nos = sorted(group_related_df[group_related_df['TYPE'] == new_type]['OPE_NO'].unique()) if new_type else available_ope_nos
                else:
                    # 通常のフィルタ
                    filtered_ope_nos = sorted(df[df['TYPE'] == new_type]['OPE_NO'].unique()) if new_type else available_ope_nos
                new_ope_no = st.selectbox("OPE_NO", filtered_ope_nos, key="new_ope_no")
            
            # INHIBIT選択とコピー元情報
            if new_type and new_ope_no:
                col1, col2 = st.columns(2)
                with col1:
                    new_inhibit = st.selectbox("INHIBIT", [0, 1], key="new_inhibit")
                with col2:
                    st.write("コピー元設備情報: New")
                
                if st.button("レコード追加"):
                    new_record = {
                        '設備名': st.session_state.selected_equipment,
                        'TYPE': new_type,
                        'OPE_NO': new_ope_no,
                        'INHIBIT': new_inhibit,
                        'コピー元情報': "New"
                    }
                    st.session_state.new_records.append(new_record)
                    st.success("レコードが追加されました")
            
            # 追加された新規レコードの表示
            if st.session_state.new_records:
                st.write("**追加されたレコード:**")
                for idx, record in enumerate(st.session_state.new_records):
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 2])
                    with col1:
                        st.write(record['設備名'])
                    with col2:
                        st.write(record['TYPE'])
                    with col3:
                        st.write(record['OPE_NO'])
                    with col4:
                        st.write(record['INHIBIT'])
                    with col5:
                        st.write(record['コピー元情報'])
            
            # 新規設備の場合は設備名を入力
            final_equipment_name = st.session_state.selected_equipment
            if equipment_type == "新規設備":
                new_equipment_name = st.text_input("新規設備名を入力してください", value="", key="new_equipment_name")
                if new_equipment_name:
                    final_equipment_name = new_equipment_name
            
            # 出力ボタン
            if st.button("出力"):
                if equipment_type == "新規設備" and not final_equipment_name:
                    st.warning("新規設備名を入力してください")
                else:
                    output_data = []
                    
                    # 既存レコードの変更をCSV出力用に準備
                    for record in st.session_state.equipment_data:
                        output_data.append({
                            '設備名': final_equipment_name,
                            '設備グループ': selected_group,
                            'TYPE': record['TYPE'],
                            'OPE_NO': record['OPE_NO'],
                            'INHIBIT': 1 if record['INHIBIT'] else 0
                        })
                    
                    # 新規レコードをCSV出力用に準備
                    for record in st.session_state.new_records:
                        output_data.append({
                            '設備名': final_equipment_name,
                            '設備グループ': selected_group,
                            'TYPE': record['TYPE'],
                            'OPE_NO': record['OPE_NO'],
                            'INHIBIT': record['INHIBIT'],
                            'コピー元情報': record['コピー元情報']
                        })
                    
                    if output_data:
                        # CSV形式で出力
                        output_df = pd.DataFrame(output_data)
                        csv_data = output_df.to_csv(index=False, encoding='utf-8-sig')
                        
                        st.subheader("出力データプレビュー")
                        st.dataframe(output_df)
                        
                        st.download_button(
                            label="CSVファイルをダウンロード",
                            data=csv_data,
                            file_name=f"equipment_data_{final_equipment_name}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("出力するデータがありません。設備を選択してレコードを編集または追加してください。")

if __name__ == "__main__":
    main()
