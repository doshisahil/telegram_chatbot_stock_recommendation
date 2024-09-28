# main_app.py

import requests
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from datetime import timedelta
import config

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_URL = config.API_URL  # URL for the real API in production
TOTAL_INVESTMENT = 10000
STOCK_LIST = ['TCS', 'INFY', 'RELIANCE', 'HDFC', 'ICICI']
INVESTMENT_PERIOD = 15  # in days
PROFIT_TARGET = 0.03  # 3% profit target

# Global variables
buy_prices = {}
liquid_money = TOTAL_INVESTMENT

async def fetch_stock_data(stock):
    response = await asyncio.to_thread(requests.get, f"{API_URL}/stock/{stock}")
    return response.json()

async def place_order(stock, quantity, order_type):
    order_details = {
        "stock": stock,
        "quantity": quantity,
        "order_type": order_type
    }
    response = await asyncio.to_thread(requests.post, f"{API_URL}/order", json=order_details)
    return response.json()

async def evaluate_top_losers(stocks):
    loser_stocks = {}
    for stock in stocks:
        data = await fetch_stock_data(stock)
        historical_data = data['historical_data']
        percent_change = (data['price'] - historical_data[0]) / historical_data[0]
        loser_stocks[stock] = percent_change

    sorted_losers = sorted(loser_stocks.items(), key=lambda x: x[1])
    return [stock[0] for stock in sorted_losers[:5]]

async def buy_stocks(loser_stocks):
    global liquid_money
    if not loser_stocks:
        return "No stocks to buy."
    investment_per_stock = liquid_money / len(loser_stocks)
    report = []
    for stock in loser_stocks:
        data = await fetch_stock_data(stock)
        current_price = data['price']
        quantity = int(investment_per_stock // current_price)
        if quantity > 0:
            await place_order(stock, quantity, "BUY")
            buy_prices[stock] = current_price
            liquid_money -= quantity * current_price
            report.append(f"Bought {quantity} of {stock} at {current_price}")
    return "\n".join(report) if report else "No stocks were bought."

async def check_and_sell():
    global liquid_money
    report = []
    for stock, buy_price in list(buy_prices.items()):
        data = await fetch_stock_data(stock)
        current_price = data['price']
        if (current_price - buy_price) / buy_price >= PROFIT_TARGET:
            await place_order(stock, 1, "SELL")  # Assuming selling all held stocks
            liquid_money += current_price
            report.append(f"Sold {stock} at {current_price}")
            del buy_prices[stock]
    return "\n".join(report) if report else "No stocks were sold."

async def periodic_buying(context: ContextTypes.DEFAULT_TYPE):
    losers = await evaluate_top_losers(STOCK_LIST)
    report = await buy_stocks(losers)
    await context.bot.send_message(chat_id=context.job.chat_id, text=f"Periodic Buying Report:\n{report}")

async def periodic_selling(context: ContextTypes.DEFAULT_TYPE):
    report = await check_and_sell()
    if report:
        await context.bot.send_message(chat_id=context.job.chat_id, text=f"Periodic Selling Report:\n{report}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id == config.TELEGRAM_CHAT_ID:
        await update.message.reply_text("Welcome to the Stock Trading Bot! Use /help to see available commands.")
    else:
        await update.message.reply_text("Sorry you are not allowed to access this service.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """  
    Available commands:  
    /start - Start the bot  
    /help - Show this help message  
    /report - Get current portfolio report  
    /buy - Trigger manual buying  
    /sell - Trigger manual selling  
    """
    await update.message.reply_text(help_text)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = f"Current Liquid Money: {liquid_money}\n\nCurrent Holdings:"
    for stock, price in buy_prices.items():
        data = await fetch_stock_data(stock)
        current_price = data['price']
        profit_percent = (current_price - price) / price * 100
        report += f"\n{stock}: Bought at {price}, Current Price: {current_price}, Profit: {profit_percent:.2f}%"
    await update.message.reply_text(report)

async def manual_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    losers = await evaluate_top_losers(STOCK_LIST)
    report = await buy_stocks(losers)
    await update.message.reply_text(f"Manual Buying Report:\n{report}")

async def manual_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = await check_and_sell()
    await update.message.reply_text(f"Manual Selling Report:\n{report}")

def main():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("buy", manual_buy))
    application.add_handler(CommandHandler("sell", manual_sell))

    # Initialize and set up the job queue
    job_queue = JobQueue()
    job_queue.set_application(application)

    # Schedule periodic tasks
    job_queue.run_repeating(periodic_buying, interval=timedelta(days=INVESTMENT_PERIOD), first=10)
    job_queue.run_repeating(periodic_selling, interval=timedelta(minutes=1), first=10)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()