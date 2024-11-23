import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import base64
import requests
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///transactions.db"  # Change to your database URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["CONSUMER_KEY"] = os.getenv("CONSUMER_KEY")
app.config["CONSUMER_SECRET"] = os.getenv("CONSUMER_SECRET")
app.config["SHORTCODE"] = os.getenv("SHORTCODE")
app.config["PASSKEY"] = os.getenv("PASSKEY")
app.config["BASE_URL"] = os.getenv("BASE_URL")

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

# Access token function
def get_access_token():
    endpoint = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        endpoint,
        auth=HTTPBasicAuth(
            app.config["CONSUMER_KEY"], app.config["CONSUMER_SECRET"]
        ),
    )
    return response.json().get("access_token")

# M-Pesa Buy Goods endpoint
@app.route("/buyGoods", methods=["POST"])
def buy_goods():
    data = request.get_json()
    amount = data.get("amount")
    phone_number = data.get("phone_number")
    transaction_id = str(datetime.timestamp(datetime.now()))  # Unique transaction ID

    # Save transaction in database
    new_transaction = Transaction(id=transaction_id, amount=amount, phone_number=phone_number)
    db.session.add(new_transaction)
    db.session.commit()

    # Generate M-Pesa payload
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{app.config['SHORTCODE']}{app.config['PASSKEY']}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode("utf-8")
    access_token = get_access_token()

    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    payload = {
        "BusinessShortCode": app.config["SHORTCODE"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": app.config["SHORTCODE"],
        "PhoneNumber": phone_number,
        "CallBackURL": app.config["BASE_URL"] + "/callback",
        "AccountReference": "Mpesa Integration Api",
        "TransactionDesc": "Test 1",
    }

    response = requests.post(endpoint, json=payload, headers=headers)
    response_data = response.json()
    return jsonify(response_data)

# M-Pesa Callback endpoint
@app.route("/callback", methods=["POST"])
def mpesa_callback():
    data = request.get_json()
    callback = data.get("Body", {}).get("stkCallback", {})
    result_code = callback.get("ResultCode")
    transaction_id = callback.get("CheckoutRequestID")

    if not transaction_id:
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid transaction ID"})

    # Update transaction status in database
    transaction = Transaction.query.filter_by(id=transaction_id).first()
    if transaction:
        transaction.status = "Completed" if result_code == 0 else "Canceled"
        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Callback received"})

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
