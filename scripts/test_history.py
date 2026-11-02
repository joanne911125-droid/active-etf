
import datetime
import json
import requests

PAGE = "https://www.ezmoney.com.tw/ETF/Transaction/PCF"
API = "https://www.ezmoney.com.tw/ETF/Transaction/GetPCF"

session = requests.Session()
session.get(PAGE, timeout=30).raise_for_status()

dates = ["114/08/01", "114/12/31", "115/06/30"]

for date in dates:
    print(f"\n查詢 00981A：{date}")

    try:
        response = session.post(
            API,
            json={
                "fundCode": "49YTW",
                "date": date,
                "specificDate": True
            },
            headers={"Referer": PAGE},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        pcf = data.get("pcf") or []
        assets = data.get("asset") or []
        stocks = [
            row
            for asset in assets
            if asset.get("AssetCode") == "ST"
            for row in (asset.get("Details") or [])
        ]

        print("回傳日期：", pcf[0].get("TranDate") if pcf else "無")
        print("股票筆數：", len(stocks))
        print("前兩筆股票：", stocks[:2])

    except Exception as e:
        print("查詢失敗：", str(e))
