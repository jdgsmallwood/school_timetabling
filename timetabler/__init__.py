import logging
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from timetabler.config import appcfg
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_principal import Principal, RoleNeed, ActionNeed, Permission, identity_loaded
from flask_sqlalchemy import *

executor = ThreadPoolExecutor(2)
app = Flask(__name__)

app.config['LOGGING_FILE'] = appcfg['log']
app.config['UPLOAD_FOLDER'] = appcfg['upload']
app.config['ALLOWED_EXTENSIONS'] = set(['xls', 'xlsx', 'csv'])
app.config['SQLALCHEMY_DATABASE_URI'] = appcfg['dbstring']
app.config.update(
    SECRET_KEY=appcfg['secretkey']
)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
principals = Principal(app, skip_static=True)
login_manager = LoginManager()
login_manager.init_app(app)

'''
FLASK-LOGIN SET UP AREA

'''
login_manager.login_view = '/login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(username=user_id).first()



'''
FLASK_PRINCIPAL SET-UP AREA.

Firstly we set up Needs - Admin and User level preferences.
'''
# Needs
be_admin = RoleNeed('admin')
to_sign_in = ActionNeed('sign in')

# Permissions
user_permission = Permission(to_sign_in)
user_permission.description = 'User\'s permissions'
admin_permission = Permission(be_admin)
admin_permission.description = 'Admin\'s permissions'

apps_needs = [be_admin, to_sign_in]
apps_permissions = [user_permission, admin_permission]


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user
    if current_user.is_authenticated:
        needs = []
        needs.append(to_sign_in)
        if current_user.is_admin == 1 or current_user.is_admin == '1':
            needs.append(be_admin)
        for n in needs:
            identity.provides.add(n)


def current_privileges():
    return (('{method} : {value}').format(method=n.method, value=n.value)
            for n in apps_needs if n in g.identity.provides)


from timetabler.models import *
import timetabler.views

from timetabler.helpers import *
from timetabler.forms import LoginForm, AddSubjectForm, NameForm, TimeslotForm, StudentForm

# DATABASE METHODS
try:
    print("Initialising database...")
    # ***********************************
    # COMMENT THIS LINE OUT WHEN YOU ARE
    # RUNNING FIRST-TIME DB COMMANDS
    # ***********************************
    # db.create_all()  # <=====|| Comment In ||
    init_db()  # <=====|| Comment Out ||
    # ***********************************
    # END COMMENT OUT
    # ***********************************
    print("SUCCESS!")
except:
    print("FAILED... Rolling Back")
    print()
    print("If you are running first-time setup, comment out line 87 from timetabler/__init__.py")
    print("Then, un-comment it when running runserver")
    print()
    db.session.rollback()

# Set up logging
handler = RotatingFileHandler(
    app.config['LOGGING_FILE'], maxBytes=10000, backupCount=10)

handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
if __name__ == '__main__':
    app.run(debug=True)
