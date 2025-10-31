from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import smtplib as s
import cv2
import numpy as np
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'monkeypox'


model = load_model('model.h5')


class_labels = ['Chickenpox', 'Measles', 'Monkeypox', 'Normal']


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'monkeydb'
}


def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn


cause_treatment = {
    'Chickenpox': {
        'cause': 'Caused by the varicella-zoster virus.',
        'treatment': 'Rest and antiviral medication as prescribed by a doctor.'
    },
    'Measles': {
        'cause': 'Caused by the measles virus, highly contagious.',
        'treatment': 'Bed rest, hydration, and symptomatic treatment.'
    },
    'Monkeypox': {
        'cause': 'Caused by the monkeypox virus, similar to smallpox but milder.',
        'treatment': 'Symptomatic treatment and isolation to prevent spread.'
    },
    'Normal': {
        'cause': 'No infection detected.',
        'treatment': 'No treatment needed.'
    }
}


def send_email(subject, body, recipients):
    try:
        ob = s.SMTP("smtp.gmail.com", 587)
        ob.starttls()
        sender_email = "projectsfind2022@gmail.com"
        app_password = "fxgzjgjryisptjun"  
        ob.login(sender_email, app_password)
        message = f"Subject: {subject}\n\n{body}"
        ob.sendmail(sender_email, recipients, message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        ob.quit()

# Home route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/graphs')
def graphs():
    return render_template('graphs.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Email already exists. Please log in instead.', 'warning')
            else:
                cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
                conn.commit()
                flash('Signup successful! Please login.', 'success')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Upload and prediction route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash('Please login first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image part', 'danger')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file:
            filename = file.filename
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)

            img = load_img(filepath, target_size=(224, 224))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0

            predictions = model.predict(img_array)
            predicted_class = np.argmax(predictions, axis=1)[0]
            probability = predictions[0][predicted_class] * 100  
            probability_formatted = f"{probability:.2f}"

            label = class_labels[predicted_class]

            cause = cause_treatment[label]['cause']
            treatment = cause_treatment[label]['treatment']

            if label == "Monkeypox":
                subject = "Health Alert: Monkeypox Detected"
                body = ("Monkeypox has been detected from the uploaded image. "
                        "Please consult a healthcare professional immediately for further guidance.")
                recipients = ["premalavc@gmail.com", "pranitabiradar82@gmail.com"]  
                send_email(subject, body, recipients)

            result = {
                'filename': filename,
                'label': label,
                'probability': probability_formatted,
                'cause': cause,
                'treatment': treatment
            }

            return render_template('result.html', result=result)

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
