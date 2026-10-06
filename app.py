import os
import uuid
import boto3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "travelgo-secret-key-change-this"

AWS_REGION = os.getenv("AWS_REGION")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
sns = boto3.client(
    "sns",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

users_table = dynamodb.Table("users")
bookings_table = dynamodb.Table("bookings")

# ---- Mock travel/hotel listings (static data, no need for a 3rd table) ----
LISTINGS = {
    "bus": [
        {"id": "B1", "from": "Hyderabad", "to": "Bangalore", "operator": "Orange Travels", "price": 800, "seats": 40},
        {"id": "B2", "from": "Pune", "to": "Mumbai", "operator": "Neeta Travels", "price": 500, "seats": 35},
    ],
    "train": [
        {"id": "T1", "from": "Delhi", "to": "Mumbai", "operator": "Rajdhani Express", "price": 1500, "seats": 60},
        {"id": "T2", "from": "Chennai", "to": "Bangalore", "operator": "Shatabdi Express", "price": 900, "seats": 50},
    ],
    "flight": [
        {"id": "F1", "from": "Mumbai", "to": "Delhi", "operator": "IndiGo", "price": 4500, "seats": 180},
        {"id": "F2", "from": "Bangalore", "to": "Hyderabad", "operator": "Air India", "price": 3800, "seats": 160},
    ],
    "hotel": [
        {"id": "H1", "city": "Chennai", "name": "Taj Residency", "type": "luxury", "price": 6000},
        {"id": "H2", "city": "Chennai", "name": "Zostel Budget Inn", "type": "budget", "price": 1200},
        {"id": "H3", "city": "Bangalore", "name": "ITC Gardenia", "type": "luxury", "price": 7500},
    ],
}


def send_notification(subject, message):
    """Send an SNS email notification. Fails silently if SNS isn't configured."""
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except Exception as e:
        print("SNS publish failed:", e)


# ---------------- AUTH ----------------

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing = users_table.get_item(Key={"email": email}).get("Item")
        if existing:
            flash("Email already registered. Please login.")
            return redirect(url_for("login"))

        users_table.put_item(Item={
            "email": email,
            "name": name,
            "password": generate_password_hash(password),
        })
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = users_table.get_item(Key={"email": email}).get("Item")
        if user and check_password_hash(user["password"], password):
            session["user"] = email
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- SEARCH / BOOKING ----------------

@app.route("/search")
def search():
    if "user" not in session:
        return redirect(url_for("login"))
    mode = request.args.get("mode", "bus")
    hotel_filter = request.args.get("hotel_type")

    if mode == "hotel":
        results = LISTINGS["hotel"]
        if hotel_filter:
            results = [h for h in results if h["type"] == hotel_filter]
    else:
        results = LISTINGS.get(mode, [])

    return render_template("search.html", mode=mode, results=results)


@app.route("/book", methods=["POST"])
def book():
    if "user" not in session:
        return redirect(url_for("login"))

    mode = request.form["mode"]
    item_id = request.form["item_id"]
    item_name = request.form["item_name"]
    price = request.form["price"]
    seat = request.form.get("seat", "N/A")

    booking_id = str(uuid.uuid4())[:8]
    booking = {
        "booking_id": booking_id,
        "user_email": session["user"],
        "mode": mode,
        "item_id": item_id,
        "item_name": item_name,
        "price": price,
        "seat": seat,
        "status": "confirmed",
        "booked_on": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    bookings_table.put_item(Item=booking)

    send_notification(
        subject="TravelGo Booking Confirmed",
        message=f"Hi {session['name']},\n\nYour {mode} booking for {item_name} "
                f"(Booking ID: {booking_id}) is confirmed. Price: Rs.{price}\n\nThank you for using TravelGo!"
    )

    flash(f"Booking confirmed! Booking ID: {booking_id}")
    return redirect(url_for("dashboard"))


@app.route("/cancel/<booking_id>")
def cancel(booking_id):
    if "user" not in session:
        return redirect(url_for("login"))

    booking = bookings_table.get_item(Key={"booking_id": booking_id}).get("Item")
    if booking and booking["user_email"] == session["user"]:
        bookings_table.update_item(
            Key={"booking_id": booking_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":val": "cancelled"},
        )
        send_notification(
            subject="TravelGo Booking Cancelled",
            message=f"Hi {session['name']},\n\nYour booking (ID: {booking_id}) for "
                    f"{booking['item_name']} has been cancelled."
        )
        flash("Booking cancelled.")
    return redirect(url_for("dashboard"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    response = bookings_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("user_email").eq(session["user"])
    )
    bookings = response.get("Items", [])
    bookings.sort(key=lambda b: b["booked_on"], reverse=True)

    return render_template("dashboard.html", bookings=bookings, name=session.get("name"))


if __name__ == "__main__":
    app.run(debug=True)
