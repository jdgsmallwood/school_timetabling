from flask import render_template
from timetabler import bcrypt, db
from timetabler.helpers import *
from pandas import isnull
from datetime import time
import datetime
from timetabler.config import appcfg


class CRUDMixin(db.Model):
    """A simple CRUD interface for other classes to inherit. Provides the basic functionality.
    """
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod(), **kwargs).first()

    @classmethod
    def get_or_create(cls, **kwargs):
        '''
        Get, or create and return an object of the specified type with the specified keyword arguments.

        :param kwargs: Arguments for the object.
        :return:
        '''
        obj = cls.get(**kwargs)
        if obj is None:
            obj = cls(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return obj
        else:
            return obj

    def update(self, commit=True, **kwargs):
        '''

        :param commit: Commit to the database?
        :param kwargs: Keyword arguments to update
        :return: nil.
        '''
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        '''
        Save the current object.
        :param commit: Commit to the database?
        :return: Current object
        '''
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        '''
        Delete this object.
        :param commit: Commit to the database?
        :return: Nil.
        '''
        db.session.delete(self)
        return commit and db.session.commit()

    @classmethod
    def create(cls, commit=True, **kwargs):
        '''
        Create an object with the specified keywords.
        :param commit:
        :param kwargs:
        :return: Created object.
        '''
        instance = cls(**kwargs)
        return instance.save(commit=commit)

    @classmethod
    def get_all(cls, **kwargs):
        '''
        Get all instances of the specified class with the specified keyword arguments.
        :param kwargs: The keywords.
        :return: List of all instances matching the arguments.
        '''
        return cls.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod(), **kwargs).all()


class Base(CRUDMixin):
    '''
    Base class for the other models to inherit.

    I'm using this class to house the common database columns that come up again and again when defining these things.
    All of my classes can now extend Base and call its constructor.
    '''
    __abstract__ = True
    id = db.Column('id', db.Integer, primary_key=True)
    year = db.Column('year', db.Integer, nullable=False)
    studyperiod = db.Column('studyperiod', db.String(20), nullable=False)

    def __init__(self):
        '''
        Set the current year and studyperiod on the object.
        '''
        self.year = get_current_year()
        self.studyperiod = get_current_studyperiod()


class User(Base):
    '''
    This is the basic User class that is used by Flask-Login and Flask-Principal.

    By default it creates a non-admin user.
    '''
    __tablename__ = "users"
    username = db.Column('username', db.String(40), index=True, nullable=False)
    password = db.Column('password', db.String(100), nullable=False)
    email = db.Column('email', db.String(50))
    is_admin = db.Column('is_admin', db.String(10))

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.is_admin = False

    def make_admin(self):
        self.update(is_admin=True)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.username)

    def __repr__(self):
        return '<User %r>' % (self.username)

    def view_user_template(self):
        return render_template('user.html', user=self, tutors=Tutor.get_all())


####MODELS


class Admin(db.Model):
    '''
    This is the Admin table where we keep key value pairs for certain things like year, studyperiod, timetable etc.
    It specifically does not inherit from Base as I do not want a year/studyperiod tag on this table.
    '''
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(50), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    def update(self, commit=True, **kwargs):
        '''

        :param commit: Commit to the database?
        :param kwargs: Keyword arguments to update
        :return: nil.
        '''
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and db.session.commit()


'''
##Association tables
Association tables for the many-to-many relationships. These are the secondaries on db.relationship.
'''
substumap = db.Table('substumap',
                     db.Column('id', db.Integer, primary_key=True),
                     db.Column('student_id', db.Integer, db.ForeignKey('students.id')),
                     db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id')))

subtutmap = db.Table('subtutmap',
                     db.Column('id', db.Integer, primary_key=True),
                     db.Column('tutor_id', db.Integer, db.ForeignKey('tutors.id')),
                     db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id')))

stutimetable = db.Table('stutimetable',
                        db.Column('id', db.Integer, primary_key=True),
                        db.Column('timetabledclass_id', db.Integer, db.ForeignKey('timetabledclass.id')),
                        db.Column('student_id', db.Integer, db.ForeignKey('students.id')))

timeslotclassesmap = db.Table('timeslotclassesmap',
                              db.Column('id', db.Integer, primary_key=True),
                              db.Column('timeslot_id', db.Integer, db.ForeignKey('timeslots.id')),
                              db.Column('timetabledclass_id', db.Integer, db.ForeignKey('timetabledclass.id')))

tutoravailabilitymap = db.Table('tutoravailabilitymap',
                                db.Column('id', db.Integer, primary_key=True),
                                db.Column('tutor_id', db.Integer, db.ForeignKey('tutors.id')),
                                db.Column('timeslot_id', db.Integer, db.ForeignKey('timeslots.id')))


class University(db.Model):
    __tablename__ = 'university'
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String(50), nullable=False)

    def __init__(self, name):
        self.name = name


class College(db.Model):
    __tablename__ = 'colleges'
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String(50), nullable=False)

    def __init__(self, name):
        self.name = name


