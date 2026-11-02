
# -*- coding: utf-8 -*-
"""
00981A 統一投信：歷史持股資料測試
測試期間：2025/07/01 ～ 2025/07/10

輸出：
1. output/00981A_holdings.csv
2. output/00981A_checks.csv

注意：
PCF 資料不一定等同完整實際投資組合。
"""

import csv
import datetime as dt
import os
import re
import time

import requests


# ===== 基本設定 =====

PAGE = "https://www.ezmoney.com.tw/ETF/Transaction/PCF"
API = "https://www.ezmoney.com.tw/ETF/Transaction/GetPCF"

ETF_CODE = "00981A"
FUND_CODE = "49YTW"

START = dt.date(2025, 7, 1)
END = dt.date(2026, 10, 1)

TAIWAN_TZ = dt.timezone(dt.timedelta(hours=8))

os.makedirs("output", exist_ok=True)


# ===== 日期解析 =====

def parse_dotnet_date(raw):
    """
    將 .NET 日期轉換為台灣時間。

    回傳：
    (日期 YYYY-MM-DD, 原始時間戳記)

    若為無效日期，回傳 (None, 原始值)。
    """

    raw = str(raw or "")

    match = re.search(
        r"/Date\((-?\d+)([+-]\d{4})?\)/",
        raw
    )

    if not match:
        return None, raw

    milliseconds = int(match.group(1))

    # 排除 .NET 預設空日期
    if milliseconds <= -62135596800000:
        return None, raw

    try:
        parsed = dt.datetime.fromtimestamp(
            milliseconds / 1000,
            tz=TAIWAN_TZ
        )

        return parsed.date().isoformat(), raw

    except (ValueError, OverflowError, OSError):
        return None, raw


# ===== 建立連線 =====

session = requests.Session()

session.get(
    PAGE,
    timeout=30
).raise_for_status()


# ===== 開始查詢 =====

records = []
checks = []

query_date = START

while query_date <= END:

    query_date_str = query_date.isoformat()

    roc_date = (
        f"{query_date.year - 1911}/"
        f"{query_date.month:02d}/"
        f"{query_date.day:02d}"
    )

    status = "OK"
    actual_date = ""
    raw_timestamp = ""
    stock_count = 0

    try:

        response = session.post(
            API,
            json={
                "fundCode": FUND_CODE,
                "date": roc_date,
                "specificDate": True
            },
            headers={
                "Referer": PAGE
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        # ===== 取得 PCF 日期 =====

        pcf = data.get("pcf") or []

        if not pcf:
            raise ValueError("No PCF metadata")

        raw_date = pcf[0].get("TranDate", "")

        actual_date, raw_timestamp = (
            parse_dotnet_date(raw_date)
        )

        if not actual_date:
            status = "INVALID_DATE"

        else:

            # ===== 取得股票明細 =====

            stocks = [
                stock
                for asset in (data.get("asset") or [])
                if asset.get("AssetCode") == "ST"
                for stock in (asset.get("Details") or [])
            ]

            stock_count = len(stocks)

            if stock_count == 0:
                status = "EMPTY"

            else:

                # 日期差異僅標記，不擅自修正
                date_difference = (
                    dt.date.fromisoformat(actual_date)
                    - query_date
                ).days

                if abs(date_difference) > 3:
                    status = "CHECK_DATE"

                # ===== 儲存持股 =====

                for stock in stocks:

                    records.append({
                        "query_date": query_date_str,
                        "data_date": actual_date,
                        "raw_timestamp": raw_timestamp,
                        "etf": ETF_CODE,
                        "stock_code": stock.get(
                            "DetailCode"
                        ),
                        "stock_name": stock.get(
                            "DetailName"
                        ),
                        "shares": stock.get(
                            "Share"
                        ),
                        "market_value": stock.get(
                            "Amount"
                        ),
                        "weight_pct": stock.get(
                            "NavRate"
                        )
                    })

    except Exception as exc:

        status = f"ERROR: {exc}"

    # ===== 輸出查詢結果 =====

    print(
        query_date_str,
        actual_date,
        stock_count,
        status
    )

    checks.append({
        "query_date": query_date_str,
        "data_date": actual_date,
        "raw_timestamp": raw_timestamp,
        "stock_count": stock_count,
        "status": status
    })

    query_date += dt.timedelta(days=1)

    # 降低查詢頻率
    time.sleep(1)


# ===== 輸出持股 CSV =====

holdings_file = "output/00981A_holdings.csv"

with open(
    holdings_file,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    fields = [
        "query_date",
        "data_date",
        "raw_timestamp",
        "etf",
        "stock_code",
        "stock_name",
        "shares",
        "market_value",
        "weight_pct"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(records)


# ===== 輸出檢核 CSV =====

checks_file = "output/00981A_checks.csv"

with open(
    checks_file,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    fields = [
        "query_date",
        "data_date",
        "raw_timestamp",
        "stock_count",
        "status"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(checks)


# ===== 結果摘要 =====

print("\n===== 00981A 歷史資料測試完成 =====")

print(f"查詢期間：{START} ～ {END}")
print(f"查詢天數：{len(checks)}")
print(f"持股紀錄：{len(records)}")

valid_dates = {
    row["data_date"]
    for row in checks
    if row["data_date"]
    and row["stock_count"] > 0
}

print(f"有效資料日期數：{len(valid_dates)}")

print("輸出檔案：")
print(holdings_file)
print(checks_file)

print("注意：資料日期仍需與官方公告核對。")

