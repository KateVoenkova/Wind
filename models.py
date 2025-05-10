# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # Связь с загруженными книгами
    uploaded_books = db.relationship('Book', backref='uploaded_by', lazy=True)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    year = db.Column(db.Integer)
    is_deleted = db.Column(db.Boolean, default=False)

    # Связь с пользователем
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Поля автора книги
    author_last_name = db.Column(db.String(100), nullable=False)
    author_first_name = db.Column(db.String(100), nullable=False)
    author_middle_name = db.Column(db.String(100))

    # Связи с другими моделями
    characters = db.relationship('Character', backref='book', lazy=True)
    analyses = db.relationship('BookAnalysis', backref='book', lazy=True)

    @property
    def author_full_name(self):
        """Возвращает полное ФИО автора"""
        parts = [self.author_last_name, self.author_first_name]
        if self.author_middle_name:
            parts.append(self.author_middle_name)
        return ' '.join(parts)

class BookAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user = db.relationship('User', backref='analyses')

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

class CharacterRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character1_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    character2_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    weight = db.Column(db.Integer, default=1)


    __table_args__ = (
        db.UniqueConstraint('character1_id', 'character2_id', 'book_id', name='unique_relationship'),
    )