class Subject(Base):
    '''
    This is the subject class that contains each subject for each year/studyperiod
    '''
    __tablename__ = 'subjects'
    subcode = db.Column(db.String(50), nullable=False)
    subname = db.Column(db.String(50), nullable=False)
    repeats = db.Column(db.Integer, default=1)
    needsprojector = db.Column(db.Boolean, nullable=True)
    universityid = db.Column(db.Integer, db.ForeignKey('university.id'))
    university = db.relationship("University", backref=db.backref('subjects'))
    def __init__(self, subcode, subname, repeats=1):
        super().__init__()
        self.subcode = subcode
        self.subname = subname
        self.repeats = repeats

    def addTutor(self, tutor):
        self.tutor = tutor
        db.session.commit()

    def view_subject_template(self, form, msg=""):
        return render_template("subject.html", subject=self, students=self.students,
                               tutor=self.tutor, tutors=Tutor.get_all(),
                               msg=msg, times=self.find_possible_times(),
                               timeslots=Timeslot.get_all(), rooms=Room.get_all(),
                               timetabledclasses=self.timetabledclasses, form=form)

    def find_possible_times(self):
        '''
        Find times where all students are available for a class.

        This method is used by the Subject template to help timetable a class when there is already a timetable in place
        :return: List of times in which all students in a particular subject have no timetabled classes.
        '''
        students = self.students
        times = get_all_timeslots()
        for student in students:
            for classes in student.timetabledclasses:
                timeslot = classes.timeslot
                if timeslot in times:
                    times.remove(timeslot)
        return times


class Student(Base):
    __tablename__ = 'students'
    studentcode = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    subjects = db.relationship("Subject", secondary=substumap, backref=db.backref('students'))
    timetabledclasses = db.relationship("TimetabledClass", secondary=stutimetable,
                                        backref=db.backref('students'))
    universityid = db.Column(db.Integer, db.ForeignKey('university.id'))
    university = db.relationship("University", backref=db.backref('students'))
    collegeid = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    college = db.relationship("College", backref=db.backref('students'))
    email = db.Column(db.String(50))

    def __init__(self, studentcode, name, universityid, collegeid, email=""):
        super().__init__()
        self.studentcode = studentcode
        self.name = name
        self.email = email
        self.universityid = universityid
        self.collegeid = collegeid

    def view_student_template(self, form, msg=""):
        return get_student_template(self, form, msg)

    def addSubject(self, subject):
        if subject not in self.subjects:
            self.subjects.append(subject)
            db.session.commit()


class Timetable(Base):
    __tablename__ = 'timetable'
    id = db.Column(db.Integer, primary_key=True)
    studyperiod = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    key = db.Column(db.String(50), nullable=True)
    timeslots = db.relationship("Timeslot", single_parent=True, cascade='all,delete-orphan')

    def __init__(self, key=""):
        super().__init__()
        self.key = key


