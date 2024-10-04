import re
from playsound import playsound
import requests
from bs4 import BeautifulSoup
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
LOGIN_URL = "https://www.schedule2drive.com/index.php"
STUDENT_PAGE_URL = "https://www.schedule2drive.com/student.php"
USER_DATA = {
    'state': 'MN',
    'permit_number': 'UserName',
    'birthdate': '01/01/1970'  # Format MM/DD/YYYY
}
EMAIL_SENDER = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_password'  # Use an app-specific password if 2FA is enabled
EMAIL_RECIPIENT = 'your_emailgmail.com'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': LOGIN_URL,
    'Origin': 'https://www.schedule2drive.com',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

# Helper function to split birthdate into day, month, and year
def split_birthdate(birthdate):
    month, day, year = birthdate.split('/')
    return month, day, year

# Debug function to print response details
def print_response_details(response):
    print("Status Code:", response.status_code)
    print("Cookies:", response.cookies)
    print("Headers:", response.headers)
    print("Text Snippet:", response.text[:500])  # Print first 500 characters for context

# Authenticate to Schedule2Drive
def login(session):
    # Split the birthdate into month, day, and year
    month, day, year = split_birthdate(USER_DATA['birthdate'])

    # Prepare the form data based on the actual HTML structure, including the hidden field
    login_data = {
        'inputLoginState': USER_DATA['state'],        # State input from the select box
        'inputLoginPermit': USER_DATA['permit_number'],  # Permit number input
        'inputLoginMonth': month,  # Month of birth (MM)
        'inputLoginDay': day,      # Day of birth (DD)
        'inputLoginYear': year,    # Year of birth (YYYY)
        '_event[submitStudent]': '_event[submitStudent]',  # Hidden field added by JS
        'submitButton': 'Login'  # Simulate a form submit button
    }

    # Send the POST request with login details to the form action URL (/index.php)
    try:
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        print("Login Response Details:")
        print_response_details(response)
    except requests.RequestException as e:
        print(f"Login failed due to network error: {e}")
        return False

    # Check if the login was successful
    if "Welcome" in response.text or response.status_code == 200:
        print("Login successful!")
        return True
    else:
        print("Login failed.")
        return False

# Extract cToken from the "Schedule Drives" link in the student page
def get_token(session):
    try:
        response = session.get(STUDENT_PAGE_URL, headers=headers)
    except requests.RequestException as e:
        print(f"Failed to retrieve student page: {e}")
        return None

    # Debugging: Check if we're being redirected to login
    if response.status_code == 200 and 'url=/index.php' in response.text:
        print("Redirected back to login page. Session may not be maintained.")
        return None

    print("Student Page Response Details:")
    print_response_details(response)

    # Parse the HTML of the student page
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the "Schedule Drives" link in the page
    schedule_link = soup.find('a', href=True, text='Schedule Drives')
    if schedule_link:
        href = schedule_link['href']
        token = href.split('cToken=')[1] if 'cToken=' in href else None
        if token:
            print(f"Extracted cToken: {token}")
            return token

    print("cToken not found in the page.")
    return None

# Function to send email notification
def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECIPIENT
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Check calendar for "Open Slots" or <div class="open">
def check_calendar(session, token):
    calendar_url = f"https://www.schedule2drive.com/student.php?sessCal=1&cToken={token}"

    try:
        response = session.get(calendar_url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
    except requests.RequestException as e:
        print(f"Failed to retrieve calendar page: {e}")
        return False  # Return False if the HTTP request fails

    soup = BeautifulSoup(response.text, 'html.parser')
    open_slots = soup.find_all('a', string=re.compile(r'^open slot', re.IGNORECASE))

    if open_slots:
        print(f"Found {len(open_slots)} open slots!")
        for slot in open_slots:
            print(slot.text.strip())
        send_email("Open Slots Found!", f"Found {len(open_slots)} open slots!")
        playsound('/Users/claudiacalderas/Documents/python/driversed/ludwig-van-beethoven-moonlight-sonata.mp3')
        return True
    else:
        print("No open slots found.")
        return True  # Return True if the request is successful but no slots are found

# Main function to run the program
def main():
    while True:
        with requests.Session() as session:
            session.headers.update(headers)
            if not login(session):
                print("Login failed, retrying after a short delay...")
                time.sleep(10)
                continue

            token = get_token(session)
            if not token:
                print("Failed to retrieve token, retrying after a short delay...")
                time.sleep(10)
                continue

            # Check calendar and handle failures
            while True:
                success = check_calendar(session, token)
                if not success:
                    print("Check failed, creating new session and restarting...")
                    break  # Exit the inner loop to restart session

                wait_time = random.randint(10, 30)
                print(f"Waiting for {wait_time} seconds before the next check.")
                time.sleep(wait_time)

if __name__ == "__main__":
    main()

