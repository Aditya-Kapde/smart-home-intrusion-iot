from flask import Flask
from flask_mail import Mail,Message 
import os
import dotenv

dotenv.load.dotenv()

app = Flask(__name__)
mail = Mail(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = True

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        msg = Message(
            'Hello',
            sender='[EMAIL_ADDRESS]',
            recipients=['[EMAIL_ADDRESS]']
        )
        msg.body = "Hello" + name + ",\n\n"+message
        msg.subject = 'Intrusion Alert'
        mail.send(msg)
        return 'Email sent successfully'
    except Exception as e:
        return str(e)



