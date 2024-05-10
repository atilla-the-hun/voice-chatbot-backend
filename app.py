from flask import Flask, request, send_file, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI
from groq import Groq
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import schedule
import threading
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Groq and OpenAI clients with environment variables
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

history_messages = []

# Function to save responses to a file
def save_to_file(user_text, ai_response):
    try:
        with open("chat_logs.txt", "a") as file:
            file.write(f"User: {user_text}\n")
            file.write(f"AI: {ai_response}\n\n")
    except Exception as e:
        print("Error writing to file:", e)

# Initial message from the chatbot
INIT_MESSAGE = {
    "role": "assistant",
    "content": """
        Do not make up any of your own information or details.
        Ask for the user's name, email address and phone number and any message the user 
        would like to send after the first question the user asks is answered.
        Refuse to answer any questions not related to Zoltan's professional services. 
        You are a sales service rep for an artificial intelligence 
        and web development specialist named Zoltan. You have a friendly 
        manner and answer any questions related to the services Zoltan provides.
        Refuse to answer any questions not related to Zoltan's professional services.
        Request the user's name, email address and phone number and any message the user 
        would like to send to Zoltan. 
        Custom coding and AI solutions.
        Whether you are looking to build a new website, an app for your business
        or need help with existing code, Zoltan can help.
        Are you seeking a highly skilled and versatile professional
        to revolutionize your company's online presence and drive
        innovation through AI-powered applications?
        Zoltan specializes in solving complex coding problems, providing solutions 
        that are tailored to meet unique needs. His mission is to help users discover
        and leverage the very best resources in the field of artificial intelligence. 
        He has experience working with the following:
        HTML, CSS, Javascript, Typescript and Python.
        His primary spoken and written languages are English being his home 
        and first language and secondary language being Afrikaans.
        The following projects showcase some of his skills and experience through real-world 
        examples of his work. It reflects his ability to solve complex problems, work with different technologies, 
        and manage projects effectively. Only respond with the information below about each specific project. 
        Do not respond with any details other than what is given here. Do not make up details about the project.
        Display the following link to the user:
        <a href="https://summit-medical-solutions.vercel.app" target="_blank">Summit Medical Solutions</a>
        Summit Medical Solutions: Built using Typescript, Javascript, CSS and HTML
    """,
}
history_messages.append(INIT_MESSAGE)

@app.route('/synthesize-speech', methods=['POST'])
def synthesize_speech():
    data = request.json
    text = data['text']
    sound = "output.mp3"
    
    voice_response = openai_client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )

    voice_response.stream_to_file(sound)
    
    return send_file(sound, mimetype="audio/mpeg")

@app.route('/process-speech', methods=['POST'])
def process_speech():
    data = request.json
    user_text = data['text']
    history_messages.append({"role": "user", "content": user_text})
    
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=history_messages,
    )
    ai_response = completion.choices[0].message.content
    history_messages.append({"role": "assistant", "content": ai_response})

    # Save user input and AI response to file
    save_to_file(user_text, ai_response)

    return jsonify({'response': ai_response})

@app.route('/start-speech', methods=['POST'])
def start_speech():
    global history_messages
    history_messages = []  # Reset message history
    history_messages.append(INIT_MESSAGE)  # Re-append the initial message
    return jsonify({'response': 'OK'})

def send_email():
    sender_email = os.getenv("EMAIL_SENDER")
    receiver_email = os.getenv("EMAIL_RECEIVER")
    api_key = os.getenv("EMAIL_API_KEY")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Daily Chat Logs"

    # Read the content of chat_logs.txt
    with open("chat_logs.txt", "r") as file:
        body = file.readlines()  # Read lines to preserve formatting

    # Use HTML formatting for the email body
    html_body = "<html><body>"
    for line in body:
        html_body += f"<p>{line}</p>"  # Wrap each line in a paragraph tag
    html_body += "</body></html>"

    message.attach(MIMEText(html_body, "html"))

    # Send email using SMTP
    try:
        server = smtplib.SMTP('smtp.elasticemail.com', 587)
        server.starttls()
        server.login(sender_email, api_key)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
        
        # Clear the chat_logs.txt file after sending email
        with open("chat_logs.txt", "w") as file:
            file.truncate(0)
            print("Chat log file cleared successfully!")
            
    except Exception as e:
        print("Error sending email:", e)
    finally:
        server.quit()

# Schedule email sending once a day
schedule.every().day.at("17:51").do(send_email)  # Adjust the time as needed

# Route for serving the index.html file
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Start the Flask app in a separate thread without the reloader
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000, 'debug': True, 'use_reloader': False}).start()

    # Run the schedule in the main thread
    while True:
        schedule.run_pending()
        time.sleep(1)