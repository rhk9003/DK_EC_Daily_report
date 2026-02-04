#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DKEC 日報產出工具 - Web App
"""

import os
import io
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# 確保上傳資料夾存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 各平台欄位對應設定
# 原始欄位 -> 輸出欄位
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

    # 嘗試多種格式
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
            dt = datetime.strptime(date_str[:len(fmt.replace('%Y', '2025').replace('%m', '01').replace('%d', '01').replace('%H', '00').replace('%M', '00').replace('%S', '00'))], fmt)
            return dt.strftime('%Y/%m/%d')
        except:
            continue

    # 如果都失敗，嘗試直接解析
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y/%m/%d')
    except:
        return None


def process_official_data(df):
    """處理官網資料"""
    config = PLATFORM_CONFIG['official']
    result = pd.DataFrame()

    # 欄位對應
    for source_col, target_col in config['column_mapping'].items():
        if source_col in df.columns:
            result[target_col] = df[source_col]
        else:
            result[target_col] = None

    # 處理日期
    if '轉單日期時間' in df.columns:
        result['訂單日期'] = df['轉單日期時間'].apply(parse_date)

    return result


def process_shopee_data(df):
    """處理蝦皮資料"""
    config = PLATFORM_CONFIG['shopee']
    result = pd.DataFrame()

    # 欄位對應
    for source_col, target_col in config['column_mapping'].items():
        if source_col in df.columns:
            result[target_col] = df[source_col]
        else:
            result[target_col] = None

    # 處理日期
    if '訂單成立日期' in df.columns:
        result['訂單日期'] = df['訂單成立日期'].apply(parse_date)

    return result


def process_momo_data(df):
    """處理 MOMO 資料"""
    config = PLATFORM_CONFIG['momo']
    result = pd.DataFrame()

    # 欄位對應
    for source_col, target_col in config['column_mapping'].items():
        if source_col in df.columns:
            result[target_col] = df[source_col]
        else:
            result[target_col] = None

    # 處理日期
    if '轉單日' in df.columns:
        result['轉單日'] = df['轉單日'].apply(parse_date)

    return result


def read_excel_file(file_storage):
    """讀取上傳的 Excel 檔案"""
    try:
        # 嘗試讀取 xlsx
        xls = pd.ExcelFile(file_storage, engine='openpyxl')
    except:
        # 嘗試讀取 xls
        file_storage.seek(0)
        xls = pd.ExcelFile(file_storage, engine='xlrd')

    return xls


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上傳並解析檔案"""
    if 'file' not in request.files:
        return jsonify({'error': '未上傳檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未選擇檔案'}), 400

    # 取得前端指定的平台
    platform = request.form.get('platform')
    if not platform or platform not in PLATFORM_CONFIG:
        return jsonify({'error': '請先選擇平台'}), 400

    try:
        # 讀取 Excel 檔案
        xls = read_excel_file(file)
        sheet_names = xls.sheet_names

        # 根據指定平台找到資料分頁
        config = PLATFORM_CONFIG[platform]
        source_sheet = config['source_sheet']

        # 嘗試讀取指定分頁，如果不存在則讀取第一個分頁
        if source_sheet in sheet_names:
            df = pd.read_excel(xls, sheet_name=source_sheet)
        else:
            # 嘗試找包含「前日交易數據」的分頁
            data_sheet = None
            for sheet in sheet_names:
                if '前日交易數據' in sheet:
                    data_sheet = sheet
                    break

            if data_sheet:
                df = pd.read_excel(xls, sheet_name=data_sheet)
            else:
                # 讀取第一個分頁
                df = pd.read_excel(xls, sheet_name=0)

        # 處理資料（依照指定平台）
        if platform == 'official':
            processed_df = process_official_data(df)
            date_column = '訂單日期'
        elif platform == 'shopee':
            processed_df = process_shopee_data(df)
            date_column = '訂單日期'
        else:  # momo
            processed_df = process_momo_data(df)
            date_column = '轉單日'

        # 取得可用日期列表
        dates = processed_df[date_column].dropna().unique().tolist()
        dates = [d for d in dates if d is not None]
        dates.sort(reverse=True)

        # 儲存處理後的資料到 session (使用檔案暫存)
        session_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{session_id}.pkl')
        processed_df.to_pickle(temp_file)

        return jsonify({
            'success': True,
            'platform': platform,
            'platform_name': PLATFORM_CONFIG[platform]['name'],
            'dates': dates,
            'total_rows': len(processed_df),
            'session_id': session_id
        })

    except Exception as e:
        return jsonify({'error': f'處理檔案時發生錯誤: {str(e)}'}), 500


