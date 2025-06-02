from flask import Flask, request, redirect, render_template, session, url_for
import pyodbc
import uuid
from pymongo import MongoClient
import boto3
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for session management

# SQL Server connection
sql_conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=database-1.c9uqkcqc8c92.ap-south-1.rds.amazonaws.com;'
    'DATABASE=user_data_db;'
    'UID=admin;'
    'PWD=Madhu789'
)
sql_cursor = sql_conn.cursor()

# MongoDB connection
mongo_client = MongoClient("mongodb://10.0.2.185:27017/")
mongo_db = mongo_client["user_db"]
mongo_collection = mongo_db["addresses"]

# AWS Lambda client for sending OTP
lambda_client = boto3.client('lambda', region_name='ap-south-1')

@app.route('/')
def name_phone_form():
    # Step 1: Simple form with name + phone only (no DB store)
    return render_template('name_phone_form.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    name = request.form['name']
    phone = request.form['phone']

    # Save name and phone temporarily in session for next steps
    session['name'] = name
    session['phone'] = phone

    # Trigger Lambda to send OTP (async)
    payload = { "phone_number": phone }
    try:
        lambda_client.invoke(
            FunctionName="sdfghjk",  # Replace with your Lambda function name
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
    except Exception as e:
        return f"Error sending OTP: {e}", 500

    return redirect(url_for('verify_otp'))

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        # For now hardcoding OTP as "123890"
        if entered_otp == "123890":
            return redirect(url_for('food_order_form'))
        else:
            return "OTP mismatch. Please try again.", 401
    return render_template('otp_verify.html')

@app.route('/food_order', methods=['GET', 'POST'])
def food_order_form():
    if request.method == 'POST':
        # Collect all food order details + save in DB

        user_id = str(uuid.uuid4())

        # Get form data
        email = request.form['email']
        password = request.form['password']
        restaurant = request.form['restaurant']
        food_item = request.form['food_item']
        quantity = request.form['quantity']
        payment_method = request.form['payment_method']
        address = request.form['address']
        suggestions = request.form['suggestions']

        # Get name and phone from session
        name = session.get('name')
        phone = session.get('phone')

        if not (name and phone):
            return "Session expired. Please start over.", 400

        # Insert into SQL Server
        try:
            sql_cursor.execute("""
                INSERT INTO users (id, name, phone, email, password, restaurant, food_item, quantity, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, phone, email, password, restaurant, food_item, quantity, payment_method))
            sql_conn.commit()
        except Exception as e:
            return f"SQL Insert Error: {e}", 500

        # Insert address and suggestions into MongoDB
        try:
            mongo_collection.insert_one({
                '_id': user_id,
                'address': address,
                'suggestions': suggestions
            })
        except Exception as e:
            return f"MongoDB Insert Error: {e}", 500

        # Clear session
        session.clear()

        return redirect(url_for('user_details', user_id=user_id))

    return render_template('food_order_form.html')

@app.route('/user/<user_id>')
def user_details(user_id):
    # Fetch user info from SQL Server
    sql_cursor.execute("""
        SELECT name, phone, email, password, restaurant, food_item, quantity, payment_method
        FROM users WHERE id = ?
    """, (user_id,))
    row = sql_cursor.fetchone()

    if row:
        name = row.name
        phone = row.phone
        email = row.email
        password = row.password
        restaurant = row.restaurant
        food_item = row.food_item
        quantity = row.quantity
        payment_method = row.payment_method
    else:
        return "User not found", 404

    # Fetch address and suggestions from MongoDB
    doc = mongo_collection.find_one({'_id': user_id})
    address = doc.get('address', 'Not Found') if doc else 'Not Found'
    suggestions = doc.get('suggestions', 'Not Found') if doc else 'Not Found'

    return render_template('details.html',
        user_id=user_id,
        name=name,
        phone=phone,
        email=email,
        password=password,
        restaurant=restaurant,
        food_item=food_item,
        quantity=quantity,
        payment_method=payment_method,
        address=address,
        suggestions=suggestions
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
