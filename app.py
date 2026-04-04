import os
import json
import base64
import numpy as np
from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

app = Flask(__name__)
app.secret_key = 'secret123'

# ===== PATHS =====
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

USERS_FILE = 'users.json'
HISTORY_FILE = 'history.json'

# ===== LOAD MODEL =====
MODEL_PATH = 'models/mobilenet_model.h5'

if os.path.exists(MODEL_PATH):
    model = load_model(MODEL_PATH)
    print("✅ Model Loaded")
else:
    model = None
    print("❌ Model NOT Found")

classes = ["Hazardous", "Non-Recyclable", "Organic", "Recyclable"]

# ===== HELPERS =====
def load_json(file):
    if not os.path.exists(file):
        return [] if file == HISTORY_FILE else {}
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

def predict_image(path):
    if model is None:
        return "Model not loaded", 0

    img = image.load_img(path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    pred = model.predict(img_array)
    index = np.argmax(pred)
    confidence = round(float(np.max(pred)) * 100, 2)

    return classes[index], confidence


# ===== AUTH =====
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['user'] = username
            return redirect('/home')

        return "Invalid Credentials ❌"

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        username = request.form['username']
        password = request.form['password']

        if username in users:
            return "User already exists ⚠️"

        users[username] = generate_password_hash(password)
        save_json(USERS_FILE, users)
        return redirect('/')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ===== HOME =====
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    return render_template('home.html')


# ===== STATIC PAGES =====
@app.route('/awareness')
def awareness():
    return render_template('info.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/compost')
def compost():
    return render_template('compost.html')

@app.route('/recycle')
def recycle():
    return render_template('recycling.html')


# ===== AI PAGE =====
@app.route('/ai')
def ai():
    if 'user' not in session:
        return redirect('/')
    return render_template('ai_identifier.html')


# ===== IMAGE PREDICTION =====
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/')

    file = request.files.get('image')

    if not file or file.filename == '':
        return redirect('/ai')

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    result, confidence = predict_image(path)

    methods = get_methods(result)

    # Save history
    history = load_json(HISTORY_FILE)
    history.append({
        "user": session['user'],
        "type": "image",
        "result": result,
        "confidence": confidence,
        "image": path
    })
    save_json(HISTORY_FILE, history)

    return render_template(
        'ai_identifier.html',
        prediction=result,
        confidence=confidence,
        image_path='/' + path,
        methods=methods
    )


# ===== CAMERA =====
@app.route('/predict_camera', methods=['POST'])
def predict_camera():
    if 'user' not in session:
        return jsonify({"result": "Login required", "confidence": 0})

    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]

        path = os.path.join(UPLOAD_FOLDER, 'camera.png')

        with open(path, "wb") as f:
            f.write(base64.b64decode(image_data))

        result, confidence = predict_image(path)

        methods = get_methods(result)

        # Save history
        history = load_json(HISTORY_FILE)
        history.append({
            "user": session['user'],
            "type": "camera",
            "result": result,
            "confidence": confidence,
            "image": path
        })
        save_json(HISTORY_FILE, history)

        return jsonify({
            "result": result,
            "confidence": confidence,
            "methods": methods
        })

    except Exception as e:
        return jsonify({"result": "Error", "confidence": 0})


# ===== TEXT AI =====
@app.route('/text_predict', methods=['POST'])
def text_predict():
    if 'user' not in session:
        return redirect('/')

    text = request.form.get('text', '').lower().strip()

    # 🔥 SMART KEYWORD DATABASE
    categories = {
        "Organic": [
            "food", "vegetable", "fruit", "leaves", "peels",
            "kitchen", "banana", "rice", "bread", "waste"
        ],
        "Recyclable": [
            "plastic", "paper", "glass", "bottle", "can",
            "cardboard", "newspaper", "box", "container"
        ],
        "Hazardous": [
            "battery", "chemical", "paint", "medicine",
            "acid", "spray", "toxic"
        ],
        "E-Waste": [
            "mobile", "phone", "laptop", "charger",
            "tv", "computer", "electronics", "earphones"
        ]
    }

    # 🔥 SMART MATCHING (sentence-based)
    scores = {cat: 0 for cat in categories}

    for cat, keywords in categories.items():
        for word in keywords:
            if word in text:   # 👈 IMPORTANT CHANGE
                scores[cat] += 1

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        result = "Non-Recyclable"
    else:
        result = "Hazardous (E-Waste)" if best == "E-Waste" else best

    # 🔥 DISPOSAL METHODS
    disposal_methods = {
        "Organic": [
            "Compost at home 🌱",
            "Use in gardening",
            "Make natural fertilizer"
        ],
        "Recyclable": [
            "Put in recycling bin ♻️",
            "Reuse or donate items",
            "Send to recycling center"
        ],
        "Hazardous": [
            "Dispose at special facility ⚠️",
            "Do not mix with regular waste"
        ],
        "Hazardous (E-Waste)": [
            "Give to e-waste center ⚠️",
            "Return to electronics shop"
        ],
        "Non-Recyclable": [
            "Reduce usage",
            "Avoid plastic items",
            "Dispose in landfill"
        ]
    }

    methods = disposal_methods.get(result, [])

    # 💾 SAVE HISTORY
    history = load_json(HISTORY_FILE)
    history.append({
        "user": session['user'],
        "type": "text",
        "input": text,
        "result": result
    })
    save_json(HISTORY_FILE, history)

    return render_template(
        'ai_identifier.html',
        text_result=result,
        user_text=text,
        methods=methods
    )    


# ===== METHODS =====
def get_methods(result):
    return {
        "Organic": ["Compost at home 🌱", "Use for gardening"],
        "Recyclable": ["Send to recycling center ♻️", "Reuse items"],
        "Hazardous": ["Dispose at special facility ⚠️"],
        "Hazardous (E-Waste)": ["Give to e-waste center ⚠️"],
        "Non-Recyclable": ["Reduce usage", "Send to landfill"]
    }.get(result, [])


# ===== DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    all_history = load_json(HISTORY_FILE)
    user_history = [h for h in all_history if h.get('user') == session['user']]

    stats = {"Organic":0, "Recyclable":0, "Hazardous":0, "Non-Recyclable":0}
    leaderboard = {}

    for h in all_history:
        result = h.get('result')
        user = h.get('user', 'guest')

        if result in stats:
            stats[result] += 1

        leaderboard[user] = leaderboard.get(user, 0)

        if result == "Recyclable":
            leaderboard[user] += 10
        elif result == "Organic":
            leaderboard[user] += 5

    leaderboard = dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True))

    return render_template(
        'dashboard.html',
        stats=stats,
        history=user_history,
        leaderboard=leaderboard
    )


# ===== CLEAR HISTORY =====
@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'user' not in session:
        return jsonify({"message": "Not logged in ❌"})

    all_history = load_json(HISTORY_FILE)
    updated = [h for h in all_history if h.get('user') != session['user']]
    save_json(HISTORY_FILE, updated)

    return jsonify({"message": "✅ History cleared"})


# ===== RUN =====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)