class Tutor(Base):
    __tablename__ = 'tutors'
    name = db.Column(db.String(50), nullable=False)
    subjects = db.relationship("Subject", secondary=subtutmap,
                               backref=db.backref('tutor', uselist=False, lazy='joined'))
    availabletimes = db.relationship("Timeslot", secondary=tutoravailabilitymap,
                                     backref=db.backref('availabiletutors'))
    email = db.Column(db.String(50), nullable=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", backref=db.backref('tutor', uselist=False))

    def __init__(self, name, email=""):
        super().__init__()
        self.name = name
        self.email = email
        self.generate_user_for_tutor()

    def get_teaching_times(self):
        teachingtimes = []
        for timeclass in self.timetabledclasses:
            teachingtimes.append(timeclass.timeslot)
        return teachingtimes

    def generate_user_for_tutor(self):
        if len(self.name.split(' ')) > 1:
            # What if someone doesn't have a family name? This has happened before.
            username = self.name.split(' ')[0][0] + self.name.split(' ')[1]
        else:
            username = self.name
        create_user_with_tutor(username=username, password=username, tutor=self)

    def view_tutor_template(self, form, msg="", msg2="", msg3=""):
        return get_tutor_template(self, form, msg, msg2, msg3)

    def addAvailableTime(self, timeslot):
        if timeslot not in self.availabletimes:
            self.availabletimes.append(timeslot)
            db.session.commit()

    def addSubject(self, **kwargs):
        subject = getSubject(**kwargs)
        if subject not in self.subjects:
            self.subjects.append(subject)
            db.session.commit()

    def num_hours(self):
        sum = 0
        for timeclass in self.subjects:
            sum += timeclass.repeats
        return sum

    def num_available_times(self):
        return len(self.availabletimes)


class TimetabledClass(Base):
    '''
    This class represents a class on the timetable - for example, Linear Algebra is timetabled to be at Wednesday 7:30pm.

    When the timetable solver has finished - it inputs timetabledclasses.

    '''
    __tablename__ = 'timetabledclass'
    subjectid = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    subject = db.relationship("Subject", backref=db.backref('timetabledclasses'), single_parent=True)
    timetable = db.Column(db.Integer, db.ForeignKey('timetable.id'))
    time = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    tutorid = db.Column(db.Integer, db.ForeignKey('tutors.id'))
    tutor = db.relationship("Tutor", backref=db.backref('timetabledclasses'), single_parent=True)
    roomid = db.Column(db.Integer, db.ForeignKey('rooms.id'))

    def __init__(self, subjectid, timetable, time, tutorid, roomid=None):
        super().__init__()
        self.subjectid = subjectid
        self.timetable = timetable
        self.time = time
        self.tutorid = tutorid
        if roomid is not None:
            self.roomid = roomid


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    projector = db.Column(db.Boolean)
    building = db.Column(db.String(50))
    timetabledclasses = db.relationship('TimetabledClass', backref=db.backref('room'))
    capacity = db.Column(db.Integer)

    @classmethod
    def get_all(cls):
        return cls.query.all()

    @classmethod
    def get_all_sorted(cls):
        list = cls.get_all()
        list.sort(key=lambda x: x.name)
        return list

    def get_available_times(self):
        timeslots = Timeslot.get_all()
        engagedtimes = []
        for timeclass in self.timetabledclasses:
            engagedtimes.append(timeclass.timeslot)
        return [timeslot for timeslot in timeslots if timeslot not in engagedtimes]

    def __init__(self, name, projector=False, capacity = 20):
        self.name = name
        self.projector = projector
        self.capacity = capacity


class Timeslot(Base):
    __tablename__ = 'timeslots'
    timetable = db.Column(db.Integer, db.ForeignKey('timetable.id'))
    day = db.Column(db.String(50), nullable=False)
    daynumeric = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    timetabledclasses = db.relationship("TimetabledClass", backref=db.backref('timeslot'), single_parent=True,
                                        cascade='all,delete-orphan')
    preferredtime = db.Column(db.Boolean)

    def __init__(self, day, time, preferredtime=True):
        super().__init__()
        self.timetable = get_current_timetable_id()
        self.day = day
        self.daynumeric = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
        self.time = time
        self.preferredtime = preferredtime


##### MODELS HELPER FUNCTIONS

def get_student_template(student, form, msg):
    return render_template('student.html', student=student, eligiblesubjects=Subject.get_all(),
                           subjects=student.subjects, msg=msg, form=form)


def getSubject(**kwargs):
    return Subject.get(**kwargs)


# HELPER METHODS
def unlinksubjecttutor(tutorid, subcode):
    subject = Subject.get(subcode=subcode)
    subject.tutor = None
    db.session.commit()
    return "Unlinked Successfully."


def unlinksubjectstudent(studentcode, subcode):
    student = Student.get(studentcode=studentcode)
    subject = Subject.get(subcode=subcode)
    student.subjects.remove(subject)
    db.session.commit()
    return "Unlinked Successfully"


def linksubjecttutor(tutorid, subcode):
    subject = Subject.get(subcode=subcode)
    subject.tutor = Tutor.get(id=tutorid)
    db.session.commit()
    msg = "Subject Linked to Tutor Successfully"
    return msg


def create_user_with_tutor(username, password, tutor):
    if User.query.filter_by(username=username, year=get_current_year(),
                            studyperiod=get_current_studyperiod()).first() is None:
        user = User(username=username, password=username)
        db.session.add(user)
        db.session.commit()
        user.tutor = tutor
        db.session.commit()


def getadmin():
    '''
    Get the current admin parameters.
    :return: Dictionary of admin parameters - currently current year and studyperiod.
    '''
    admin = {}
    admin["currentyear"] = get_current_year()
    admin["studyperiod"] = get_current_studyperiod()
    admin["timetable"] = get_current_timetable()
    return admin


def populate_students(df):
    '''
    Populate student and subject database from a dataframe.
    :param df: Pandas dataframe containing the student and subject data.
    :return: Nil.
    '''
    print("Populating Students")
    studyperiod = get_current_studyperiod()
    col_student_id = appcfg["enrolment_schema"]["student_id"]
    col_student_first_name = appcfg["enrolment_schema"]["student_first_name"]
    col_student_last_name = appcfg["enrolment_schema"]["student_last_name"]
    col_subject_code = appcfg["enrolment_schema"]["subject_code"]
    col_subject_name = appcfg["enrolment_schema"]["subject_name"]
    col_study_period = appcfg["enrolment_schema"]["study_period"]
    for index, row in df.iterrows():
        if studyperiod == row[col_study_period]:
            student_name = (str(row[col_student_first_name]) + " " + str(row[col_student_last_name])).strip().title()
            print("Adding: ", student_name, row[col_subject_code], row[col_subject_name])
            student = Student.get_or_create(studentcode=str(int(row[col_student_id])),
                                            name=student_name,
                                            universityid=University.query.filter_by(
                                                name='University of Melbourne').first().id,
                                            collegeid=str(College.query.filter_by(name="International House").first().id))
            subject = Subject.get_or_create(subcode=row[col_subject_code],
                                            subname=row[col_subject_name])
            student.addSubject(subject)


def populate_timetabledata(df):
    '''
    Populate timetable and classlists from dataframe
    :param df: Pandas dataframe containing timetable and classlist data.
    :return: Nil.
    '''
    timetable = Timetable.get_or_create(key="default")
    print("Timetable Created")
    for index, row in df.iterrows():
        tutor = Tutor.get_or_create(name=row['x3'])
        subject = Subject.get_or_create(subcode=row['x1'])
        time2 = row['x4'].split(' ')
        day = time2[0]
        time2 = time2[1]
        time2 = check_time(time2)
        timeslot = Timeslot.get_or_create(day=day, time=time2)
        timetable = get_current_timetable()
        timetabledclass = TimetabledClass.get_or_create(time=timeslot.id, subjectid=subject.id, timetable=timetable.id)
        for i in range(5, len(row)):
            if not isnull(row[i]):
                student = Student.get(name=row[i]).first()
                if timetabledclass not in student.timetabledclasses:
                    student.timetabledclasses.append(timetabledclass)
                    db.session.commit()


def populate_availabilities(df):
    '''
    Populate tutor availabilities from dataframe.
    :param df: Pandas dataframe containing tutor availabilities (1/0) against the current timeslots.
    :return: Nil.
    '''
    for index, row in df.iterrows():
        tutor = Tutor.get_or_create(name=row["Tutor"])
        tutor.availabletimes = []
        db.session.commit()
        for key in row.keys():
            keysplit = key.split(' ')
            if keysplit[0] in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                timeslot = Timeslot.get_or_create(day=keysplit[0],
                                                  time=keysplit[1])
                if row[key] == 1:
                    print("Assigning timeslot: ", key, row["Tutor"])
                    tutor.addAvailableTime(timeslot)


def get_tutor_template(tutor, form, msg="", msg2="", msg3=""):
    return render_template('tutor.html', tutor=tutor, eligiblesubjects=Subject.get_all(),
                           subjects=tutor.subjects, timeslots=Timeslot.get_all(),
                           availability=tutor.availabletimes,
                           msg=msg, msg2=msg2, msg3=msg3, form=form)


def populate_tutors(df):
    for index, row in df.iterrows():
        tutor = Tutor.get_or_create(name=row['Tutor'])
        subject = Subject.get(subcode=row["Subject Code"])
        subject.update(repeats=row["Repeats"])
        if subject not in tutor.subjects:
            print("Assigning tutor: ", row['Tutor'], row["Subject Code"], row["Repeats"])
            subject.addTutor(tutor)


def update_year(year):
    '''
    Update the current year in the admin table.
    :param year: The year to switch to.
    :return: Nil.
    '''
    admin = Admin.query.filter_by(key='currentyear').first()
    admin.value = year
    db.session.commit()


def update_studyperiod(studyperiod):
    '''
    Update the current studyperiod in the admin table.
    :param studyperiod: The studyperiod to switch to.
    :return: Nil.
    '''
    admin = Admin.query.filter_by(key='studyperiod').first()
    admin.value = studyperiod
    db.session.commit()

def get_current_year():
    '''
    Get the current year from the admin table.
    :return: The current year as an integer.
    '''
    admin = Admin.query.filter_by(key='currentyear').first()
    return int(admin.value)


def get_current_timetable():
    '''
    Get the current timetable from the database.
    :return: The current timetable as an object.
    '''
    admin = Admin.query.filter_by(key='timetable').first()
    return Timetable.get(id=int(admin.value))


def get_current_timetable_id():
    '''
    Get the current timetable id from the database.
    :return: The current timetable id as an integer.
    '''
    admin = Admin.query.filter_by(key='timetable').first()
    return Timetable.get(id=int(admin.value)).id


def get_current_studyperiod():
    '''
    Get the current studyperiod from the database
    :return: The current studyperiod as a String.
    '''
    admin = Admin.query.filter_by(key='studyperiod').first()
    return admin.value


def linksubjectstudent(studentcode, subcode):
    student = Student.get(studentcode=studentcode)
    subject = Subject.get(subcode=subcode)
    if subject not in student.subjects:
        student.subjects.append(subject)
        db.session.commit()
    return "Linked Successfully."


def check_time(time2):
    '''
    This method checks when you input a timetable that the time is in the right format.

    '''
    if time2.find('pm') != -1:
        time2 = time.strftime("%H:%M", time.strptime(time2, "%I:%M%p"))
    elif len(time2) < 5:
        time2 = time2 + "pm"
        time2 = time.strftime("%H:%M", time.strptime(time2, "%I:%M%p"))
    return time2


def change_room_projector(roomid, value):
    room = Room.query.filter_by(id=roomid).first()
    if value == 1:
        room.projector = True
        db.session.commit()
    elif value == 0:
        room.projector = False
        db.session.commit()


def get_timetabled_class(classid):
    return TimetabledClass.get(id=classid)


def get_all_subjects():
    return Subject.get_all()


def get_all_timeslots():
    return Timeslot.get_all()


def get_timetable_data(rooms=False):
    '''
    Get all required timetable data from the database
    :return: All timetabling data as a tuple to the preparetimetable method.
    '''
    SUBJECTS = []
    SUBJECTMAPPING = {}
    STUDENTS = []
    ROOMS = []
    REPEATS = {}
    TEACHERS = []
    TUTORAVAILABILITY = {}
    TEACHERMAPPING = {}
    PROJECTORS = []
    PROJECTORROOMS = []
    NONPREFERREDTIMES = []
    CAPACITIES = {}

    allsubjects = Subject.query.filter(Subject.year == get_current_year(),
                                       Subject.studyperiod == get_current_studyperiod(), Subject.tutor != None).all()
    alltutors = []
    for subject in allsubjects:
        SUBJECTMAPPING[subject.subcode] = []
        REPEATS[subject.subcode] = subject.repeats
        SUBJECTS.append(subject.subcode)
        TEACHERS.append(subject.tutor.name)
        if subject.tutor not in alltutors:
            alltutors.append(subject.tutor)
        for student in subject.students:
            STUDENTS.append(student.name)
            SUBJECTMAPPING[subject.subcode].append(student.name)
        SUBJECTMAPPING[subject.subcode] = set(SUBJECTMAPPING[subject.subcode])
        if subject.needsprojector is True:
            PROJECTORS.append(subject.subcode)
    STUDENTS = list(set(STUDENTS))
    TEACHERS = list(set(TEACHERS))
    for tutor in alltutors:
        TUTORAVAILABILITY[tutor.name] = []
        TEACHERMAPPING[tutor.name] = []
        for timeslot in tutor.availabletimes:
            TUTORAVAILABILITY[tutor.name].append(timeslot.day + " " + timeslot.time)
        for subject in tutor.subjects:
            TEACHERMAPPING[tutor.name].append(subject.subcode)
        TUTORAVAILABILITY[tutor.name] = set(TUTORAVAILABILITY[tutor.name])
        TEACHERMAPPING[tutor.name] = set(TEACHERMAPPING[tutor.name])

    allrooms = Room.query.all()
    for room in allrooms:
        ROOMS.append(room.name)
        if room.projector is True:
            PROJECTORROOMS.append(room.name)
        if room.capacity is not None:
            CAPACITIES[room.name] = int(room.capacity)
        else:
            CAPACITIES[room.name] = appcfg["default_room_capacity"]
    numroomsprojector = len(PROJECTORROOMS)
    maxclasssize = appcfg["max_class_size"]
    minclasssize = appcfg["min_class_size"]
    nrooms = len(ROOMS)
    TIMES = []
    day = []
    timeslots = Timeslot.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod(),
                                         timetable=get_current_timetable().id).all()
    for timeslot in timeslots:
        TIMES.append(timeslot.day + " " + timeslot.time)
        day.append(timeslot.day)
        if timeslot.preferredtime is False:
            NONPREFERREDTIMES.append(timeslot.day + " " + timeslot.time)

    day = list(set(day))
    DAYS = {}
    for d in day:
        DAYS[d] = []
    for timeslot in timeslots:
        DAYS[timeslot.day].append(timeslot.day + " " + timeslot.time)
    for d in day:
        DAYS[d] = set(DAYS[d])


    if rooms == True:
        return (STUDENTS, SUBJECTS, TIMES, day, DAYS, TEACHERS, SUBJECTMAPPING, REPEATS, TEACHERMAPPING,
                TUTORAVAILABILITY, maxclasssize, minclasssize, ROOMS, PROJECTORS, PROJECTORROOMS, numroomsprojector, NONPREFERREDTIMES, CAPACITIES)
    else:
        return (STUDENTS, SUBJECTS, TIMES, day, DAYS, TEACHERS, SUBJECTMAPPING, REPEATS, TEACHERMAPPING,
                TUTORAVAILABILITY, maxclasssize, minclasssize, nrooms)


