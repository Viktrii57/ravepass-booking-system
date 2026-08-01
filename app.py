from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import create_app


import models  # Import models to register them with SQLAlchemy

app = create_app()


if __name__ == "__main__":
    app.run(port=5555, debug=True)

    
# # Initialize extensions
# db = SQLAlchemy(app)
# migrate = Migrate(app, db)

# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(128), nullable=False)

# @app.route('/')
# def index():
#     return 'Flask app is running.'
