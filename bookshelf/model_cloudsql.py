# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


builtin_list = list


db = SQLAlchemy()


def init_app(app):
    # Disable track modifications, as it unnecessarily uses memory.
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    db.init_app(app)


def from_sql(row):
    """Translates a SQLAlchemy model instance into a dictionary"""
    data = row.__dict__.copy()
    data['id'] = row.id
    data.pop('_sa_instance_state')
    return data


# [START model]
class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    publishedDate = db.Column(db.String(255))
    imageUrl = db.Column(db.String(255))
    description = db.Column(db.String(4096))
    createdBy = db.Column(db.String(255))
    createdById = db.Column(db.String(255))
    comments = db.relationship('Comment', backref='books', lazy=True)

    def __repr__(self):
        return "<Book(title='%s', author=%s)" % (self.title, self.author)
# [END model]

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    username = db.Column(db.String(255))
    content = db.Column(db.String(4096))
    rate = db.Column(db.Integer)

    def __repr__(self):
        return "<Comment(username='%s', rate='%s', content='%s')" % (self.username, self.rate, self.content)

# [START list]
def list(limit=10, cursor=None):
    cursor = int(cursor) if cursor else 0
    query = (Book.query
             .order_by(Book.title)
             .limit(limit)
             .offset(cursor))
    books = builtin_list(map(from_sql, query.all()))
    next_page = cursor + limit if len(books) == limit else None
    return (books, next_page)
# [END list]


# [START read]
def read(id):
    result = Book.query.get(id)
    if not result:
        return None, None
    comments_query = Comment.query.filter_by(book_id=id).order_by(Comment.id.desc())
    if not comments_query:
        return from_sql(result), None
    return from_sql(result), builtin_list(map(from_sql, comments_query.all())), result
# [END read]


# [START create]
def create(data):
    book = Book(**data)
    db.session.add(book)
    db.session.commit()
    return from_sql(book)
# [END create]


# [START update]
def update(data, id):
    book = Book.query.get(id)
    for k, v in data.items():
        setattr(book, k, v)
    db.session.commit()
    return from_sql(book)
# [END update]


def delete(id):
    Comment.query.filter_by(book_id=id).delete()
    Book.query.filter_by(id=id).delete()
    db.session.commit()


def search(data, limit=10, cursor=None):
    year = data['year']
    title = data['title']
    
    query = None
    if year != '' and title != '':
        query = Book.query.filter((Book.title == title and Book.publishedDate.like(f'{year}%'))).limit(limit).offset(cursor)
    elif year != '' and title == '':
        query = Book.query.filter(Book.publishedDate.like(f'{year}%')).limit(limit).offset(cursor)
    elif year == '' and title != '':
        query = Book.query.filter(Book.title == title).limit(limit).offset(cursor)
    else:
        query = Book.query.limit(limit).offset(cursor)

    books = builtin_list(map(from_sql, query.all()))
    next_page = cursor + limit if len(books) == limit else None
    return books, next_page

def add_comment(book_raw, data):
    data['book_id'] = book_raw.id
    comment = Comment(**data)
    book_raw.comments.append(comment)
    db.session.add(comment)
    db.session.commit()

def ranking():
    subq = Book.query.with_entities(Comment.book_id, db.func.avg(Comment.rate).label('avgRate')).filter(Comment.book_id == Book.id).group_by(Comment.book_id).subquery()
    books = Book.query.with_entities(Book.id, Book.title, Book.author, Book.publishedDate, subq.c.avgRate).join(subq, Book.id == subq.c.book_id).order_by(subq.c.avgRate.desc()).all()
    rank = []
    cur_rank = 0
    cur_rate = 6
    for index, book in enumerate(books):
        if cur_rate > round(book.avgRate, 2):
            cur_rank = index + 1
            cur_rate = round(book.avgRate, 2)
        rank.append(cur_rank)
    return books, rank

def _create_database():
    """
    If this script is run directly, create all the tables necessary to run the
    application.
    """
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    init_app(app)
    with app.app_context():
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