def add_classes_to_timetable(TEACHERS, TEACHERMAPPING, SUBJECTMAPPING, TIMES, subject_vars, assign_vars, ROOMS):
    print(ROOMS)
    for m in TEACHERS:
        for j in TEACHERMAPPING[m]:
            subject = Subject.get(subcode=j)
            for k in TIMES:
                for n in ROOMS:
                    print(n)
                    timesplit = k.split(' ')
                    timeslot = Timeslot.get(timetable=get_current_timetable().id, day=timesplit[0], time=timesplit[1])
                    tutor = Tutor.get(name=m)
                    room = Room.query.filter_by(name=n).first()
                    print(room.id)
                    if subject_vars[(j, k, m, n)].varValue == 1:
                        timetabledclass = TimetabledClass.create(subjectid=subject.id,
                                                                 timetable=get_current_timetable().id, time=timeslot.id,
                                                                 tutorid=tutor.id, roomid=room.id)
                        for i in SUBJECTMAPPING[j]:
                            if assign_vars[(i, j, k, m, n)].varValue == 1:
                                student = Student.get(name=i)
                                timetabledclass.students.append(student)
                                db.session.commit()


def add_classes_to_timetable_twostep(TEACHERS, TEACHERMAPPING, SUBJECTMAPPING, TIMES, subject_vars_with_rooms,
                                     assign_vars, ROOMS, classpop):
    print("Adding classes to timetable.")
    for m in TEACHERS:
        for j in TEACHERMAPPING[m]:
            subject = Subject.get(subcode=j)
            for k in TIMES:
                for n in ROOMS:
                    if (j,k,m) in classpop.keys():
                        timesplit = k.split(' ')
                        timeslot = Timeslot.get(timetable=get_current_timetable().id, day=timesplit[0], time=timesplit[1])
                        tutor = Tutor.get(name=m)
                        room = Room.query.filter_by(name=n).first()
                        if subject_vars_with_rooms[(j, k, m, n)].varValue == 1:
                            timetabledclass = TimetabledClass.create(subjectid=subject.id,
                                                                     timetable=get_current_timetable().id, time=timeslot.id,
                                                                     tutorid=tutor.id, roomid=room.id)
                            for i in SUBJECTMAPPING[j]:
                                if assign_vars[(i, j, k, m)].varValue == 1:
                                    student = Student.get(name=i)
                                    timetabledclass.students.append(student)
                                    db.session.commit()


