from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
import os
from models import db, User
from image_routes import image_bp

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize DB and register blueprints
db.init_app(app)
app.register_blueprint(image_bp)

# Expose request and session in all templates
@app.context_processor
def inject_request():
    return dict(request=request, session=session)

# Redirect root to /az/
@app.route('/')
def home_redirect():
    return redirect('/az/')

# Dynamic page renderer
@app.route('/<lang>/<page>')
@app.route('/<lang>/', defaults={'page': 'index'})
def render_page(lang, page):
    if lang not in ['az', 'en']:
        abort(404)

    template_path = f"{lang}/{page}.html"
    if not os.path.exists(os.path.join('templates', template_path)):
        abort(404)

    return render_template(template_path, lang=lang, page=page)

# Flash message helper
def flash_message(key, lang):
    messages = {
        'missing_fields': {
            'en': "Email and password are required.",
            'az': "E-poçt və şifrə tələb olunur."
        },
        'user_exists': {
            'en': "User already exists.",
            'az': "İstifadəçi artıq mövcuddur."
        },
        'signup_success': {
            'en': "Account created successfully! Please log in.",
            'az': "Hesab uğurla yaradıldı! Zəhmət olmasa daxil olun."
        },
        'email_not_found': {
            'en': "No account with this email exists. Create a new one.",
            'az': "Bu e-poçt ünvanı ilə hesab tapılmadı. Yeni bir hesab yaradın."
        },
        'wrong_password': {
            'en': "Incorrect password. Please try again.",
            'az': "Şifrə yanlışdır. Zəhmət olmasa yenidən cəhd edin."
        },
        'login_success': {
            'en': "Logged in successfully!",
            'az': "Uğurla daxil oldunuz!"
        },
        'logged_out': {
            'en': "Logged out.",
            'az': "Sistemdən çıxıldı."
        }
    }

    category = 'success' if key in ['signup_success', 'login_success', 'logged_out'] else 'danger'
    flash(messages[key].get(lang, messages[key]['en']), category)

# Signup
@app.route('/<lang>/signup', methods=['GET', 'POST'])
def signup(lang):
    if lang not in ['az', 'en']:
        abort(404)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash_message('missing_fields', lang)
            return redirect(request.url)

        if User.query.filter_by(email=email).first():
            flash_message('user_exists', lang)
            return redirect(request.url)

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash_message('signup_success', lang)
        return redirect(url_for('login', lang=lang))

    return render_template(f"{lang}/signup.html", lang=lang, page='signup')

# Login
@app.route('/<lang>/login', methods=['GET', 'POST'])
def login(lang):
    if lang not in ['az', 'en']:
        abort(404)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash_message('missing_fields', lang)
            return redirect(request.url)

        user = User.query.filter_by(email=email).first()

        if not user:
            flash_message('email_not_found', lang)
            return redirect(request.url)

        if not user.check_password(password):
            flash_message('wrong_password', lang)
            return redirect(request.url)

        session['user_id'] = user.id
        flash_message('login_success', lang)
        return redirect(url_for('image.upload_image', lang=lang))

    return render_template(f"{lang}/login.html", lang=lang, page='login')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash_message('logged_out', session.get('lang', 'en'))
    return redirect('/')

# Run the app
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
