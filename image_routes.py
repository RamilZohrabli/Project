import os
import uuid
import numpy as np
from PIL import Image as PILImage
from flask import Blueprint, request, render_template, redirect, url_for, session, abort, flash
from werkzeug.utils import secure_filename
from models import db, Image, User
import tensorflow as tf

image_bp = Blueprint('image', __name__)
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Load the trained model (.h5)
MODEL_PATH = os.path.join('model', 'agrovision.h5')
model = tf.keras.models.load_model(MODEL_PATH)

# Optional: class labels if your model uses them
CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy', 'Grape___Black_rot',
    'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy',
    'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy',
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy', 'Potato___Early_blight', 'Potato___Late_blight',
    'Potato___healthy', 'Raspberry___healthy', 'Soybean___healthy', 'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch', 'Strawberry___healthy', 'Tomato___Bacterial_spot', 'Tomato___Early_blight',
    'Tomato___Late_blight', 'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot',
    'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 'Tomato___healthy', 'Unknown'
]
  # Update based on your model output

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@image_bp.route('/<lang>/upload', methods=['GET', 'POST'])
def upload_image(lang):
    if lang not in ['az', 'en']:
        abort(404)

    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to upload.")
        return redirect(url_for('login', lang=lang))

    messages = {
        'az': {
            'no_image': 'Şəkil seçilməyib.',
            'no_file': 'Fayl seçilməyib.',
            'wrong_format': 'Yalnız png, jpg, jpeg və gif formatları qəbul olunur.',
            'success': 'Şəkil uğurla yükləndi.'
        },
        'en': {
            'no_image': 'No image selected.',
            'no_file': 'No file selected.',
            'wrong_format': 'Only png, jpg, jpeg and gif files are allowed.',
            'success': 'Image successfully uploaded.'
        }
    }

    msg = messages[lang]

    if request.method == 'POST':
        if 'image' not in request.files:
            flash(msg['no_image'])
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            flash(msg['no_file'])
            return redirect(request.url)

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{original_filename}"
            upload_path = os.path.join(UPLOAD_FOLDER, unique_name)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(upload_path)

            # Save record in DB
            new_image = Image(filename=unique_name, user_id=user_id)
            db.session.add(new_image)
            db.session.commit()

            # ✅ Predict using the model
            try:
                img = PILImage.open(upload_path).convert('RGB')
                img = img.resize((224, 224))  # Modelin gözlədiyi ölçü
                img_array = np.array(img) / 255.0
                img_array = np.expand_dims(img_array, axis=0)

                prediction = model.predict(img_array)
                print("Prediction output:", prediction)
                print("Prediction shape:", prediction.shape)

                # Əgər prediction cavabı boşdursa
                confidence = np.max(prediction[0])
                predicted_index = np.argmax(prediction[0])
                predicted_label = CLASS_NAMES[predicted_index]
                confidence = np.max(prediction[0])
                predicted_index = np.argmax(prediction[0])
                predicted_label = CLASS_NAMES[predicted_index]

                if confidence < 0.6:
                    predicted_label = "Image not recognized / Low confidence"


            except Exception as e:
                flash(f"Error during prediction: {str(e)}", "danger")
                return redirect(request.url)

            flash(msg['success'])
            return render_template(f"{lang}/upload.html", filename=unique_name, lang=lang, prediction=predicted_label)

        flash(msg['wrong_format'])
        return redirect(request.url)

    return render_template(f"{lang}/upload.html", filename=None, lang=lang)

@image_bp.route('/<lang>/my_images')
def my_images(lang):
    if lang not in ['az', 'en']:
        abort(404)

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to see your images.")
        return redirect(url_for('login', lang=lang))

    user = User.query.get(user_id)
    return render_template(f"{lang}/my_images.html", images=user.images, lang=lang)

@image_bp.route('/<lang>/delete/<filename>', methods=['POST'])
def delete_image(lang, filename):
    if lang not in ['az', 'en']:
        abort(404)

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in.")
        return redirect(url_for('login', lang=lang))

    image = Image.query.filter_by(filename=filename, user_id=user_id).first()
    if not image:
        abort(403)

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(image)
    db.session.commit()

    flash("Image deleted successfully.")
    return redirect(url_for('image.my_images', lang=lang))

@image_bp.route('/display/<filename>')
def display_image(filename):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in.")
        return redirect(url_for('login', lang='en'))

    image = Image.query.filter_by(filename=filename, user_id=user_id).first()
    if not image:
        abort(403)

    return redirect(url_for('static', filename='uploads/' + filename), code=301)
