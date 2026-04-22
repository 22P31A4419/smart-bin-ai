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

# 🔥 SMART PREDICTION FUNCTION
def predict_image(path):
    if model is None:
        return "Model not loaded", 0, 0, 0

    img = image.load_img(path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    pred = model.predict(img_array)[0]

    top_index = np.argmax(pred)
    top_conf = float(pred[top_index])
    second_conf = float(sorted(pred)[-2])

    confidence = round(top_conf * 100, 2)
    result = classes[top_index]

    return result, confidence, top_conf, second_conf

# ===== METHODS =====
def get_methods(result):
    return {
        "Organic Waste (Biodegradable)": [
            "Convert into compost 🌱",
            "Use for gardening"
        ],
        "Recyclable Waste": [
            "Send to recycling center ♻️",
            "Reuse items"
        ],
        "Hazardous Waste": [
            "Dispose safely ⚠️"
        ],
        "Non-Recyclable Waste": [
            "Reduce usage"
        ],
        "Mixed Waste": [
            "⚠ Contains multiple waste types",
            "Please separate items"
        ],
        "Hazardous (E-Waste)": [
            "Give to e-waste center ⚠️"
        ]
    }.get(result, [])

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

# ===== PAGES =====
@app.route('/ai')
def ai():
    if 'user' not in session:
        return redirect('/')
    return render_template('ai_identifier.html')

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

    result, confidence, top_conf, second_conf = predict_image(path)

    labels = {
        "Organic": "Organic Waste (Biodegradable)",
        "Recyclable": "Recyclable Waste",
        "Hazardous": "Hazardous Waste",
        "Non-Recyclable": "Non-Recyclable Waste"
    }

    # 🔥 SMART MIXED WASTE LOGIC
    if confidence < 60 and (top_conf - second_conf) < 0.2:
        result = "Mixed Waste"
    else:
        result = labels.get(result, result)

    methods = get_methods(result)

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

        result, confidence, top_conf, second_conf = predict_image(path)

        if confidence < 60 and (top_conf - second_conf) < 0.2:
            result = "Mixed Waste"

        methods = get_methods(result)

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

    except:
        return jsonify({"result": "Error", "confidence": 0})

# ===== TEXT AI =====
@app.route('/text_predict', methods=['POST'])
def text_predict():
    if 'user' not in session:
        return redirect('/')

    text = request.form.get('text', '').lower().strip()

    categories = {
        "Organic": ["food","fruit","vegetable","banana","rice","bread"],
        "Recyclable": ["plastic","paper","glass","bottle","can"],
        "Hazardous": ["battery","chemical","paint","medicine"],
        "E-Waste": ["mobile","laptop","charger","tv","computer"]
    }

    scores = {cat: 0 for cat in categories}

    for cat, words in categories.items():
        for w in words:
            if w in text:
                scores[cat] += 2

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        result = "Non-Recyclable Waste"
    else:
        result = "Hazardous (E-Waste)" if best == "E-Waste" else best + " Waste"

    methods = get_methods(result)

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

# ===== DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    all_history = load_json(HISTORY_FILE)
    user_history = [h for h in all_history if h.get('user') == session['user']]

    stats = {"Organic":0, "Recyclable":0, "Hazardous":0, "Non-Recyclable":0}

    for h in user_history:
        result = h.get('result', '')
        if "Organic" in result:
            stats["Organic"] += 1
        elif "Recyclable" in result:
            stats["Recyclable"] += 1
        elif "Hazardous" in result:
            stats["Hazardous"] += 1
        else:
            stats["Non-Recyclable"] += 1

    leaderboard = {}
    for h in all_history:
        user = h.get('user', 'guest')
        result = h.get('result', '')

        leaderboard[user] = leaderboard.get(user, 0)

        if "Recyclable" in result:
            leaderboard[user] += 10
        elif "Organic" in result:
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
