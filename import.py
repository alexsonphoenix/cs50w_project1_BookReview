#Import: Provided for you in this project is a file called books.csv, which is a spreadsheet in CSV format of 5000 different books. Each one has an ISBN number, a title, an author, and a publication year. In a Python file called import.py separate from your web application, write a program that will take the books and import them into your PostgreSQL database. You will first need to decide what table(s) to create, what columns those tables should have, and how they should relate to one another. Run this program by running python3 import.py to import the books into your database, and submit this program with the rest of your project code.

import csv
from app import db

f = open("books.csv")
reader = csv.reader(f)
next(f)
count=0
for i, t, a, y in reader: # loop gives each column a name
    toInt = int(y)
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
              {"isbn": i, "title": t, "author": a, "year": toInt}) # substitute values from CSV line into SQL command, as per this dict
db.commit() # transactions are assumed, so close the transaction finished
