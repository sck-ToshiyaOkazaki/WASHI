import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from functools import lru_cache
import polars as pl
from typing import Optional, Dict, List
import gc

# アプリのタイトル設定
st.set_page_config(page_title="SONY製造情報可視化アプリ", layout="wide")
st.title("SONY製造情報可視化アプリ")

# データベースパスを設定
db_path = "./load/SONY.db"

# キャッシュをクリア（デバッグ用）
if st.sidebar.button("🔄 キャッシュをクリア"):
    st.cache_data.clear()
    st.rerun()

# データ読み込みオプション
st.sidebar.markdown("### ⚙️ データ読み込み設定")
st.sidebar.info("🚀 大容量データ対応: 最大32GBメモリまで処理可能")

# 期間設定
st.sidebar.markdown("#### 📅 データ取得期間")
period_months = st.sidebar.selectbox(
    "データ最終日からの期間（月数）",
    ["全期間", 1, 3, 6, 12],
    index=0,  # デフォルトを全期間に変更
    help="データベース内の最新日付からさかのぼって取得する月数を選択してください"
)

# 期間設定変更時の注意
if period_months != "全期間":
    st.sidebar.info("💡 期間を変更した場合は「キャッシュをクリア」ボタンを押してください")

# データ読み込み上限設定
data_limit = st.sidebar.selectbox(
    "データ読み込み上限",
    [10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, "全件"],
    index=2,  # デフォルトを100,000件に設定
    help="大容量データの場合、読み込み上限を設定して高速化できます（最大32GBメモリまで対応）"
)

