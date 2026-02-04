#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DKEC 日報產出工具 - Streamlit 版本
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 頁面設定
st.set_page_config(
    page_title="DKEC 日報產出工具",
    page_icon="📊",
    layout="wide"
)

# 各平台欄位對應設定
PLATFORM_CONFIG = {
    'official': {
        'name': '官網',
        'date_column': '訂單日期',
        'amount_column': '折扣後金額',
        'source_sheet': '官網前日交易數據',
        'output_columns': [
            '商品原廠編號', '商品選項', '數量', '收件人', '訂單編號',
            '折扣後金額', '通路', '門市', '付款方式', '訂單狀態', '訂單日期'
        ],
        'column_mapping': {
            '商品料號': '商品原廠編號',
            '商品選項': '商品選項',
            '數量': '數量',
            '收件人': '收件人',
            '主單編號': '訂單編號',
            '銷售金額(折扣後)': '折扣後金額',
            '通路商': '通路',
            '門市': '門市',
            '付款方式': '付款方式',
            '訂單狀態': '訂單狀態',
            '轉單日期時間': '訂單日期'
        }
    },
    'shopee': {
        'name': '蝦皮',
        'date_column': '訂單日期',
        'amount_column': '訂單總金額 (單)',
        'source_sheet': '蝦皮前日交易數據',
        'output_columns': [
            '訂單編號', '商品總價', '訂單總金額 (單)', '商品名稱 (品)',
            '主商品貨號', '商品選項名稱 (品)', '商品活動價格 (品)',
            '數量', '寄送方式 (單)', '付款方式 (單)', '訂單狀態', '訂單日期'
        ],
        'column_mapping': {
            '訂單編號': '訂單編號',
            '商品總價': '商品總價',
            '買家總支付金額': '訂單總金額 (單)',
            '商品名稱': '商品名稱 (品)',
            '主商品貨號': '主商品貨號',
            '商品選項名稱': '商品選項名稱 (品)',
            '商品活動價格': '商品活動價格 (品)',
            '數量': '數量',
            '寄送方式': '寄送方式 (單)',
            '付款方式': '付款方式 (單)',
            '訂單狀態': '訂單狀態',
            '訂單成立日期': '訂單日期'
        }
    },
    'momo': {
        'name': 'MOMO',
        'date_column': '轉單日',
        'amount_column': '末端售價',
        'source_sheet': 'MOMO前日交易數據(未出貨)',
        'output_columns': [
            '訂單編號', '收件人姓名', '商品原廠編號', '單品詳細',
            '數量', '售價(含稅)', '末端售價', '轉單日', '訂單狀態'
        ],
        'column_mapping': {
            '訂單編號': '訂單編號',
            '收件人姓名': '收件人姓名',
            '商品原廠編號': '商品原廠編號',
            '單品詳細': '單品詳細',
            '數量': '數量',
            '售價(含稅)': '售價(含稅)',
            '末端售價': '末端售價',
            '轉單日': '轉單日',
            '訂單類別': '訂單狀態'
        }
    }
}


