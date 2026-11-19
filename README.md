Sales Intelligence Hub

Project Overview

Sales Intelligence Hub is a branch-based Sales Analytics and Financial Tracking System developed using Python, MySQL, and Streamlit.

The application helps businesses manage branch-wise sales, track customer payments, and monitor pending amounts.

Key Features

User login with role-based access

Super Admin and Branch Admin dashboards

Branch-wise sales management

Automatic pending payment calculation

Split payment tracking

Payment history

Date-wise sales reports

Sales performance analysis

Technologies Used

Python

MySQL

Streamlit

Pandas

Bcrypt

Database

Database name: sales_intelligence_hub

Main tables:

branches

customer_sales

payment_splits

users

Project Structure

app.py – Main Streamlit application

hash_password.py – Password hashing utility

requirements.txt – Python dependencies

sq.sql – Database tables and sample data

sql.sql – Database trigger

.gitignore – Excludes private and unnecessary files

How to Run

Install Python.

Install the required packages:

pip install -r requirements.txt

Create the MySQL database and tables.

Configure your private database credentials in .streamlit/secrets.toml.

Run the application:

streamlit run app.py

Author

Madhu