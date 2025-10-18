from app import app, db

print("Attempting to create database tables...")

# This pushes an application context to make the app and db objects available.
with app.app_context():
    db.create_all()

print("Database tables should be created now.")