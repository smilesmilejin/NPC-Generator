from app import create_app, db


my_app = create_app()
with my_app.app_context():
    db.session.clear()
    print("Session cleared.")