def get_all_rolls():
    path_to_file = app.config['UPLOAD_FOLDER'] + '/rolls' + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + '.docx'
    subjects = get_all_subjects()
    document = Document()
    for subject in subjects:
        for timetabledclass in subject.timetabledclasses:
            timeslot = timetabledclass.timeslot
            room = timetabledclass.room
            students = timetabledclass.students
            document.add_heading(subject.subname, 0)

            document.add_paragraph('Timeslot: ' + timeslot.day + " " + timeslot.time)
            if timetabledclass.room is not None:
                document.add_paragraph('Room: ' + room.name)

            table = document.add_table(rows=1, cols=12)
            table.style = 'TableGrid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Name'
            hdr_cells[1].text = '1'
            hdr_cells[2].text = '2'
            hdr_cells[3].text = '3'
            hdr_cells[4].text = '4'
            hdr_cells[5].text = '5'
            hdr_cells[6].text = '6'
            hdr_cells[7].text = '7'
            hdr_cells[8].text = '8'
            hdr_cells[9].text = '9'
            hdr_cells[10].text = '10'
            hdr_cells[11].text = '11'
            for item in students:
                row_cells = table.add_row().cells
                row_cells[0].text = str(item.name)
            document.add_page_break()
    document.save(path_to_file)
    return path_to_file