@app.route('/api/generate', methods=['POST'])
def generate_report():
    """產生日報圖片（支援多日期）"""
    data = request.json
    session_id = data.get('session_id')
    selected_dates = data.get('dates', [])  # 改為接收多個日期
    platform = data.get('platform')

    # 相容舊的單日期格式
    if not selected_dates and data.get('date'):
        selected_dates = [data.get('date')]

    if not all([session_id, selected_dates, platform]):
        return jsonify({'error': '缺少必要參數'}), 400

    try:
        # 讀取暫存資料
        temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{session_id}.pkl')
        if not os.path.exists(temp_file):
            return jsonify({'error': '資料已過期，請重新上傳檔案'}), 400

        df = pd.read_pickle(temp_file)

        # 篩選多個日期
        config = PLATFORM_CONFIG[platform]
        date_column = config['date_column']

        filtered_df = df[df[date_column].isin(selected_dates)].copy()

        if len(filtered_df) == 0:
            return jsonify({'error': f'找不到所選日期的資料'}), 400

        # 計算總金額
        amount_column = config['amount_column']
        if amount_column in filtered_df.columns:
            total_amount = pd.to_numeric(filtered_df[amount_column], errors='coerce').sum()
        else:
            # 嘗試找到對應的欄位
            if platform == 'official':
                total_amount = pd.to_numeric(filtered_df.get('折扣後金額', 0), errors='coerce').sum()
            elif platform == 'shopee':
                total_amount = pd.to_numeric(filtered_df.get('訂單總金額 (單)', 0), errors='coerce').sum()
            else:
                total_amount = pd.to_numeric(filtered_df.get('末端售價', 0), errors='coerce').sum()

        # 只保留需要的欄位
        output_columns = config['output_columns']
        display_df = filtered_df[[col for col in output_columns if col in filtered_df.columns]].copy()

        # 按日期排序（最新的在前）
        display_df = display_df.sort_values(by=date_column, ascending=False)

        # 產生 HTML 表格
        date_display = '、'.join(selected_dates)
        html_table = generate_html_report(display_df, platform, date_display, total_amount)

        return jsonify({
            'success': True,
            'html': html_table,
            'total_amount': f'{total_amount:,.0f}',
            'row_count': len(filtered_df),
            'dates': selected_dates
        })

    except Exception as e:
        return jsonify({'error': f'產生報表時發生錯誤: {str(e)}'}), 500


def generate_html_report(df, platform, date, total_amount):
    """產生 HTML 報表"""
    config = PLATFORM_CONFIG[platform]
    platform_name = config['name']

    # 處理 NaN 值
    df = df.fillna('')

    # 格式化日期顯示（用於標題）
    # 如果是多個日期，取第一個；如果是單一日期，直接使用
    if '、' in date:
        title_date = date.split('、')[0]
    else:
        title_date = date

    # 轉換日期格式 2026/02/03 -> 02/03
    try:
        date_parts = title_date.split('/')
        short_date = f"{date_parts[1]}/{date_parts[2]}"
    except:
        short_date = title_date

    # 根據平台產生不同標題
    if platform == 'official':
        title = f"官網每日訂單報表{short_date}"
    elif platform == 'shopee':
        title = f"{short_date} 蝦皮訂單"
    else:  # momo
        title = f"{short_date} MOMO訂單"

    # 產生表格 HTML（不使用 pandas to_html，自己建立以加入總計列）
    columns = list(df.columns)

    # 表頭
    header_html = '<tr>' + ''.join([f'<th>{col}</th>' for col in columns]) + '</tr>'

    # 資料列
    rows_html = ''
    for _, row in df.iterrows():
        cells = ''.join([f'<td>{row[col]}</td>' for col in columns])
        rows_html += f'<tr>{cells}</tr>'

    # 總計列（只顯示金額欄位的總計）
    amount_col = config['amount_column']
    total_row_html = '<tr class="total-row">'
    for col in columns:
        if col == columns[0]:
            total_row_html += '<td class="total-label">總計</td>'
        elif col == amount_col:
            total_row_html += f'<td class="total-value">{total_amount:,.0f}</td>'
        else:
            total_row_html += '<td></td>'
    total_row_html += '</tr>'

    html = f'''
    <div class="report-container" id="report-content">
        <div class="report-title">
            <h2>{title}</h2>
        </div>
        <div class="table-wrapper">
            <table class="report-table">
                <thead>{header_html}</thead>
                <tbody>{rows_html}{total_row_html}</tbody>
            </table>
        </div>
    </div>
    '''

    return html


@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup(session_id):
    """清理暫存檔案"""
    try:
        temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{session_id}.pkl')
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})


if __name__ == '__main__':
    print("=" * 50)
    print("DKEC 日報產出工具")
    print("=" * 50)
    print("請在瀏覽器開啟: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服務")
    print("=" * 50)
    app.run(host='127.0.0.1', port=5000, debug=False)