def parse_date(date_str):
    """解析日期字串，支援多種格式"""
    if pd.isna(date_str):
        return None

    if isinstance(date_str, datetime):
        return date_str.strftime('%Y/%m/%d')

    date_str = str(date_str).strip()

    formats = [
        '%Y/%m/%d',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y-%m-%d %H:%M'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:19], fmt)
            return dt.strftime('%Y/%m/%d')
        except:
            continue

    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y/%m/%d')
    except:
        return None


def process_data(df, platform):
    """處理資料，進行欄位對應"""
    config = PLATFORM_CONFIG[platform]
    result = pd.DataFrame()

    for source_col, target_col in config['column_mapping'].items():
        if source_col in df.columns:
            result[target_col] = df[source_col]
        else:
            result[target_col] = None

    # 處理日期
    date_source_cols = {
        'official': '轉單日期時間',
        'shopee': '訂單成立日期',
        'momo': '轉單日'
    }

    source_col = date_source_cols.get(platform)
    if source_col and source_col in df.columns:
        target_col = config['date_column']
        result[target_col] = df[source_col].apply(parse_date)

    return result


def read_excel_file(uploaded_file):
    """讀取上傳的 Excel 檔案"""
    try:
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
    except:
        uploaded_file.seek(0)
        xls = pd.ExcelFile(uploaded_file, engine='xlrd')
    return xls


def generate_report_html(df, platform, dates, total_amount):
    """產生報表 HTML"""
    config = PLATFORM_CONFIG[platform]

    # 格式化日期
    if len(dates) == 1:
        title_date = dates[0]
    else:
        title_date = dates[0]

    try:
        date_parts = title_date.split('/')
        short_date = f"{date_parts[1]}/{date_parts[2]}"
    except:
        short_date = title_date

    # 標題
    if platform == 'official':
        title = f"官網每日訂單報表{short_date}"
    elif platform == 'shopee':
        title = f"{short_date} 蝦皮訂單"
    else:
        title = f"{short_date} MOMO訂單"

    # 產生表格
    columns = list(df.columns)
    amount_col = config['amount_column']

    html = f'''
    <style>
        .report-container {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            background: white;
            padding: 15px;
        }}
        .report-title {{
            text-align: center;
            border-bottom: 1px solid #000;
            padding-bottom: 8px;
            margin-bottom: 10px;
        }}
        .report-title h2 {{
            font-size: 1.2em;
            margin: 0;
            text-decoration: underline;
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            border: 1px solid #8ea9db;
        }}
        .report-table th {{
            background: #4472c4;
            color: white;
            padding: 8px 6px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #8ea9db;
            font-size: 11px;
        }}
        .report-table td {{
            padding: 6px;
            border: 1px solid #d9e2f3;
            text-align: center;
        }}
        .report-table tbody tr:nth-child(odd) {{
            background: #d9e2f3;
        }}
        .report-table tbody tr:nth-child(even) {{
            background: white;
        }}
        .total-row {{
            background: white !important;
            font-weight: bold;
        }}
        .total-row td {{
            border-top: 2px solid #4472c4;
            padding-top: 10px;
        }}
        .total-label {{
            color: #c00000;
            text-align: right;
            padding-right: 15px;
        }}
        .total-value {{
            color: #c00000;
        }}
    </style>
    <div class="report-container">
        <div class="report-title">
            <h2>{title}</h2>
        </div>
        <table class="report-table">
            <thead>
                <tr>
    '''

    for col in columns:
        html += f'<th>{col}</th>'

    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in columns:
            val = row[col] if pd.notna(row[col]) else ''
            html += f'<td>{val}</td>'
        html += '</tr>'

    # 總計列
    html += '<tr class="total-row">'
    for i, col in enumerate(columns):
        if i == 0:
            html += '<td class="total-label">總計</td>'
        elif col == amount_col:
            html += f'<td class="total-value">{total_amount:,.0f}</td>'
        else:
            html += '<td></td>'
    html += '</tr>'

    html += '</tbody></table></div>'

    return html


# 主程式
def main():
    st.title("📊 DKEC 日報產出工具")
    st.caption("上傳訂單明細，快速產出日報表")

    # 初始化 session state
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None
    if 'available_dates' not in st.session_state:
        st.session_state.available_dates = []

    # 步驟 1：選擇平台
    st.subheader("① 選擇平台")

    col1, col2, col3 = st.columns(3)

    with col1:
        official_btn = st.button("🌐 官網", use_container_width=True)
    with col2:
        shopee_btn = st.button("🦐 蝦皮", use_container_width=True)
    with col3:
        momo_btn = st.button("🛒 MOMO", use_container_width=True)

    # 處理平台選擇
    if official_btn:
        st.session_state.platform = 'official'
        st.session_state.processed_df = None
    elif shopee_btn:
        st.session_state.platform = 'shopee'
        st.session_state.processed_df = None
    elif momo_btn:
        st.session_state.platform = 'momo'
        st.session_state.processed_df = None

    # 顯示目前選擇的平台
    if 'platform' in st.session_state:
        platform = st.session_state.platform
        platform_name = PLATFORM_CONFIG[platform]['name']
        st.success(f"已選擇：{platform_name}")

        # 步驟 2：上傳檔案
        st.subheader(f"② 上傳 {platform_name} 訂單明細")

        uploaded_file = st.file_uploader(
            "拖曳或點擊上傳 Excel 檔案",
            type=['xlsx', 'xls'],
            key=f"uploader_{platform}"
        )

        if uploaded_file is not None:
            try:
                with st.spinner('處理檔案中...'):
                    xls = read_excel_file(uploaded_file)
                    sheet_names = xls.sheet_names

                    config = PLATFORM_CONFIG[platform]
                    source_sheet = config['source_sheet']

                    if source_sheet in sheet_names:
                        df = pd.read_excel(xls, sheet_name=source_sheet)
                    else:
                        data_sheet = None
                        for sheet in sheet_names:
                            if '前日交易數據' in sheet:
                                data_sheet = sheet
                                break

                        if data_sheet:
                            df = pd.read_excel(xls, sheet_name=data_sheet)
                        else:
                            df = pd.read_excel(xls, sheet_name=0)

                    processed_df = process_data(df, platform)
                    date_column = config['date_column']

                    dates = processed_df[date_column].dropna().unique().tolist()
                    dates = [d for d in dates if d is not None]
                    dates.sort(reverse=True)

                    st.session_state.processed_df = processed_df
                    st.session_state.available_dates = dates

                    st.success(f"成功讀取 {len(processed_df)} 筆資料，{len(dates)} 個日期")

            except Exception as e:
                st.error(f"處理檔案時發生錯誤：{str(e)}")

        # 步驟 3：選擇日期
        if st.session_state.processed_df is not None and st.session_state.available_dates:
            st.subheader("③ 選擇日報日期（可多選）")

            selected_dates = st.multiselect(
                "選擇要產生報表的日期",
                options=st.session_state.available_dates,
                default=[st.session_state.available_dates[0]] if st.session_state.available_dates else []
            )

            if selected_dates:
                st.info(f"已選擇 {len(selected_dates)} 個日期：{', '.join(selected_dates)}")

                # 產生報表按鈕
                if st.button("📄 產生日報表", type="primary", use_container_width=True):
                    config = PLATFORM_CONFIG[platform]
                    date_column = config['date_column']
                    amount_column = config['amount_column']

                    filtered_df = st.session_state.processed_df[
                        st.session_state.processed_df[date_column].isin(selected_dates)
                    ].copy()

                    # 只保留需要的欄位
                    output_columns = config['output_columns']
                    display_df = filtered_df[[col for col in output_columns if col in filtered_df.columns]].copy()
                    display_df = display_df.sort_values(by=date_column, ascending=False)

                    # 計算總金額
                    if amount_column in filtered_df.columns:
                        total_amount = pd.to_numeric(filtered_df[amount_column], errors='coerce').sum()
                    else:
                        total_amount = 0

                    # 儲存結果
                    st.session_state.display_df = display_df
                    st.session_state.total_amount = total_amount
                    st.session_state.selected_dates = selected_dates
                    st.session_state.show_report = True

        # 顯示報表結果
        if st.session_state.get('show_report'):
            st.subheader("📊 報表結果")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("日期", ', '.join(st.session_state.selected_dates))
            with col2:
                st.metric("訂單數", f"{len(st.session_state.display_df)} 筆")
            with col3:
                st.metric("銷售金額總額", f"NT$ {st.session_state.total_amount:,.0f}")

            # 產生 HTML 報表
            report_html = generate_report_html(
                st.session_state.display_df,
                platform,
                st.session_state.selected_dates,
                st.session_state.total_amount
            )

            # 顯示報表
            st.markdown("---")
            st.markdown(report_html, unsafe_allow_html=True)

            # 提示
            st.markdown("---")
            st.info("💡 提示：可以使用瀏覽器的截圖功能（如 Chrome 的開發者工具）來擷取報表圖片")

            # 重新開始按鈕
            if st.button("🔄 重新開始"):
                for key in ['processed_df', 'available_dates', 'display_df',
                           'total_amount', 'selected_dates', 'show_report', 'platform']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()


if __name__ == '__main__':
    main()