def get_roll(classid):
    timeclass = get_timetabled_class(classid)
    subject = timeclass.subject
    students = subject.students
    room = timeclass.room
    timeslot = timeclass.timeslot
    return create_roll(students, subject, timeslot, room)


def init_db_studyperiod():
    if Admin.query.filter_by(key='currentyear').first() is None:
        admin = Admin(key='currentyear', value=int(appcfg["startyear"]))
        db.session.add(admin)
        db.session.commit()
    if Admin.query.filter_by(key='studyperiod').first() is None:
        study = Admin(key='studyperiod', value=appcfg["startstudyperiod"])
        db.session.add(study)
        db.session.commit()


def init_db_timetable():
    if Admin.query.filter_by(key='timetable').first() is None:
        timetable = Timetable(key="default")
        db.session.add(timetable)
        db.session.commit()
        timetableadmin = Admin(key='timetable', value=timetable.id)
        db.session.add(timetableadmin)
        db.session.commit()


def init_db_users():
    if User.query.filter_by(username='admin').first() is None:
        user = User.create(username='admin', password=appcfg['adminpassword'])
        user.update(is_admin=True)


def init_db_uni():
    if University.query.filter_by(name='University of Melbourne').first() is None:
        uni = University(name='University of Melbourne')
        db.session.add(uni)
        db.session.commit()


