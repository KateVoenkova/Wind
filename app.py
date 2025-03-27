from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Book, Character, CharacterRelationship
from name_parser import get_names_from_file
from relationships import find_relationships
import os
import uuid
import chardet
import logging
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db.init_app(app)
Bootstrap(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('library'))
        return f(*args, **kwargs)

    return decorated


# ---------------------------
# Маршруты аутентификации
# ---------------------------

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Успешный вход!', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверные учетные данные', 'danger')
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, password_hash=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Аккаунт успешно создан!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('home'))


# ---------------------------
# Личный кабинет и профили
# ---------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@app.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    books = Book.query.filter_by(user_id=user.id).all()
    return render_template('user/profile.html', user=user, books=books)


# ---------------------------
# Работа с книгами
# ---------------------------

@app.route('/library')
def library():
    books = Book.query.all()
    return render_template('books/library.html', books=books)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if not (request.referrer and url_for('dashboard') in request.referrer):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            file = request.files['file']
            title = request.form['title']
            description = request.form.get('description', '')

            if not file or file.filename == '':
                flash('Файл не выбран', 'danger')
                return redirect(url_for('upload'))

            if not file.filename.endswith('.txt'):
                flash('Поддерживаются только TXT-файлы', 'danger')
                return redirect(url_for('upload'))

            # Сохранение файла
            filename = f"{uuid.uuid4()}.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Парсинг имен
            names = get_names_from_file(filepath)
            if not names:
                raise ValueError("Не найдено имен персонажей")

            # Создание книги
            new_book = Book(
                title=title,
                description=description,
                user_id=current_user.id
            )
            db.session.add(new_book)
            db.session.commit()

            # Добавление персонажей
            for name in names:
                character = Character(
                    name=name,
                    normalized_name=name.lower().strip(),
                    description=f"Персонаж книги {title}",
                    book_id=new_book.id
                )
                db.session.add(character)

            db.session.commit()

            # Добавляем этот вызов для анализа отношений между персонажами
            find_relationships(new_book.id, filepath)

            flash('Книга успешно загружена!', 'success')
            return redirect(url_for('book_page', book_id=new_book.id))

        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            flash(f'Ошибка: {str(e)}', 'danger')

    return render_template('books/upload.html')

@app.route('/books/<int:book_id>', methods=['GET', 'POST'])
def book_page(book_id):
    book = Book.query.get_or_404(book_id)
    edit_mode = request.args.get('edit', 'false').lower() == 'true'

    if request.method == 'POST':
        if book.user_id != current_user.id and not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('library'))

        book.title = request.form['title']
        book.description = request.form['description']
        db.session.commit()
        flash('Изменения сохранены', 'success')
        return redirect(url_for('book_page', book_id=book.id))

    characters = Character.query.filter_by(book_id=book_id).all()
    return render_template('books/detail.html',
                           book=book,
                           characters=characters,
                           edit_mode=edit_mode)


@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.user_id != current_user.id and not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('library'))

    if request.method == 'POST':
        book.title = request.form['title']
        book.description = request.form['description']
        db.session.commit()
        flash('Изменения сохранены', 'success')
        return redirect(url_for('book_page', book_id=book.id))

    return render_template('books/edit.html', book=book)


@app.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Книга удалена', 'success')
    return redirect(url_for('library'))


# ---------------------------
# Работа с персонажами
# ---------------------------

@app.route('/books/<int:book_id>/characters')
@login_required
def manage_characters(book_id):
    book = Book.query.get_or_404(book_id)
    characters = Character.query.filter_by(book_id=book_id).all()
    return render_template('characters/manage.html', book=book, characters=characters)


@app.route('/characters/<int:character_id>')
@login_required
def character_details(character_id):
    character = Character.query.get_or_404(character_id)
    return render_template('characters/detail.html', character=character)


@app.route('/characters/<int:character_id>/edit', methods=['POST'])
@login_required
def edit_character(character_id):
    character = Character.query.get_or_404(character_id)
    character.name = request.form['name']
    character.description = request.form['description']
    db.session.commit()
    flash('Изменения сохранены', 'success')
    return redirect(url_for('character_details', character_id=character.id))

@app.route('/characters/<int:character_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_character(character_id):
    character = Character.query.get_or_404(character_id)
    db.session.delete(character)
    db.session.commit()
    flash('Персонаж удален', 'success')
    return redirect(url_for('manage_characters', book_id=character.book_id))


# ---------------------------
# Визуализация графа
# ---------------------------

@app.route('/graph/<int:book_id>')
@login_required
def show_graph(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('books/graph.html', book=book)


@app.route('/api/books/<int:book_id>/graph')
@login_required
def get_graph_data(book_id):
    characters = Character.query.filter_by(book_id=book_id).all()
    relationships = CharacterRelationship.query.filter_by(book_id=book_id).all()

    nodes = [{
        "id": char.id,
        "name": char.name,
        "description": char.description
    } for char in characters]

    links = [{
        "source": rel.character1_id,
        "target": rel.character2_id,
        "value": rel.weight
    } for rel in relationships]

    return jsonify({"nodes": nodes, "links": links})


# ---------------------------
# Инициализация приложения
# ---------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Создание администратора
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)