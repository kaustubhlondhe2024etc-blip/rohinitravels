[README.md](https://github.com/user-attachments/files/33126680/README.md)
# TravelGo: A Cloud-Powered Real-Time Travel Booking Platform

TravelGo is a full-stack, cloud-based travel booking platform that lets users search and book buses, trains, flights, and hotels through a unified interface, with real-time email confirmations.

## Tech Stack
- **Backend:** Flask (Python)
- **Database:** Amazon DynamoDB
- **Notifications:** Amazon SNS (email)
- **Hosting:** Amazon EC2
- **Frontend:** HTML, CSS, Jinja2 templates

## Features
- User registration and login with secure password hashing
- Search and browse buses, trains, flights, and hotels (with luxury/budget filtering)
- Seat selection for bus bookings
- Real-time booking confirmation and cancellation emails via AWS SNS
- Personal dashboard showing booking history with cancellation management

## Architecture
1. **Flask** handles all backend routes — auth, search, booking, cancellation, dashboard.
2. **DynamoDB** stores two tables:
   - `users` — partition key `email`
   - `bookings` — partition key `booking_id`
3. **SNS** publishes a notification every time a booking is confirmed or cancelled, which triggers an email to the user.
4. **EC2** hosts the deployed Flask app (if applicable).

## Setup Instructions
1. Clone this repo
2. Create a `.env` file with:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   SNS_TOPIC_ARN=your_topic_arn
   ```
3. Install dependencies: `pip install flask boto3 python-dotenv`
4. Create DynamoDB tables `users` (PK: `email`) and `bookings` (PK: `booking_id`)
5. Create an SNS topic and subscribe your email
6. Run: `python app.py`
7. Visit `http://127.0.0.1:5000`

## Scenarios Covered
- **Scenario 1:** Unified multi-mode travel booking (bus/train/flight/hotel search and booking)
- **Scenario 2:** Real-time booking confirmation via AWS SNS email notifications
- **Scenario 3:** Dynamic dashboard with personal travel history and cancellation