def init_db_college():
    if College.query.filter_by(name="International House").first() is None:
        college = College(name='International House')
        db.session.add(college)
        db.session.commit()


def init_db_timeslots():
    timeslots = appcfg['timeslots']
    for timeslot in timeslots:
        if Timeslot.get(day = timeslot[0].split(' ')[0], time = timeslot[0].split(' ')[1]) is None:
            if timeslot[1] == False:
                Timeslot.create(day = timeslot[0].split(' ')[0], time = timeslot[0].split(' ')[1], preferredtime = False)
            else:
                Timeslot.create(day=timeslot[0].split(' ')[0], time=timeslot[0].split(' ')[1], preferredtime=True)


def init_db_rooms():
    rooms = appcfg['rooms']
    for room in rooms:
        if Room.query.filter_by(name = room[0]).first() is None:
            room2 = Room(name = room[0], projector = room[1], capacity = room[2])
            db.session.add(room2)
            db.session.commit()


def init_db():
   print("Importing study period and year")
   init_db_studyperiod()
   print("Creating Timetable")
   init_db_timetable()
   print("Creating admin user")
   init_db_users()
   print("Creating University")
   init_db_uni()
   print("Creating College")
   init_db_college()
   print("Creating Timeslots")
   init_db_timeslots()
   print("Creating Rooms")
   init_db_rooms()


def change_preferred_timeslot(id, preferred):
    timeslot = Timeslot.query.get(id)
    if preferred == 1:
        timeslot.preferredtime = True
    else:
        timeslot.preferredtime = False
    db.session.commit()
