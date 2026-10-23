import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def scrape_el_paso_foreclosure_map():
    url = "https://epcountytx.gov"
    parsed_records = []
    
    async with async_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()

        intercepted_json_feeds = []
        async def handle_response(response):
            if "query" in response.url or "FeatureServer" in response.url or "getForeclosures" in response.url:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        data = await response.json()
                        intercepted_json_feeds.append(data)
                except Exception:
                    pass

        page.on("response", handle_response)
        await page.goto(url, wait_until="networkidle")

        accept_button = page.locator("text=Accept")
        if await accept_button.count() > 0:
            await accept_button.click()
            await page.wait_for_timeout(5000) 

        for feed in intercepted_json_feeds:
            features = feed.get("features", feed.get("rows", []))
            for item in features:
                props = item.get("attributes", item)
                record = {
                    "instrument_number": str(props.get("InstrumentNo") or props.get("DOC_NUM") or "UNKNOWN"),
                    "sale_date": props.get("SaleDate") or props.get("DATE_OF_SALE") or "UNKNOWN",
                    "borrower_name": props.get("BorrowerName") or props.get("GRANTOR") or "UNKNOWN",
                    "original_loan_amount": f"${props.get('Amount', 0):,}" if props.get('Amount') else "UNKNOWN",
                    "deed_of_trust_execution_date": props.get("DeedDate") or "UNKNOWN",
                    "property_address": props.get("PropertyAddress") or props.get("SITUS_ADDR") or "UNKNOWN",
                    "market_value": "PENDING_MANUAL_COMPS", 
                    "property_liens": "FLAG_FOR_TITLE_SEARCH",
                    "date_synced": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                parsed_records.append(record)

        await browser.close()
    return parsed_records

if __name__ == "__main__":
    records = asyncio.run(scrape_el_paso_foreclosure_map())
    if records:
        with open("data.json", "w") as f:
            json.dump(records, f, indent=4)
        print(f"Successfully generated data.json with {len(records)} active notices.")
    else:
        print("No dynamic notice entries found today.")
