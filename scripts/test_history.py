
import csv
import datetime as dt
import os
import re
import time

import requests

PAGE = "https://www.ezmoney.com.tw/ETF/Transaction/PCF"
API = "https://www.ezmoney.com.tw/ETF/Transaction/GetPCF"
FUND = "49YTW"
START = dt.date(2025, 7, 1)
END = dt.date(2025, 7, 10)

os.makedirs("output", exist_ok=True)

session = requests.Session()
session.get(PAGE, timeout=30).raise_for_status()

records = []
checks = []
date = START

while date <= END:
    roc = f"{date.year - 1911}/{date.month:02d}/{date.day:02d}"
    status = "OK"
    actual_date = ""
    count = 0

    try:
        response = session.post(
            API,
            json={
                "fundCode": FUND,
                "date": roc,
                "specificDate": True,
            },
            headers={"Referer": PAGE},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        pcf = data.get("pcf") or []
        if not pcf:
            raise ValueError("No PCF metadata")

        raw = pcf[0].get("TranDate", "")
        match = re.search(r"/Date\((\d+)", str(raw))
        if not match:
            raise ValueError(f"Unknown date format: {raw}")

        timestamp = int(match.group(1)) / 1000
        actual_date = dt.datetime.fromtimestamp(
            timestamp, tz=dt.timezone.utc
        ).date().isoformat()

        stocks = [
            item
            for asset in (data.get("asset") or [])
            if asset.get("AssetCode") == "ST"
            for item in (asset.get("Details") or [])
        ]

        count = len(stocks)
        if not stocks:
            status = "EMPTY"

        for stock in stocks:
            records.append({
                "query_date": date.isoformat(),
                "data_date": actual_date,
                "etf": "00981A",
                "stock_code": stock.get("DetailCode"),
                "stock_name": stock.get("DetailName"),
                "shares": stock.get("Share"),
                "market_value": stock.get("Amount"),
                "weight_pct": stock.get("NavRate"),
            })

    except Exception as exc:
        status = f"ERROR: {exc}"

    print(date.isoformat(), actual_date, count, status)
    checks.append([date.isoformat(), actual_date, count, status])

    date += dt.timedelta(days=1)
    time.sleep(1)

with open("output/00981A_holdings.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "query_date", "data_date", "etf",
        "stock_code", "stock_name", "shares",
        "market_value", "weight_pct",
    ])
    writer.writeheader()
    writer.writerows(records)

with open("output/00981A_checks.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["query_date", "data_date", "stock_count", "status"])
    writer.writerows(checks)

print(f"完成：{len(records)} 筆持股紀錄")
