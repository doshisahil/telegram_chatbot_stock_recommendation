import logging
import asyncio
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta

import config

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global stock list
stock_list = ['TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'RELIANCE.NS', 'ICICIBANK.NS']  # Use Yahoo Finance tickers


# def fetch_stock_data(stock):
#     try:
#         stock_data = yf.Ticker(stock)
#         current_price = stock_data.history(period='1d')['Close'].iloc[-1]
#         historical_data = stock_data.history(period='1mo')['Close'].iloc[0]
#         return current_price, historical_data
#     except Exception as e:
#         logger.error(f"Error fetching data for {stock}: {e}")
#         return None, None

def fetch_stock_data(stock):
    try:
        stock_data = yf.Ticker(stock)

        # Fetch current price
        current_price = stock_data.history(period='1d')['Close'].iloc[-1]

        # Calculate the date one month ago
        one_month_ago = datetime.now() - timedelta(days=15)

        # Fetch historical price from exactly one month ago
        historical_data = stock_data.history(start=one_month_ago, end=one_month_ago + timedelta(days=1))['Close'].iloc[
            0]

        return current_price, historical_data
    except Exception as e:
        logger.error(f"Error fetching data for {stock}: {e}")
        return None, None
async def evaluate_top_losers(stocks, top_n):
    loser_stocks = {}
    for stock in stocks:
        current_price, historical_price = await asyncio.to_thread(fetch_stock_data, stock)
        if current_price is not None and historical_price is not None:
            percent_change = (current_price - historical_price) / historical_price
            loser_stocks[stock] = percent_change

    sorted_losers = sorted(loser_stocks.items(), key=lambda x: x[1])
    return sorted_losers[:top_n], sorted(loser_stocks.items(), key=lambda x: x[1])


async def recommend_buys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        corpus = float(context.args[0])
        top_n = int(context.args[1]) if len(context.args) > 1 else 5  # Default to top 5 losers
        losers, all_drops = await evaluate_top_losers(stock_list, top_n)

        if not losers:
            await update.message.reply_text("No stocks to recommend for buying.")
            return

        investment_per_stock = corpus / len(losers)
        recommendations = ["*Percentage Drop Analysis for All Stocks:*"]
        for stock, drop in all_drops:
            change_type = "dropped" if drop < 0 else "gained"
            recommendations.append(f"{stock}: {abs(drop) * 100:.2f}% {change_type}")

        recommendations.append("\n*Buy Recommendations:*")
        total_investment = 0
        for stock, _ in losers:
            current_price, _ = await asyncio.to_thread(fetch_stock_data, stock)
            if current_price is not None:
                quantity = int(investment_per_stock // current_price)
                total_for_stock = quantity * current_price
                total_investment += total_for_stock
                recommendations.append(
                    f"Buy {quantity} of {stock} at {current_price:.2f} (Total: {total_for_stock:.2f})")

        recommendations.append(f"\n*Total Investment: {total_investment:.2f}*")
        await update.message.reply_text("\n".join(recommendations), parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a valid amount and optionally the number of top losers to pick. Usage: /buy <amount> [top_n]")


def main():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("buy", recommend_buys))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()