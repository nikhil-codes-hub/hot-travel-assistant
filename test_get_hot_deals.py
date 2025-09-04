from agents.user_profile.hot_deals_agent import HotDealsAgent
import asyncio
import json

async def main():
    """Main function to run the scraper and print results."""
    agent = HotDealsAgent()
    deals = await agent.execute("5 AU deals please", 1)
    # Pretty print results
    print(json.dumps(deals, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())