# データベースから必要なデータを読み込む（元の仕様）
@st.cache_data(ttl=3600, show_spinner="データを読み込み中...", max_entries=3)
def load_data_optimized(period_months="全期間", data_limit=100000):
    """元のチャンク読み込み方式を使用"""
    try:
        # データベース接続
        conn = sqlite3.connect(db_path)
        st.sidebar.success(f"✅ データベース接続成功")
        
        # 期間フィルタの設定
        date_filter = ""
        if period_months != "全期間":
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(OPE_START_DATETIME) 
                    FROM LOG2 
                    WHERE SUB_LOT_TYPE = 'P0' AND MRC = 'MASTER' 
                    AND OPE_START_DATETIME IS NOT NULL
                """)
                max_date_result = cursor.fetchone()
                
                if max_date_result and max_date_result[0]:
                    max_date = max_date_result[0]
                    st.sidebar.info(f"📅 最新データ日時: {max_date}")
                    date_filter = f"AND OPE_START_DATETIME >= datetime('{max_date}', '-{period_months} months')"
                    st.sidebar.info(f"📅 期間フィルタ: 最新データから{period_months}ヶ月")
                    st.sidebar.info(f"🔍 適用されるフィルタ: {date_filter}")
                else:
                    st.sidebar.warning("⚠️ 最新データ日時が取得できませんでした")
            except Exception as e:
                st.sidebar.warning(f"⚠️ 期間フィルタエラー: {e}")
        
        # LIMIT句の設定
        limit_clause = f"LIMIT {data_limit}" if data_limit != "全件" else ""
        
        # 最適化されたSQLクエリ（実際のデータ形式に合わせて修正）
        query = f"""
        SELECT 
            LOT_ID, 
            OPE_START_DATETIME, 
            CAST(WAIT_TIME as REAL) as WAIT_TIME, 
            EQP_ID, 
            OPE_NO, 
            SUB_LOT_TYPE, 
            MRC, 
            DeviceGp
        FROM LOG2
        WHERE SUB_LOT_TYPE = 'P0' 
        AND MRC = 'MASTER'
        AND WAIT_TIME IS NOT NULL
        AND WAIT_TIME != ''
        AND WAIT_TIME != '0'
        AND CAST(WAIT_TIME as REAL) > 0
        AND DeviceGp IS NOT NULL
        AND DeviceGp != ''
        AND EQP_ID IS NOT NULL
        AND EQP_ID != ''
        AND OPE_START_DATETIME IS NOT NULL
        AND OPE_START_DATETIME != ''
        {date_filter}
        ORDER BY ROWID DESC
        {limit_clause}
        """
        
        st.sidebar.info(f"🔍 読み込み上限: {data_limit}件" if data_limit != "全件" else f"🔍 読み込み上限: {data_limit}")
        
        # デバッグ用：実際のクエリを表示
        if period_months != "全期間":
            st.sidebar.info(f"🔍 期間フィルタが適用されています: {period_months}ヶ月")
        else:
            st.sidebar.info("🔍 全期間でデータを取得します")
        
        # チャンク読み込みで大量データに対応（進行状況表示付き）
        # データ量に応じてチャンクサイズを動的に調整
        if data_limit == "全件":
            chunk_size = 50000  # 全件の場合は大きなチャンクサイズ
        elif isinstance(data_limit, int):
            if data_limit >= 5000000:  # 500万件以上
                chunk_size = 100000
            elif data_limit >= 1000000:  # 100万件以上
                chunk_size = 50000
            elif data_limit >= 100000:  # 10万件以上
                chunk_size = 20000
            else:
                chunk_size = 10000
        else:
            chunk_size = 10000
        
        st.sidebar.info(f"📦 チャンクサイズ: {chunk_size:,}件/チャンク")
        
        try:
            # 少量のデータで先にテスト
            if data_limit != "全件":
                test_query = query.replace(f"LIMIT {data_limit}", "LIMIT 100")
            else:
                # 全件の場合は元のクエリにLIMIT 100を追加
                test_query = query + " LIMIT 100"
            
            test_df = pd.read_sql(test_query, conn)
            
            if test_df.empty:
                st.sidebar.warning("⚠️ 条件に一致するデータがありません")
                conn.close()
                return pd.DataFrame()
            
            st.sidebar.success(f"✅ テストクエリ成功: {len(test_df)}件")
            
            # 実際のデータ読み込み
            if data_limit == "全件" or data_limit > chunk_size:
                # チャンクで読み込み（進行状況表示付き）
                df_chunks = []
                chunk_count = 0
                total_loaded = 0
                
                # 進行状況表示用のプレースホルダ
                progress_placeholder = st.sidebar.empty()
                status_placeholder = st.sidebar.empty()
                chunk_detail = st.sidebar.empty()
                
                # 推定チャンク数を計算
                if data_limit != "全件":
                    estimated_chunks = (data_limit // chunk_size) + 1
                else:
                    estimated_chunks = None
                
                status_placeholder.info("📊 チャンクデータを読み込み中...")
                
                for chunk in pd.read_sql(query, conn, chunksize=chunk_size):
                    chunk_count += 1
                    
                    # チャンクレベルでのデータ処理
                    if not chunk.empty:
                        # 日時変換とyear_month追加
                        chunk['OPE_START_DATETIME'] = pd.to_datetime(chunk['OPE_START_DATETIME'], errors='coerce')
                        chunk['year_month'] = chunk['OPE_START_DATETIME'].dt.strftime('%Y-%m')
                        
                        # 有効なデータのみ追加
                        chunk = chunk.dropna(subset=['OPE_START_DATETIME', 'year_month'])
                        
                        if not chunk.empty:
                            df_chunks.append(chunk)
                            total_loaded += len(chunk)
                        
                        # チャンク詳細情報
                        chunk_detail.text(f"チャンク{chunk_count}: {len(chunk):,}件 (累計: {total_loaded:,}件)")
                    
                    # 進行状況を更新
                    if estimated_chunks:
                        progress_pct = min(100, (chunk_count / estimated_chunks) * 100)
                        progress_placeholder.progress(int(progress_pct))
                        status_placeholder.info(f"📊 進行状況: {progress_pct:.1f}% ({chunk_count}/{estimated_chunks}チャンク)")
                    else:
                        status_placeholder.info(f"📊 チャンク{chunk_count}: {total_loaded:,}件読み込み済み")
                    
                    # データ制限チェック
                    if data_limit != "全件" and total_loaded >= data_limit:
                        status_placeholder.success(f"✅ データ制限に達しました: {total_loaded:,}件")
                        break
                    
                    # メモリ保護（20チャンクごとにチェック - 大容量対応）
                    if chunk_count % 20 == 0:
                        current_memory = sum(chunk.memory_usage(deep=True).sum() for chunk in df_chunks)
                        memory_mb = current_memory / (1024 * 1024)
                        memory_gb = memory_mb / 1024
                        chunk_detail.text(f"メモリ使用量: {memory_gb:.2f}GB ({memory_mb:.1f}MB) (チャンク{chunk_count}まで)")
                        
                        if current_memory > 32 * 1024 * 1024 * 1024:  # 32GB制限
                            status_placeholder.warning(f"⚠️ メモリ制限により読み込み終了: {total_loaded:,}件 (32GB達成)")
                            break
                
                # 進行状況表示をクリア
                progress_placeholder.empty()
                chunk_detail.empty()
                
                if df_chunks:
                    status_placeholder.info("� データを結合中...")
                    df = pd.concat(df_chunks, ignore_index=True)
                    if data_limit != "全件":
                        df = df.head(data_limit)
                    status_placeholder.success(f"✅ チャンク読み込み完了: {len(df):,}件 ({chunk_count}チャンク)")
                else:
                    df = pd.DataFrame()
                    status_placeholder.warning("⚠️ データが読み込めませんでした")
            else:
                # 一括読み込み
                st.sidebar.info("📊 一括データ読み込み中...")
                df = pd.read_sql(query, conn)
                
                # 日時変換とyear_month追加
                if not df.empty:
                    df['OPE_START_DATETIME'] = pd.to_datetime(df['OPE_START_DATETIME'], errors='coerce')
                    df['year_month'] = df['OPE_START_DATETIME'].dt.strftime('%Y-%m')
                    df = df.dropna(subset=['OPE_START_DATETIME', 'year_month'])
                
                st.sidebar.success(f"✅ 一括読み込み完了: {len(df):,}件")
                
        except Exception as query_error:
            st.sidebar.error(f"❌ クエリエラー: {query_error}")
            conn.close()
            return pd.DataFrame()
        
        conn.close()
        
        if df.empty:
            st.sidebar.warning("⚠️ データが見つかりませんでした")
            return pd.DataFrame()
        
        # データ型の変換（最適化）
        df['WAIT_TIME'] = pd.to_numeric(df['WAIT_TIME'], errors='coerce')
        
        # 最終的なデータクリーニング
        original_len = len(df)
        st.sidebar.info(f"🔍 処理前データ: {original_len:,}件")
        
        if not df.empty:
            # 有効なデータのみ保持
            df = df.dropna(subset=['WAIT_TIME', 'OPE_START_DATETIME', 'DeviceGp', 'EQP_ID', 'year_month'])
            df = df[df['WAIT_TIME'] > 0]
            
            # データ型最適化（メモリ節約）
            df['WAIT_TIME'] = df['WAIT_TIME'].astype('float32')
            for col in ['EQP_ID', 'DeviceGp', 'LOT_ID']:
                if col in df.columns and df[col].dtype == 'object':
                    df[col] = df[col].astype('category')
            
            # 実際のデータ日付範囲を表示（期間フィルタの確認用）
            if 'OPE_START_DATETIME' in df.columns:
                min_date = df['OPE_START_DATETIME'].min()
                max_date = df['OPE_START_DATETIME'].max()
                st.sidebar.info(f"📅 実際のデータ期間: {min_date} ～ {max_date}")
            
            # 最終的なメモリ使用量を表示
            final_memory = df.memory_usage(deep=True).sum()
            final_memory_mb = final_memory / (1024 * 1024)
            final_memory_gb = final_memory_mb / 1024
            if final_memory_gb >= 1:
                st.sidebar.info(f"💾 最終メモリ使用量: {final_memory_gb:.2f}GB")
            else:
                st.sidebar.info(f"💾 最終メモリ使用量: {final_memory_mb:.1f}MB")
            
            st.sidebar.success(f"✅ 最終データ: {len(df):,}件")
        
        st.sidebar.success(f"✅ データ読み込み完了: {len(df):,}件 (元データ: {original_len:,}件)")
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ データベースエラー: {e}")
        return pd.DataFrame()

# 高速化された事前計算関数
@st.cache_data(ttl=3600, show_spinner="統計データを高速計算中...", max_entries=5)
def calculate_monthly_stats_optimized(df):
    """最適化された月ごとの統計計算"""
    try:
        if df.empty:
            return pd.DataFrame()
        
        # NumPyを使用した高速集約
        stats_list = []
        
        # グループ化のためのユニークな組み合わせを事前取得
        grouped = df.groupby(['year_month', 'DeviceGp', 'EQP_ID'])['WAIT_TIME']
        
        for (year_month, device_gp, eqp_id), group in grouped:
            wait_times = group.values  # NumPy配列で高速化
            
            stats_list.append({
                'year_month': year_month,
                'DeviceGp': device_gp,
                'EQP_ID': eqp_id,
                'count': len(wait_times),
                'mean': np.mean(wait_times),
                'median': np.median(wait_times),
                'q3': np.percentile(wait_times, 75)
            })
        
        device_stats = pd.DataFrame(stats_list)
        
        # 全DeviceGp統合版の計算（高速化）
        all_stats_list = []
        all_grouped = df.groupby(['year_month', 'EQP_ID'])['WAIT_TIME']
        
        for (year_month, eqp_id), group in all_grouped:
            wait_times = group.values
            
            all_stats_list.append({
                'year_month': year_month,
                'DeviceGp': 'ALL',
                'EQP_ID': eqp_id,
                'count': len(wait_times),
                'mean': np.mean(wait_times),
                'median': np.median(wait_times),
                'q3': np.percentile(wait_times, 75)
            })
        
        all_stats = pd.DataFrame(all_stats_list)
        
        # 結合
        combined_stats = pd.concat([device_stats, all_stats], ignore_index=True)
        
        # データ型最適化
        combined_stats['count'] = combined_stats['count'].astype('int32')
        combined_stats['mean'] = combined_stats['mean'].astype('float32')
        combined_stats['median'] = combined_stats['median'].astype('float32')
        combined_stats['q3'] = combined_stats['q3'].astype('float32')
        
        st.sidebar.success(f"✅ 高速事前計算完了: {len(combined_stats):,}件")
        return combined_stats
        
    except Exception as e:
        st.sidebar.error(f"❌ 事前計算エラー: {e}")
        return pd.DataFrame()

# 高速化されたプロット作成関数
@lru_cache(maxsize=32)
def create_optimized_plot(plot_type: str, data_hash: str, **kwargs):
    """LRUキャッシュを使用した高速プロット生成"""
    # この関数は実際のプロット作成ロジックで使用
    pass

def create_fast_ranking_chart(plot_data, title, height=600):
    """高速化されたランキングチャート"""
    # データサンプリングで高速化（データが多い場合）
    if len(plot_data) > 1000:
        # 重要なデータポイントを保持しつつサンプリング
        sampled_data = plot_data.groupby('EQP_ID').apply(
            lambda x: x.iloc[::max(1, len(x)//10)]
        ).reset_index(drop=True)
        st.info(f"⚡ 高速化のためデータをサンプリング: {len(plot_data):,} → {len(sampled_data):,}件")
        plot_data = sampled_data
    
    # Plotlyの最適化設定
    fig = px.line(
        plot_data, 
        x='year_month', 
        y='rank', 
        color='EQP_ID',
        markers=True, 
        title=title,
        labels={
            'year_month': '月', 
            'rank': 'ランキング（1位が最も待ち時間が長い）', 
            'EQP_ID': '機器ID'
        },
        hover_data=['count', 'q3']
    )
    
    # パフォーマンス最適化設定
    fig.update_layout(
        height=height,
        showlegend=len(plot_data['EQP_ID'].unique()) <= 20,  # 凡例を条件付きで表示
        hovermode='closest',
        dragmode=False,  # ドラッグ無効化で軽量化
    )
    
    fig.update_yaxes(autorange="reversed")
    
    # WebGLレンダリングで高速化（多データの場合）
    if len(plot_data) > 500:
        fig.update_traces(mode='lines+markers', marker=dict(size=4))
    
    return fig

def create_fast_stacked_bar(plot_df, title, height=600):
    """高速化された積み上げ棒グラフ"""
    # カテゴリ数制限で高速化
    unique_eqps = plot_df['EQP_ID'].nunique()
    if unique_eqps > 30:
        # 上位30機器＋その他でまとめる
        top_eqps = plot_df.groupby('EQP_ID')['wait_time'].sum().nlargest(29).index
        plot_df.loc[~plot_df['EQP_ID'].isin(top_eqps), 'EQP_ID'] = 'その他'
        st.info(f"⚡ 高速化のため上位29機器＋その他で表示 (元: {unique_eqps}機器)")
    
    fig = px.bar(
        plot_df, 
        x='month', 
        y='percentage', 
        color='EQP_ID',
        title=title,
        labels={
            'month': '月', 
            'percentage': '待ち時間の割合 (%)', 
            'EQP_ID': '機器ID'
        },
        hover_data=['wait_time']
    )
    
    fig.update_layout(
        barmode='stack',
        height=height,
        yaxis=dict(range=[0, 100]),
        showlegend=plot_df['EQP_ID'].nunique() <= 20,
        dragmode=False
    )
    
    return fig
    


# メイン処理（最適化版）
def main():
    try:
        # プログレスバーと詳細ステータス
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_status = st.sidebar.empty()
        
        # ステップ1: データベース接続
        status_text.text('⚡ 高速データベース接続中...')
        detail_status.info("🔗 データベース接続を開始...")
        progress_bar.progress(10)
        
        # ステップ2: 最適化されたデータ読み込み
        status_text.text('⚡ 高速データ読み込み中...')
        if isinstance(data_limit, int):
            detail_status.info(f"📊 高速データ取得中 (期間: {period_months}, 上限: {data_limit:,}件)")
        else:
            detail_status.info(f"📊 高速データ取得中 (期間: {period_months}, 上限: {data_limit})")
        
        # 最適化されたload_data関数を使用
        df = load_data_optimized(period_months=period_months, data_limit=data_limit)
        progress_bar.progress(50)
        
        # メモリクリーンアップ
        gc.collect()
        
        if not df.empty:
            status_text.text('⚡ 高速統計計算中...')
            detail_status.info("📈 最適化された月次統計を計算中...")
            progress_bar.progress(70)
            
            # 最適化された事前計算実行
            monthly_stats = calculate_monthly_stats_optimized(df)
            progress_bar.progress(90)
            
            if not monthly_stats.empty:
                status_text.text('⚡ 高速可視化準備中...')
                detail_status.info("🎨 高速可視化コンポーネント準備中...")
                progress_bar.progress(100)
                
                # 少し待ってからクリア
                import time
                time.sleep(0.3)  # 時間短縮
                
                progress_bar.empty()
                status_text.empty()
                detail_status.success("🚀 高速処理完了！")
                
                # データの概要を表示
                unique_devices = df['DeviceGp'].nunique()
                unique_months = df['year_month'].nunique()
                unique_eqps = df['EQP_ID'].nunique()
                date_range = f"{df['year_month'].min()} ～ {df['year_month'].max()}"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("総レコード数", f"{len(df):,}")
                with col2:
                    st.metric("デバイス数", unique_devices)
                with col3:
                    st.metric("機器数", unique_eqps)
                with col4:
                    st.metric("対象期間", f"{unique_months}ヶ月")
                
                st.info(f"📅 データ期間: {date_range}")
                
                # デバイスリストを取得
                devices_list = sorted([d for d in df['DeviceGp'].dropna().unique() if d != 'ALL'])
                
                if devices_list:
                    devices = ["ALL"] + devices_list
                    
                    # サイドバーにデバイス選択を追加
                    selected_device = st.sidebar.selectbox(
                        "🔍 デバイスを選択してください", 
                        devices,
                        index=0,
                        help="個別のデバイスまたは全デバイス統合（ALL）を選択できます"
                    )
                    
                    # パフォーマンス情報表示
                    if len(df) > 100000:
                        st.sidebar.info("⚡ 大容量データ対応：高速化機能が有効です")
                    
                    # タブを作成
                    tab1, tab2, tab3 = st.tabs(["📊 機器待ち時間ランキング表", "📈 機器ランキング推移", "🥧 機器待ち時間割合"])
                    
                    # 可視化1: 月ごとの各機器の待ち時間のランキング表（最適化版）
                    with tab1:
                        st.header("📊 月ごとの各機器の待ち時間ランキング")
                        
                        # 月の選択
                        available_months = sorted(monthly_stats[monthly_stats['DeviceGp'] == selected_device]['year_month'].unique())
                        if available_months:
                            selected_month = st.selectbox("月を選択", available_months, index=len(available_months)-1)
                            
                            # データ数の閾値設定
                            min_data_count = st.slider(
                                "データ数の閾値（これ以下のデータ数の機器はランキングから除外）",
                                min_value=1, max_value=200, value=50, step=1
                            )
                            
                            # 最適化されたフィルタリング
                            mask = (
                                (monthly_stats['year_month'] == selected_month) & 
                                (monthly_stats['DeviceGp'] == selected_device) &
                                (monthly_stats['count'] >= min_data_count)
                            )
                            filtered_stats = monthly_stats[mask].copy()
                            
                            if not filtered_stats.empty:
                                # 第三四分位点でソート（高速化）
                                filtered_stats = filtered_stats.sort_values('q3', ascending=False).reset_index(drop=True)
                                filtered_stats['rank'] = np.arange(1, len(filtered_stats) + 1)  # NumPy使用で高速化
                                
                                # 表示用データフレーム（小数点丸めを高速化）
                                display_df = filtered_stats[['rank', 'EQP_ID', 'q3', 'mean', 'median', 'count']].copy()
                                display_df[['q3', 'mean', 'median']] = display_df[['q3', 'mean', 'median']].round(2)
                                
                                display_df = display_df.rename(columns={
                                    'rank': 'ランク', 
                                    'EQP_ID': '機器ID',
                                    'q3': '待ち時間(第三四分位点)', 
                                    'mean': '平均待ち時間', 
                                    'median': '中央値', 
                                    'count': 'データ数'
                                })
                                
                                st.write(f"**{selected_month}の待ち時間ランキング - デバイス: {selected_device}**")
                                
                                # 大量データの場合はページネーション風の表示
                                if len(display_df) > 100:
                                    show_all = st.checkbox("全ての機器を表示", value=False)
                                    if not show_all:
                                        display_df = display_df.head(100)
                                        st.info("上位100件を表示中。全件表示するには上のチェックボックスをONにしてください。")
                                
                                st.dataframe(display_df, use_container_width=True, height=400)
                                
                                st.info(f"表示機器数: {len(filtered_stats)}台 | 最大待ち時間(Q3): {filtered_stats['q3'].max():.2f} | 最小待ち時間(Q3): {filtered_stats['q3'].min():.2f}")
                            else:
                                st.warning(f"選択された条件に一致するデータがありません。")
                        else:
                            st.warning("月次データが見つかりません。")
                    
                    # 可視化2: 月ごとの各機器の待ち時間のランキング変化（最適化版）
                    with tab2:
                        st.header("📈 月ごとの待ち時間ランキング推移")
                        
                        # データ数の閾値設定
                        min_data_count_vis2 = st.slider(
                            "データ数の閾値（これ以下のデータ数の機器は推移から除外）",
                            min_value=1, max_value=200, value=50, step=1, key="vis2_threshold"
                        )
                        
                        # 上位表示する機器数を選択
                        max_machines = min(50, monthly_stats[monthly_stats['DeviceGp'] == selected_device]['EQP_ID'].nunique())
                        top_n = st.slider("表示する機器数", min_value=5, max_value=max_machines, value=min(25, max_machines), step=1)
                        
                        # 最適化されたフィルタリング
                        device_mask = (
                            (monthly_stats['DeviceGp'] == selected_device) &
                            (monthly_stats['count'] >= min_data_count_vis2)
                        )
                        device_stats = monthly_stats[device_mask].copy()
                        
                        if not device_stats.empty:
                            # 月ごとのランキングを高速計算
                            device_stats['rank'] = device_stats.groupby('year_month')['q3'].rank(method='dense', ascending=False)
                            
                            # 複数の月にデータがある機器を特定（高速化）
                            eqp_month_counts = device_stats.groupby('EQP_ID')['year_month'].nunique()
                            multi_month_eqps = eqp_month_counts[eqp_month_counts >= 2].index.tolist()
                            
                            if multi_month_eqps:
                                # 平均Q3値でトップN機器を選択（高速化）
                                avg_q3 = device_stats[device_stats['EQP_ID'].isin(multi_month_eqps)].groupby('EQP_ID')['q3'].mean()
                                top_eqps = avg_q3.nlargest(top_n).index.tolist()
                                
                                plot_data = device_stats[device_stats['EQP_ID'].isin(top_eqps)]
                                
                                if not plot_data.empty:
                                    # 最適化されたプロット作成
                                    fig = create_fast_ranking_chart(
                                        plot_data, 
                                        f"月ごとの待ち時間ランキング推移 - デバイス: {selected_device}",
                                        height=600
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})  # ツールバー非表示で軽量化
                                    
                                    st.info(f"表示機器数: {len(top_eqps)}台（最小データ数: {min_data_count_vis2}件以上）")
                                else:
                                    st.warning("プロット用のデータが見つかりません。")
                            else:
                                st.warning("複数の月にわたってデータがある機器が見つかりません。")
                        else:
                            st.warning(f"選択されたデバイス({selected_device})のデータがありません。")
                    
                    # 可視化3: 月ごとの各機器の待ち時間の割合の可視化（最適化版）
                    with tab3:
                        st.header("🥧 月ごとの機器待ち時間の割合")
                        
                        # 上位表示する機器数を選択
                        max_machines_vis3 = min(30, df['EQP_ID'].nunique())
                        top_n_vis3 = st.slider("上位表示する機器数", min_value=5, max_value=max_machines_vis3, value=min(20, max_machines_vis3), step=1, key="vis3_top_n")
                        
                        # 選択されたデバイスに基づいてデータをフィルタリング（最適化）
                        if selected_device == "ALL":
                            device_df_vis3 = df
                        else:
                            device_df_vis3 = df[df['DeviceGp'] == selected_device].copy()
                        
                        if not device_df_vis3.empty:
                            # 月ごとの各機器の待ち時間合計を高速計算
                            monthly_wait = device_df_vis3.groupby(['year_month', 'EQP_ID'])['WAIT_TIME'].sum().reset_index()
                            
                            # 各月の上位機器を効率的に計算
                            plot_data = []
                            for month in sorted(monthly_wait['year_month'].unique()):
                                month_data = monthly_wait[monthly_wait['year_month'] == month].copy()
                                month_data = month_data.sort_values('WAIT_TIME', ascending=False)
                                
                                # 上位N機器とその他を分ける
                                if len(month_data) > top_n_vis3:
                                    top_eqps = month_data.head(top_n_vis3)
                                    others_wait = month_data.tail(len(month_data) - top_n_vis3)['WAIT_TIME'].sum()
                                    
                                    # 上位機器のデータ追加
                                    for _, row in top_eqps.iterrows():
                                        plot_data.append({
                                            'month': month,
                                            'EQP_ID': row['EQP_ID'],
                                            'wait_time': row['WAIT_TIME']
                                        })
                                    
                                    # その他のデータ追加
                                    if others_wait > 0:
                                        plot_data.append({
                                            'month': month,
                                            'EQP_ID': 'その他',
                                            'wait_time': others_wait
                                        })
                                else:
                                    # 全機器を追加
                                    for _, row in month_data.iterrows():
                                        plot_data.append({
                                            'month': month,
                                            'EQP_ID': row['EQP_ID'],
                                            'wait_time': row['WAIT_TIME']
                                        })
                            
                            if plot_data:
                                plot_df = pd.DataFrame(plot_data)
                                
                                # 割合計算（高速化）
                                plot_df['total_by_month'] = plot_df.groupby('month')['wait_time'].transform('sum')
                                plot_df['percentage'] = (plot_df['wait_time'] / plot_df['total_by_month']) * 100
                                
                                # 最適化されたプロット作成
                                fig = create_fast_stacked_bar(
                                    plot_df, 
                                    f"月ごとの機器待ち時間の割合 - デバイス: {selected_device}",
                                    height=600
                                )
                                
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                                
                                unique_months = len(plot_df['month'].unique())
                                unique_eqps = len(plot_df['EQP_ID'].unique())
                                st.info(f"表示期間: {unique_months}ヶ月 | 表示機器数: {unique_eqps}台")
                            else:
                                st.warning("プロット用のデータが準備できませんでした。")
                        else:
                            st.warning(f"選択されたデバイス({selected_device})のデータがありません。")
                else:
                    st.warning("デバイスが見つかりません。データを確認してください。")
            else:
                st.warning("事前計算に失敗しました。")
        else:
            st.warning("データが読み込めませんでした。データベースの接続とテーブル構造を確認してください。")
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.info("このアプリはSQLiteデータベース「SONY.db」のLOG2テーブルを使用しています。")
    finally:
        # メモリクリーンアップ
        gc.collect()

if __name__ == "__main__":
    main()
