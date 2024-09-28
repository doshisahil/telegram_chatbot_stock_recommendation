# mock_server.py  

from flask import Flask, jsonify, request  

app = Flask(__name__)  

# Mock stock data  
mock_stock_data = {  
    "TCS": {"price": 100, "historical_data": [95, 98, 100, 99, 97]},  
    "INFY": {"price": 200, "historical_data": [190, 195, 200, 198, 197]},  
    "RELIANCE": {"price": 180, "historical_data": [145, 148, 150, 149, 147]},
    "HDFC": {"price": 250, "historical_data": [240, 245, 250, 248, 247]},  
    "ICICI": {"price": 300, "historical_data": [290, 295, 300, 298, 297]},  
}  

@app.route('/api/stock/<string:stock_symbol>', methods=['GET'])  
def get_stock_data(stock_symbol):  
    return jsonify(mock_stock_data.get(stock_symbol, {"error": "Stock not found"}))  

@app.route('/api/order', methods=['POST'])  
def place_order():  
    order_details = request.json  
    return jsonify({"message": f"Order placed for {order_details['stock']} with quantity {order_details['quantity']}"})  

if __name__ == '__main__':  
    app.run(port=5001)