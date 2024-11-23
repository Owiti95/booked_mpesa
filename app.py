import os

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request
from datetime import datetime
import base64
import requests

from requests.auth import HTTPBasicAuth


app = Flask(__name__)


app.config["CONSUMER_KEY"] = os.getenv("CONSUMER_KEY")
app.config["CONSUMER_SECRET"] = os.getenv("CONSUMER_SECRET")
app.config["SHORTCODE"] = os.getenv("SHORTCODE")
app.config["PASSKEY"] = os.getenv("PASSKEY")
app.config["BASE_URL"] = os.getenv("BASE_URL")

customer_key = 'jGBDe11Bk9ahuSyJAU0D1qkGKWdTqS4ced54E0tbKk7mPw8H'
customer_secret = "Xs7zns3ZseZMkGT6fNOU3D6WCc3YU2HDja7ZHJVGLlLVsYhOBmLkfHKJwFRAAq4S"


@app.route("/")
def hello():
    return"<p>Hello World</p>"


# def get_access_token():
#     endpoint = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
#     response = requests.get(endpoint,auth=HTTPBasicAuth(
#         app.config["CONSUMER_KEY"], app.config["CONSUMER_SECRET"]
#     ))
    
#     return response.json().get("acces_token")


def get_access_token():

    endpoint = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        endpoint,
        auth=HTTPBasicAuth(
           customer_key, customer_secret
        ),
    )
    return response.json().get("access_token")


@app.route("/buyGoods",methods=['POST'])
def buyGoods():
    
    data = request.get_json()
    
    amount = data.get("amount")
    phone_number = data.get("phone_number")
    
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    pasword_str = f"{app.config['SHORTCODE']}{app.config['PASSKEY']}{timestamp}"
    
    password = base64.b64encode(pasword_str.encode()).decode("utf-8")
    
    acces_token = get_access_token()
    
    print(acces_token)
    
    
    headers = {"Authorization":f"Bearer {acces_token}"}
    
    
    endpoint = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    payload = {    
        "BusinessShortCode": "174379",    
        "Password": password,    
        "Timestamp": timestamp,    
        "TransactionType": "CustomerPayBillOnline",    
        "Amount": "1",    
        "PartyA":"254748292218",    
        "PartyB":"174379",    
        "PhoneNumber":phone_number,    
        "CallBackURL": app.config["BASE_URL"] + "/callback",    
        "AccountReference":"Mpesa Integration Api",    
        "TransactionDesc":"Test 1"
    }
    
    response = requests.post(endpoint,json=payload, headers=headers)
    
    response_data =response.json()

    return jsonify(response_data)



@app.route("/callback")

def mpesa_callback():
    data = request.get_json()
    callback = data.get("Body", {}).get("stkCallback", {})
    result_code = callback.get("ResultCode")
    transaction_id = callback.get("CheckoutRequestID")
    
    if transaction_id :
        return jsonify({"ResultCode": 1 , "ResultDesc": "Invalid transaction ID"})
    
    transaction = Transaction.query.filter_by(id=transaction_id).first()
    if transaction:
        transaction.status = "Completed" if result_code == 0 else "Canceled"
        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Callback received"})

    
   
    