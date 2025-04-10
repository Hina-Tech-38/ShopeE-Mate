# app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pymysql
from werkzeug.utils import secure_filename
import os
import mysql.connector
import random
from datetime import datetime, timedelta

# DB setup
pymysql.install_as_MySQLdb()
app = Flask(__name__)
app.secret_key = "1000786hss"
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root@localhost/e-commerce"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Models
class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    profilepicture = db.Column(db.String(255), nullable=True, default='/static/profile.png')
    preferences = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    socials = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Signup {self.username}>"

class Signin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Load data
training_data = pd.read_csv('C:/Users/LENOVO/PycharmProjects/ShopeE-Mate/models/cleaned_dataset_final.csv')

# ================= Routes =======================
@app.route("/")
def index():
    return render_template('index.html')



@app.route("/index2")
def indexredirect2():
    df = pd.read_csv("C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/models/all_trends.csv")
    trending_data = df.to_dict(orient="records")
    return render_template("index2.html", trending=trending_data)

@app.route("/signup", methods=['POST'])
def signup():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        preferences = request.form.get('preferences', '')
        bio = request.form.get('bio', '')
        socials = request.form.get('socials', '')

        profile_picture = request.files.get('profilepicture')
        filepath = None
        if profile_picture and profile_picture.filename:
            filename = secure_filename(profile_picture.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            profile_picture.save(filepath)

        existing_user = Signup.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for("index"))

        new_user = Signup(
            username=username,
            email=email,
            password=password,
            preferences=preferences,
            bio=bio,
            socials=socials,
            profilepicture=filepath
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User signed up successfully!", "success")
        return redirect(url_for("index"))

    except Exception as e:
        db.session.rollback()
        print("Error during signup:", str(e))
        flash("An error occurred while signing up!", "danger")
        return redirect(url_for("index"))

@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        username = request.form.get('signinUsername')
        password = request.form.get('signinPassword')
        user = Signup.query.filter_by(username=username).first()

        if user:
            session['username'] = user.username
            session['email'] = user.email
            session['id'] = user.id
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop("username", None)
    flash("Logout successful!", "success")
    return redirect(url_for("index"))

@app.route('/profile')
def profile():
    if 'username' not in session:
        flash("You must signin first!", "warning")
        return redirect(url_for('signin'))

    user = Signup.query.filter_by(id=session['id']).first()
    if not user:
        flash("User profile not found!", "danger")
        return redirect(url_for('signin'))

    return render_template('profile.html', user=user)

# ========== Content-Based Recommendation ==========
def content_based_recommendation_system(training_data, item_name, top_n=10):
    if item_name not in training_data['name'].values:
        return pd.DataFrame()

    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(training_data['Tags'])
    cosine_similarities = cosine_similarity(tfidf_matrix, tfidf_matrix)
    item_index = training_data[training_data['name'] == item_name].index[0]
    similar_items = list(enumerate(cosine_similarities[item_index]))
    similar_items = sorted(similar_items, key=lambda x: x[1], reverse=True)
    top_indices = [x[0] for x in similar_items[1:top_n+1]]
    return training_data.iloc[top_indices][['name', 'ratings', 'image', 'url', 'reviews count', 'platform']]

@app.route("/recommendations", methods=['POST', 'GET'])
def content_recommendations():
    if request.method == 'POST':
        prod = request.form.get('prod')
        nbr = int(request.form.get('nbr'))
        recs = content_based_recommendation_system(training_data, prod, top_n=nbr)

        if recs.empty:
            return render_template('main.html', message="No recommendations available for this product.")
        return render_template("recommendations.html", products=recs.to_dict(orient='records'))



# ========== Users Also Liked ==========

@app.route('/insert_random_clicks')
def insert_random_clicks():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="e-commerce"
    )
    cursor = conn.cursor()

    user_ids = list(range(45, 56))
    product_ids = list(range(1, 10))

    for _ in range(50):
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)
        clicked_at = datetime.now() - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))

        cursor.execute("""
            INSERT INTO product_clicks (user_id, product_id, clicked_at)
            VALUES (%s, %s, %s)
        """, (user_id, product_id, clicked_at))

    conn.commit()
    cursor.close()
    conn.close()

    return "Random product clicks inserted!"

# ========== Click Tracker ==========
@app.route('/track_click', methods=['POST'])
def track_click():
    data = request.get_json()
    product_id = data.get('product_id')
    user_id = data.get('user_id')

    if not user_id or not product_id:
        return jsonify({'error': 'Missing data'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO product_clicks (user_id, product_id, clicked_at) VALUES (%s, %s, NOW())",
        (user_id, product_id)
    )
    mysql.connection.commit()
    cursor.close()

    return jsonify({"status": "success"}), 200
# load files===========================================================================================================
sample_products = pd.read_csv("C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/models/sample_products (1) .csv")

#randomly displaying when no clicked data is avialable
# List of predefined image URLs
# Define a mapping from product names to image filenames
image_mapping = {
    "Product 1": "C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/static/sample1.jpeg",
    "Product 2": "C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/static/sample2.jpg",
    "Product 3": "C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/static/sample3.jpg",
    "Product 4": "C:/Users/LENOVO/PycharmProjects/ShopeE-mate(demo)/static/sample4.jpg",
    # Add more mappings as needed
}


@app.route("/main")
def mainhome():
    # Create a list of image URLs based on product names
    random_product_image_urls = [
        url_for('static', filename=image_mapping.get(product['Name'], 'default.jpg'))
        for product in sample_products.to_dict(orient='records')
    ]

    # Print the generated URLs for debugging
    print("Generated Image URLs:", image_mapping)

    random_price = random.choice([40, 50, 60, 70])

    return render_template(
        'main.html',
        sample_products=sample_products,
        random_product_image_urls=image_mapping,
        random_price=random_price
    )



@app.template_filter('truncate')
def truncate(s, length=50):
    if not s:
        return ''
    return s[:length] + '...' if len(s) > length else s


@app.route("/search", methods=["GET"])
def search():
    product_query = request.args.get("prod", "").lower()
    num_results = int(request.args.get("nbr", 5))
    filtered_df = training_data[training_data["name"].str.lower().str.contains(product_query, na=False)].head(num_results)
    recommendations = filtered_df.to_dict(orient="records")
    return jsonify({"recommendations": recommendations})

@app.route('/cart')
def cart():
    return render_template('cart.html')

if __name__ == '__main__':
    app.run(debug=True)
