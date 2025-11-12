import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pickle
import numpy as np
from datetime import datetime
import os

# ページ設定
st.set_page_config(
    page_title="製造データ可視化アプリ (装置汎用化後)",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data_from_pickle(file_path):
    """pklファイルからデータを読み込み、前処理を行う"""
    try:
        with open(file_path, 'rb') as f:
            df = pickle.load(f)
        
        # データ型変換
        df['OPE_START_DATETIME'] = pd.to_datetime(df['OPE_START_DATETIME'])
        df['WAIT_TIME'] = pd.to_numeric(df['WAIT_TIME'], errors='coerce')
        
        # 除外するOPE_NO
        excluded_ope_no = [
            "NY_DMY.NY-DMY", "SSATU.1PC-MPC", "SSATU.1PC-MPC2", "SSATU.1PC-WWS",
            "SSATU.2PC-MPC", "SSATU.2PC-MPC2", "SSATU.2PC-MPC3", "SSATU.MOKUSHIT",
            "P_WET.P-YLP", "P_WET.P-WWS", "PASS.CHECK", "NYUUKO.NYUUKO-1",
            "NYUUKO.NYUUKO-2", "NYUUKO.W1-END", "BANK_IN.BANK-IN"
        ]
        
        # データフィルタリング
        df_filtered = df[
            (df['SUB_LOT_TYPE'] == 'P0') & 
            (df['MRC'] == 'MASTER') & 
            (~df['OPE_NO'].isin(excluded_ope_no))
        ].copy()
        
        # 月情報を追加
        df_filtered['年月'] = df_filtered['OPE_START_DATETIME'].dt.to_period('M')
        
        # メモリ最適化
        df_filtered['DeviceGp'] = df_filtered['DeviceGp'].astype('category')
        df_filtered['EQP_ID'] = df_filtered['EQP_ID'].astype('category')
        df_filtered['WAIT_TIME'] = df_filtered['WAIT_TIME'].astype('float32')
        
        return df_filtered
        
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return None

@st.cache_data
def calculate_monthly_stats(df):
    """月ごとの統計情報を事前計算"""
    try:
        # 全DeviceGpでの統計
        all_stats = df.groupby(['年月', 'EQP_ID']).agg({
            'WAIT_TIME': ['mean', lambda x: np.percentile(x, 75)]
        }).round(2)
        all_stats.columns = ['平均待ち時間', '第三四分位点']
        all_stats = all_stats.reset_index()
        all_stats['DeviceGp'] = 'All Devices'
        
        # DeviceGp別の統計
        device_stats = df.groupby(['年月', 'DeviceGp', 'EQP_ID']).agg({
            'WAIT_TIME': ['mean', lambda x: np.percentile(x, 75)]
        }).round(2)
        device_stats.columns = ['平均待ち時間', '第三四分位点']
        device_stats = device_stats.reset_index()
        
        # 統合
        combined_stats = pd.concat([all_stats, device_stats], ignore_index=True)
        
        return combined_stats
        
    except Exception as e:
        st.error(f"統計計算に失敗しました: {e}")
        return None
        
def main():
    st.title("📊 製造データ可視化アプリ (装置汎用化後)")
    st.markdown("---")
    
    # セッション状態の初期化
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    
    # 初期状態の案内メッセージ
    if not st.session_state.data_loaded:
        st.info("🔍 サイドバーからデータファイルを選択してください")
    
    # キャッシュクリア機能をサイドバーに追加
    if st.sidebar.button("🗑️ キャッシュクリア"):
        st.cache_data.clear()
        st.session_state.data_loaded = False
        st.sidebar.success("キャッシュがクリアされました")
        st.rerun()
    
    # ファイル選択
    st.sidebar.header("📁 データファイル選択")
    
    # データの読み込み方法を選択
    data_source = st.sidebar.radio(
        "データの読み込み方法:",
        ["--- 選択してください ---", "フォルダ内のファイル", "ファイルアップロード"]
    )
    
    df = None
    selected_file_info = None
    
    # データ読み込み方法が選択されていない場合は処理を停止
    if data_source == "--- 選択してください ---":
        st.markdown("""
        ### 📋 使用方法
        1. サイドバーの「データの読み込み方法」を選択してください
        2. ファイルを選択またはアップロードしてください
        3. データが読み込まれると可視化が開始されます
        
        ### 📊 このアプリでできること
        - **月ごとランキング表**: 各機器の待ち時間ランキングを表形式で確認
        - **ランキング変化の推移**: 時系列での機器ランキングの変化を折れ線グラフで表示
        - **待ち時間割合の可視化**: 月ごとの機器別待ち時間割合を100%積み上げ棒グラフで表示
        """)
        return
    
    elif data_source == "フォルダ内のファイル":
        # vis_aフォルダ内のpklファイルを取得
        pkl_files = []
        vis_a_path = "./load"
        if os.path.exists(vis_a_path):
            for file in os.listdir(vis_a_path):
                if file.endswith('.pkl'):
                    pkl_files.append(file)
        
        if not pkl_files:
            st.error("loadフォルダ内にpklファイルが見つかりません。")
            return
        
        # デフォルト選択肢として"選択してください"を追加
        file_options = ["--- ファイルを選択してください ---"] + pkl_files
        
        # ファイル選択
        selected_option = st.sidebar.selectbox(
            "読み込むpklファイルを選択:",
            file_options,
            index=0
        )
        
        if selected_option != "--- ファイルを選択してください ---":
            file_path = os.path.join(vis_a_path, selected_option)
            selected_file_info = f"フォルダ内ファイル: {selected_option}"
            
            # データ読み込み
            with st.spinner('データを読み込み中...'):
                df = load_data_from_pickle(file_path)
                if df is not None:
                    st.session_state.data_loaded = True
        else:
            st.info("📁 フォルダ内のpklファイルを選択してください")
            st.markdown(f"""
            **利用可能なファイル:**
            {chr(10).join([f"- {file}" for file in pkl_files])}
            
            **必要な列:**
            - LOT_ID: ロットID
            - OPE_START_DATETIME: 作業開始日時
            - WAIT_TIME: 待ち時間
            - EQP_ID: 機器ID
            - OPE_NO: 作業番号
            - SUB_LOT_TYPE: サブロットタイプ
            - MRC: MRC
            - DeviceGp: デバイスグループ
            """)
            return
                
    elif data_source == "ファイルアップロード":
        # ファイルアップロード機能
        uploaded_file = st.sidebar.file_uploader(
            "pklファイルをアップロード:",
            type=['pkl']
        )
        
        if uploaded_file is not None:
            # 一時ファイルとして保存
            temp_path = f"/tmp/{uploaded_file.name}"
            selected_file_info = f"アップロードファイル: {uploaded_file.name}"
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # データ読み込み
            with st.spinner('アップロードされたデータを読み込み中...'):
                df = load_data_from_pickle(temp_path)
                if df is not None:
                    st.session_state.data_loaded = True
            
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
        else:
            st.info("📤 pklファイルをアップロードしてください")
            st.markdown("""
            **アップロード可能なファイル形式:**
            - `.pkl` (pickle形式)
            """)
            return
    
    if df is None:
        if not st.session_state.data_loaded:
            st.warning("⚠️ データファイルが選択されていません")
        return
    
    # ファイル情報の表示
    if selected_file_info:
        st.success(f"✅ データが正常に読み込まれました: {selected_file_info}")
    
    # データ情報表示
    st.sidebar.markdown("### 📊 データ情報")
    st.sidebar.info(f"""
    - 総レコード数: {len(df):,}件
    - 期間: {df['OPE_START_DATETIME'].min().strftime('%Y-%m-%d')} ～ {df['OPE_START_DATETIME'].max().strftime('%Y-%m-%d')}
    - DeviceGp数: {df['DeviceGp'].nunique()}種類
    - EQP_ID数: {df['EQP_ID'].nunique()}種類
    """)
    
    # データサンプル表示
    with st.expander("📋 データサンプル（先頭5行）"):
        st.dataframe(df.head(), use_container_width=True)
    
    # 統計計算
    with st.spinner('統計情報を計算中...'):
        stats_df = calculate_monthly_stats(df)
    
    if stats_df is None:
        return
    
    # タブ作成
    tab1, tab2, tab3 = st.tabs([
        "📋 月ごとランキング表", 
        "📈 ランキング変化の推移", 
        "📊 待ち時間割合の可視化"
    ])
    
    # タブ1: 月ごとランキング表
    with tab1:
        st.header("📋 月ごとの各機器の待ち時間ランキング表")
        
        # コントロール
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            device_options = ['All Devices'] + sorted(df['DeviceGp'].unique())
            selected_device = st.selectbox(
                "DeviceGp選択:",
                device_options,
                key="tab1_device"
            )
        
        with col2:
            available_months = sorted(stats_df['年月'].unique())
            selected_month = st.selectbox(
                "対象月選択:",
                available_months,
                index=len(available_months)-1,  # 最新月をデフォルト
                key="tab1_month"
            )
        
        with col3:
            display_count = st.slider(
                "表示件数:",
                min_value=5,
                max_value=50,
                value=25,
                step=5,
                key="tab1_count"
            )
        
        # データフィルタリングとランキング作成
        filtered_stats = stats_df[
            (stats_df['DeviceGp'] == selected_device) & 
            (stats_df['年月'] == selected_month)
        ].copy()
        
        if not filtered_stats.empty:
            # 第三四分位点でソート（降順）
            filtered_stats = filtered_stats.sort_values('第三四分位点', ascending=False)
            filtered_stats['順位'] = range(1, len(filtered_stats) + 1)
            
            # 表示用データ準備
            display_data = filtered_stats.head(display_count)[
                ['順位', 'EQP_ID', '第三四分位点', '平均待ち時間']
            ].copy()
            
            st.subheader(f"🏆 {selected_device} - {selected_month} のランキング")
            st.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True
            )
            
            # 簡単な統計情報
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("1位機器", display_data.iloc[0]['EQP_ID'])
            with col2:
                st.metric("1位待ち時間(Q3)", f"{display_data.iloc[0]['第三四分位点']:.1f}時間")
            with col3:
                st.metric("総機器数", len(filtered_stats))
        else:
            st.warning("選択された条件に該当するデータがありません。")
    
    # タブ2: ランキング変化の推移
    with tab2:
        st.header("📈 月ごとの各機器の待ち時間ランキング変化")
        
        # コントロール
        col1, col2 = st.columns([2, 1])
        
        with col1:
            device_options = ['All Devices'] + sorted(df['DeviceGp'].unique())
            selected_device_tab2 = st.selectbox(
                "DeviceGp選択:",
                device_options,
                key="tab2_device"
            )
        
        with col2:
            display_count_tab2 = st.slider(
                "表示機器数:",
                min_value=5,
                max_value=50,
                value=25,
                step=5,
                key="tab2_count"
            )
        
        # データ準備
        device_stats = stats_df[stats_df['DeviceGp'] == selected_device_tab2].copy()
        
        if not device_stats.empty:
            # 各月でランキング計算
            monthly_rankings = []
            for month in sorted(device_stats['年月'].unique()):
                month_data = device_stats[device_stats['年月'] == month].copy()
                month_data = month_data.sort_values('第三四分位点', ascending=False)
                month_data['順位'] = range(1, len(month_data) + 1)
                month_data['年月_str'] = str(month)
                monthly_rankings.append(month_data)
            
            if monthly_rankings:
                ranking_df = pd.concat(monthly_rankings, ignore_index=True)
                
                # 上位機器を特定（最新月基準）
                latest_month = max(ranking_df['年月'])
                top_equipment = ranking_df[
                    ranking_df['年月'] == latest_month
                ].head(display_count_tab2)['EQP_ID'].tolist()
                
                # グラフ作成
                fig = go.Figure()
                
                colors = px.colors.qualitative.Set3
                for i, eqp in enumerate(top_equipment):
                    eqp_data = ranking_df[ranking_df['EQP_ID'] == eqp]
                    if not eqp_data.empty:
                        fig.add_trace(go.Scatter(
                            x=eqp_data['年月_str'],
                            y=eqp_data['順位'],
                            mode='lines+markers',
                            name=eqp,
                            line=dict(color=colors[i % len(colors)], width=2),
                            marker=dict(size=6)
                        ))
                
                fig.update_layout(
                    title=f"{selected_device_tab2} - 機器別ランキング推移",
                    xaxis_title="月",
                    yaxis_title="順位",
                    yaxis=dict(autorange='reversed'),  # Y軸を反転（1位が上）
                    height=600,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 情報表示
                st.info(f"表示期間: {min(ranking_df['年月_str'])} ～ {max(ranking_df['年月_str'])}")
            else:
                st.warning("ランキングデータの作成に失敗しました。")
        else:
            st.warning("選択されたDeviceGpのデータが見つかりません。")
    
    # タブ3: 待ち時間割合の可視化
    with tab3:
        st.header("📊 月ごとの各機器の待ち時間割合の可視化")
        
        # コントロール
        col1, col2 = st.columns([2, 1])
        
        with col1:
            device_options = ['All Devices'] + sorted(df['DeviceGp'].unique())
            selected_device_tab3 = st.selectbox(
                "DeviceGp選択:",
                device_options,
                key="tab3_device"
            )
        
        with col2:
            display_count_tab3 = st.slider(
                "表示機器数:",
                min_value=5,
                max_value=50,
                value=25,
                step=5,
                key="tab3_count"
            )
        
        # データ準備
        device_stats = stats_df[stats_df['DeviceGp'] == selected_device_tab3].copy()
        
        if not device_stats.empty:
            # 各月の待ち時間合計を計算
            monthly_totals = device_stats.groupby('年月')['第三四分位点'].sum()
            
            # パーセンテージ計算
            device_stats['割合'] = device_stats.apply(
                lambda row: (row['第三四分位点'] / monthly_totals[row['年月']]) * 100, 
                axis=1
            )
            
            # 上位機器を特定（全月の平均割合基準）
            avg_ratios = device_stats.groupby('EQP_ID')['割合'].mean().sort_values(ascending=False)
            top_equipment = avg_ratios.head(display_count_tab3).index.tolist()
            
            # データフィルタリング
            filtered_data = device_stats[device_stats['EQP_ID'].isin(top_equipment)]
            
            # ピボットテーブル作成
            pivot_data = filtered_data.pivot(index='年月', columns='EQP_ID', values='割合').fillna(0)
            
            # 100%積み上げ棒グラフ作成
            fig = go.Figure()
            
            colors = px.colors.qualitative.Set3
            months = [str(m) for m in sorted(pivot_data.index)]
            
            for i, eqp in enumerate(pivot_data.columns):
                fig.add_trace(go.Bar(
                    name=eqp,
                    x=months,
                    y=pivot_data[eqp].tolist(),
                    marker_color=colors[i % len(colors)]
                ))
            
            fig.update_layout(
                title=f"{selected_device_tab3} - 月ごと待ち時間割合の推移",
                xaxis_title="月",
                yaxis_title="割合 (%)",
                barmode='stack',
                height=600,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 統計情報
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("表示機器数", len(top_equipment))
            with col2:
                st.metric("対象月数", len(months))
            with col3:
                avg_top_ratio = avg_ratios.iloc[0]
                st.metric("最大平均割合", f"{avg_top_ratio:.1f}%")
        else:
            st.warning("選択されたDeviceGpのデータが見つかりません。")

if __name__ == "__main__":
    main()
