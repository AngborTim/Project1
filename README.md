# Project 1
This project allows users search for books using ISBN, title or author. The search is case sensitive. It means result of 'Dee' and 'dee' will be different. Result is presented as a table. By clicking on a row user will redirect to books details page.
This page has three blocks:
Book info
User's reviews if any (except current user)
Current user review. Here user can vote by clicking on stars and can write a review. He can chose to do both action or only one of them.
My review page shows reviews of current user. Every row is clickable, by clicking you will redirect to chosen book page.

For using this program you have to register.
Registration requires username, password and password confirmation. If username was already chosen by other user, or password and its confirmation are not equal, system will show alarm message.
After registration user can search, write revies etc.
Once register, user can login using his username and password.
User can logout for finishing his work.

.
application.py - main program
books.csv - books list
import.py - program for books list import 
README.md - this file
requirements.txt jsonify is added

./static:
favicon.png
logo.png
styles.css

./templates:
book.html - page for a book details
index.html - index file
layout.html - main layout
login.html - login page
my_reviews.html - page for all reviews of current user 
rating.html - insertion into book.html for rating
register.html - register page
review.html - insertion into book.html for review

