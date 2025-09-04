from playwright.async_api import async_playwright
import json
import asyncio

async def scrape_houseoftravel_deals():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.houseoftravel.co.nz/deals/search", timeout=60000)
        await page.wait_for_selector("div", timeout=30000)

        # Use a more robust selector for the deal cards
        deal_cards = await page.query_selector_all("div._deal-card")
        results = []

        for i, card in enumerate(deal_cards, start=1):
            # Using more specific and resilient selectors based on the provided HTML structure
            title_element = await card.query_selector("xpath=.//div[2]/div[2]/h3")
            airline_element = await card.query_selector("xpath=.//span[contains(text(), 'Flying with')]/following-sibling::span[2]")
            price_element = await card.query_selector("xpath=.//span[contains(@class, '_heading-3') or contains(@class, '_heading-2')]")
            destination_element = await card.query_selector("xpath=.//div[2]/div[1]/span")
            info_element = await card.query_selector("xpath=.//div[2]/div[4]")

            deal = {
                "title": (await title_element.inner_text()) if title_element else None,
                "airline": (await airline_element.inner_text()) if airline_element else None,
                "price": (await price_element.inner_text()) if price_element else None,
                "destination": (await destination_element.inner_text()) if destination_element else None,
                "info": (await info_element.inner_text()) if info_element else None,
            }
            if title_element and airline_element and price_element and destination_element and info_element:
                results.append(deal)

        await browser.close()
        return results

async def main():
    """Main function to run the scraper and print results."""
    deals = await scrape_houseoftravel_deals()
    # Pretty print results
    print(json.dumps(deals, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())