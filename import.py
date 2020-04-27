import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    b_file = open("books.csv")
    # исопльзование DictReader вместо reader позволяет использовать первую строку как ключ для словаря,
    # тогда при выводе первая строка трансформируется в название ключей
    books = csv.DictReader(b_file)
    db.execute("CREATE TABLE books (id SERIAL PRIMARY KEY, isbn text NOT NULL, title text NOT NULL, author text NOT NULL, year text NOT NULL)")
    for row in books:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": row['isbn'], "title": row['title'], "author": row['author'], "year":row['year']})
    db.commit()

if __name__ == "__main__":
    main()
