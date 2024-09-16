# main.py
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from flask_migrate import Migrate  # Импортируем Flask-Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelance.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Инициализация миграций
migrate = Migrate(app, db)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelance.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модель пользователя
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False)
    is_freelancer = db.Column(db.Boolean, default=False)

    # Отзывы, где пользователь является фрилансером
    reviews = db.relationship('Review', foreign_keys='Review.freelancer_id', backref='freelancer', lazy=True)

    # Сообщения
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

# Модель отзыва
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)

    # Внешний ключ на фрилансера
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Внешний ключ на проект
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    # Внешний ключ на пользователя, оставившего отзыв
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id])


# Модель проекта
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



# Модель сообщений для чата
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Главная страница
@app.route('/')
def home():
    projects = Project.query.all()
    return render_template('home.html', projects=projects)

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        is_freelancer = 'freelancer' in request.form
        user = User(username=username, email=email, password=password, is_freelancer=is_freelancer)
        db.session.add(user)
        db.session.commit()
        flash('Аккаунт создан!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Страница авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Логин или пароль неверный!', 'danger')
    return render_template('login.html')

# Личный кабинет
@app.route('/dashboard')
@login_required
def dashboard():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', projects=projects)

# Выход из аккаунта
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# Публикация проекта
@app.route('/post_project', methods=['GET', 'POST'])
@login_required
def post_project():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        budget = request.form['budget']
        project = Project(title=title, description=description, budget=budget, user_id=current_user.id)
        db.session.add(project)
        db.session.commit()
        flash('Проект опубликован!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_project.html')

# Оставить отзыв
@app.route('/leave_review/<int:freelancer_id>/<int:project_id>', methods=['GET', 'POST'])
@login_required
def leave_review(freelancer_id, project_id):
    if request.method == 'POST':
        content = request.form['content']
        rating = request.form['rating']
        review = Review(content=content, rating=rating, freelancer_id=freelancer_id, project_id=project_id, user_id=current_user.id)
        db.session.add(review)
        db.session.commit()
        flash('Ваш отзыв был оставлен!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('leave_review.html', freelancer_id=freelancer_id, project_id=project_id)

# Фильтр проектов
@app.route('/search_projects', methods=['GET'])
def search_projects():
    keyword = request.args.get('keyword', '')
    budget_min = request.args.get('budget_min')
    budget_max = request.args.get('budget_max')
    query = Project.query.filter(Project.title.contains(keyword) | Project.description.contains(keyword))
    
    if budget_min:
        query = query.filter(Project.budget >= int(budget_min))
    if budget_max:
        query = query.filter(Project.budget <= int(budget_max))
    
    projects = query.all()
    return render_template('search_results.html', projects=projects)

# Чат между заказчиком и фрилансером
@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    if request.method == 'POST':
        content = request.form['content']
        message = Message(sender_id=current_user.id, receiver_id=user_id, content=content)
        db.session.add(message)
        db.session.commit()
    
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) & (Message.receiver_id == user_id) | 
        (Message.sender_id == user_id) & (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', messages=messages, user_id=user_id)

# Добавим обработчики ошибок в main.py
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run()
