import json
import os
from flask import request, redirect, current_app, url_for, send_file, render_template
from flask_login import login_user, logout_user, current_user, login_required
from flask_principal import identity_changed, Identity
from sqlalchemy.orm import joinedload
import pandas
from timetabler import admin_permission
from timetabler.forms import LoginForm, AddSubjectForm, NameForm, TimeslotForm, StudentForm, EditTutorForm, \
    EditStudentForm, AddTimetableForm, JustNameForm
from timetabler.helpers import *
from timetabler.models import *


### APP ROUTES
@app.route('/')
@login_required
def hello_world():
    return render_template('index.html')


# FLASK LOGIN / LOGOUT / REGISTER
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template("login.html", form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            success = process_login(form.user_id.data, form.password.data, form)
            if success:
                return redirect('/')
            else:
                return render_template('login.html', form=form, msg="Username or Password was incorrect")
        else:
            return render_template('login.html', form=form, msg="Please enter username and password.")


def process_login(user_id, password, form):
    if User.query.filter_by(username=user_id).first() is not None:
        user = User.query.filter_by(username=user_id).first()
        if bcrypt.check_password_hash(user.password, password):
            login_user(user)
            identity_changed.send(current_app._get_current_object(), identity=Identity(user.username))
            return True
        else:
            return False



@app.route('/register', methods=['GET', 'POST'])
@admin_permission.require()
def register():
    form = LoginForm()
    if request.method == 'GET':
        return render_template("register.html", form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            template = add_user(form.user_id.data, form.password.data)
            return template
        else:
            return render_template("register.html", form=form)


def add_user(user_id, password):
    if User.query.filter_by(username=user_id).first() is None:
        user = User(username=user_id, password=password)
        db.session.add(user)
        db.session.commit()
    return redirect('/users')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


#UPLOAD ROUTES

@app.route('/uploadstudentdata', methods=['GET', 'POST'])
@admin_permission.require()
def uploadstudentdata():
    if request.method == 'POST':
        try:
            df = upload_and_return_df(request.files['file'])
            populate_students(df)
            return redirect("/students")
        except PermissionError as e:
            app.logger.error(e)
            return redirect('/uploadstudentdata')

    # msg = "Completed Successfully"
    # except:
    #    msg = "There was an error with the upload, please try again"
        # Redirect the user to the uploaded_file route, which
        # will basicaly show on the browser the uploaded file

    else:
        return render_template('/uploadstudentdata.html')


def upload_and_return_df(file):
    path_to_file = upload(file)
    if os.path.splitext(path_to_file)[1] == ".csv":
        return read_csv(path_to_file)
    else:
        return read_excel(path_to_file)


@app.route('/uploadtimetableclasslists', methods=['GET', 'POST'])
@admin_permission.require()
def uploadtimetableclasslists():
    if request.method == 'POST':
        df = upload_and_return_df(request.files['file'])
        populate_timetabledata(df)
        msg = "Completed Successfully"
    return render_template("uploadtimetabledata.html")





@app.route('/currentuser')
@login_required
def currentuser():
    return render_template("user.html", user=current_user)





@app.route('/updateadminsettings', methods=['POST'])
@admin_permission.require()
def updateadminsettings():
    studyperiod = request.form['studyperiod']
    year = request.form['year']
    if year != None:
        admin = Admin.get(key='currentyear')
        admin.update(value=year)
    admin = Admin.get(key='studyperiod')
    admin.update(value=studyperiod)
    for user in User.get_all(is_admin=True):
        user.update(year=year, studyperiod=studyperiod)
    timetable = Timetable.get_or_create(key='default')
    admin = Admin.get(key='timetable')
    admin.update(value=timetable.id)
    timetabler.models.init_db()
    return redirect('/admin')


@app.route('/updatetimetable', methods=['POST'])
@admin_permission.require()
def updatetimetable():
    if request.form['timetable'] is not None:
        admin = Admin.get(key='timetable')
        admin.update(value=request.form['timetable'])
    return redirect('/admin')


@app.route('/uploadtutordata', methods=['GET', 'POST'])
@admin_permission.require()
def uploadtutordata():
    if request.method == 'GET':
        return render_template('uploadtutordata.html')
    elif request.method == 'POST':
        df = upload_and_return_df(request.files['file'])
        populate_tutors(df)
        # os.remove(filename2)
        msg = "Completed successfully"
        return render_template('uploadtutordata.html', msg=msg)

@app.route('/uploadtutoravailabilities', methods=['POST'])
@admin_permission.require()
def upload_tutor_availabilities():
    df = upload_and_return_df(request.files['file'])
    populate_availabilities(df)
    msg2 = "Completed Successfully"
    return render_template("uploadtutordata.html",msg2=msg2)

@app.route('/runtimetabler')
@admin_permission.require()
def run_timetabler():
    return render_template("runtimetabler.html", tutors=Tutor.get_all(), timeslots=Timeslot.get_all())


@app.route('/addsubjecttotutor?tutorid=<tutorid>', methods=['GET', 'POST'])
@admin_permission.require()
def add_subject_to_tutor(tutorid):
    if request.method == 'POST':
        subcode = request.form['subject']
        msg = linksubjecttutor(tutorid, subcode)
        return redirect(url_for('view_tutor', tutorid=tutorid))



@app.route('/addtimetabledclasstosubject?subcode=<subcode>', methods=['POST'])
@admin_permission.require()
def add_timetabledclass_to_subject(subcode):
    subject = Subject.get(subcode=subcode)
    timeslot = Timeslot.query.get(request.form['timeslot'])
    timetable = get_current_timetable().id
    timetabledclass = TimetabledClass.get_or_create(subjectid=subject.id, timetable=timetable, time=timeslot.id,
                                                    tutorid=subject.tutor.id)
    if len(subject.timetabledclasses) == 1:
        timetabledclass.students = subject.students
        db.session.commit()
    return redirect(request.referrer)


@app.route('/admin')
@admin_permission.require()
def admin():
    return render_template('admin.html', admin=getadmin(), timetables=Timetable.get_all())


@app.route('/addtutortosubject?subcode=<subcode>', methods=['GET', 'POST'])
@admin_permission.require()
def add_tutor_to_subject(subcode):
    if request.method == 'POST':
        linksubjecttutor(request.form['tutor'], subcode)
        return redirect(request.referrer)


@app.route('/myclasses')
@login_required
def get_my_classes():
    return render_template('myclasses.html',tutor=current_user.tutor)

@app.route('/myprofile')
@login_required
def view_my_profile():
    tutor = Tutor.query.get(current_user.tutor.id)
    form = EditTutorForm(obj=tutor)
    return current_user.tutor.view_tutor_template(form=form)




@app.route('/addsubjecttostudent?studentcode=<studentcode>', methods=['POST'])
@admin_permission.require()
def add_subject_to_student(studentcode):
    subcode = request.form['subject']
    msg = linksubjectstudent(studentcode, subcode)
    return redirect(request.referrer)


#DELETION ROUTES

@app.route('/deleteallclasses')
@admin_permission.require()
def delete_all_timetabled_classes_view():
    delete_all_timetabled_classes()
    return redirect('/timetable')


@app.route('/deleteallstudentsajax', methods=['POST'])
@admin_permission.require()
def delete_all_students_view():
    delete_all_students()
    return "Done"


def delete_all_students():
    students = Student.get_all()
    for student in students:
        student.delete()
    db.session.commit()


@app.route('/deleteallsubjectsajax', methods=['POST'])
@admin_permission.require()
def delete_all_subjects_view():
    delete_all_subjects()
    return "Done"


def delete_all_subjects():
    subjects = Subject.get_all()
    for subject in subjects:
        subject.delete()


@app.route('/deletealltutorsajax', methods=['POST'])
@admin_permission.require()
def delete_all_tutors_view():
    delete_all_tutors()
    return "Done"


def delete_all_tutors():
    tutors = Tutor.get_all()
    for tutor in tutors:
        tutor.delete()


def delete_all_timetabled_classes():
    timetabledclasses = TimetabledClass.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod(),
                                                        timetable=get_current_timetable().id).all()
    for timeclass in timetabledclasses:
        db.session.delete(timeclass)
        db.session.commit()


@app.route('/deleteuser?username=<username>')
@admin_permission.require()
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    db.session.delete(user)
    db.session.commit()
    return redirect('/users')


@app.route('/deletestudent?studentid=<studentid>')
@admin_permission.require()
def delete_student(studentid):
    student = Student.get(id=studentid)
    student.delete()
    return redirect('/students')

@app.route('/removesubject?subcode=<subcode>')
@admin_permission.require()
def remove_subject(subcode):
    sub = Subject.get(subcode=subcode)
    sub.delete()
    msg = "Completed Successfully"
    return redirect("/subjects")


@app.route('/removetutor?tutorid=<tutorid>')
@admin_permission.require()
def remove_tutor(tutorid):
    tut = Tutor.query.get(tutorid)
    tut.delete()
    msg = "Completed Successfully"
    return redirect("/tutors")


@app.route('/removesubjectfromtutor?tutorid=<tutorid>&subcode=<subcode>')
@admin_permission.require()
def remove_subject_from_tutor(tutorid, subcode):
    msg = unlinksubjecttutor(tutorid, subcode)
    return redirect(request.referrer)
    # return redirect(url_for('view_tutor', tutorid=tutorid))

@app.route('/removesubjectfromstudent?studentcode=<studentcode>&subcode=<subcode>')
@admin_permission.require()
def remove_subject_from_student(studentcode, subcode):
    msg = unlinksubjectstudent(studentcode, subcode)
    return redirect(request.referrer)


@app.route('/removetimetabledclass?timetabledclassid=<timetabledclassid>')
@admin_permission.require()
def remove_timetabled_class(timetabledclassid):
    timetabledclass = TimetabledClass.query.get(timetabledclassid)
    subject = timetabledclass.subject
    db.session.delete(timetabledclass)
    db.session.commit()
    if subject.timetabledclasses is not None:
        if len(subject.timetabledclasses) == 1:
            for tutorial in subject.timetabledclasses:
                tutorial.students = subject.students
                db.session.commit()
    return redirect(request.referrer)


@app.route('/removetimeslot?timeslotid=<timeslotid>')
@admin_permission.require()
def remove_timeslot(timeslotid):
    timeslot = Timeslot.query.get(timeslotid)
    timeslot.delete()
    return redirect("/timeslots")


# View Data Methods (TUTORS/TIMESLOTS/ROOMS/STUDENTS/ETC)
@app.route('/tutors', methods=['GET', 'POST'])
@login_required
def view_tutors():
    form = NameForm()
    if request.method == 'GET':
        return render_template('viewtutors.html', form=form)
    else:
        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            if Tutor.query.filter_by(name=name, year=get_current_year(),
                                     studyperiod=get_current_studyperiod()).first() is None:
                tut = Tutor(name=name,email=email)
                db.session.add(tut)
                db.session.commit()
            msg = "Record successfully added"
            return redirect("/tutors")
        return render_template('viewtutors.html',form=form)


@app.route('/rooms', methods=['GET', 'POST'])
@login_required
def view_rooms():
    form = JustNameForm()
    if request.method == 'GET':
        return render_template('viewrooms.html', form=form, rooms=Room.get_all_sorted(), timeslots=Timeslot.get_all())
    else:
        if form.validate_on_submit():
            name = form.name.data
            if Room.query.filter_by(name=name).first() is None:
                room = Room(name=name)
                db.session.add(room)
                db.session.commit()
            msg = "Record successfully added"
            return redirect("/rooms")
        return render_template('viewrooms.html', form=form, rooms=Room.get_all_sorted(), timeslots=Timeslot.get_all())


@app.route('/addtutorial', methods=['POST'])
def add_tutorial():
    return redirect(request.referrer)




@app.route('/universities', methods=['GET', 'POST'])
@login_required
def view_universities():
    form = JustNameForm()
    if request.method == 'GET':
        return render_template('viewuniversities.html', form=form)
    else:
        if form.validate_on_submit():
            name = form.name.data
            if University.query.filter_by(name=name).first() is None:
                uni = University(name=name)
                db.session.add(uni)
                db.session.commit()
            msg = "Record successfully added"
            return redirect("/universities")
        return render_template('viewuniversities.html', form=form)


@app.route('/colleges', methods=['GET', 'POST'])
@login_required
def view_colleges():
    form = JustNameForm()
    if request.method == 'GET':
        return render_template('viewcolleges.html', form=form)
    else:
        if form.validate_on_submit():
            name = form.name.data
            if College.query.filter_by(name=name).first() is None:
                college = College(name=name)
                db.session.add(college)
                db.session.commit()
            msg = "Record successfully added"
            return redirect("/colleges")
        return render_template('viewcolleges.html', form=form)



@app.route('/subjects', methods=['GET', 'POST'])
@login_required
def view_subjects():
    form = AddSubjectForm()
    if request.method == 'GET':
        return render_template('subjects.html', form=form)
    elif request.method == 'POST':
        if form.validate_on_submit() and int(current_user.is_admin) == 1:
            subname = form.subname.data
            subcode = form.subcode.data
            if Subject.query.filter_by(subcode=subcode, year=get_current_year(),
                                       studyperiod=get_current_studyperiod()).first() is None:
                sub = Subject(subcode=subcode, subname=subname)
                db.session.add(sub)
                db.session.commit()
            msg = "Record successfully added"
            return redirect("/subjects")
        return render_template('subjects.html', form=form)


@app.route('/viewclashreport')
@admin_permission.require()
def viewclashreport():
    return render_template("viewclashreport.html")

@app.route('/timetable', methods=['GET', 'POST'])
@login_required
def view_timetable():
    form = AddTimetableForm()
    if request.method == 'GET':
        return render_template('viewtimetable.html', form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            Timetable.create(key=form.key.data)
        return redirect('/timetable')


@app.route('/timeslots', methods=['GET', 'POST'])
@login_required
def view_timeslots():
    form = TimeslotForm()
    if request.method == 'GET':
        return render_template('viewtimeslots.html', form=form)
    else:
        if form.validate_on_submit():
            day = form.day.data
            time = form.time.data
            Timeslot.get_or_create(day=day, time=time)
        return render_template('viewtimeslots.html', form=form)


@app.route('/tutoravailability')
@admin_permission.require()
def managetutoravailability():
    return render_template("tutoravailability.html", timeslots=Timeslot.get_all(), tutors=Tutor.get_all())


@app.route('/students', methods=['GET', 'POST'])
@login_required
def view_students():
    form = StudentForm()
    colleges = College.query.all()
    choices = [(-1, "")]
    for college in colleges:
        choices.append((int(college.id), college.name))
    form.college.choices = choices
    universities = University.query.all()
    choices = [(-1, "")]
    for university in universities:
        choices.append((int(university.id), university.name))
    form.university.choices = choices
    if request.method == 'GET':
        return render_template('viewstudents.html', form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            name = form.name.data
            studentcode = form.studentcode.data
            email = form.email.data
            universityid = form.university.data
            collegeid = form.college.data
            Student.create(name=name, studentcode=studentcode, email=email, universityid=universityid,
                           collegeid=collegeid)
            return redirect('/students')
        return render_template('viewstudents.html', form=form)


@app.route('/users')
@admin_permission.require()
def view_users():
    form = LoginForm()
    return render_template('viewusers.html', form=form)


#VIEW INDIVIDUAL PAGES

@app.route('/viewstudent?studentcode=<studentcode>', methods=['GET', 'POST'])
@login_required
def view_student(studentcode):
    student = Student.get(studentcode=studentcode)
    form = StudentForm(obj=student)
    colleges = College.query.all()
    choices = [(-1, "")]
    for college in colleges:
        choices.append((int(college.id), college.name))
    form.college.choices = choices
    universities = University.query.all()
    choices = [(-1, "")]
    for university in universities:
        choices.append((int(university.id), university.name))
    form.university.choices = choices
    if request.method == 'GET':
        if student.university is not None:
            form.university.data = student.university.id
        if student.college is not None:
            form.college.data = student.college.id
        return student.view_student_template(form)
    elif request.method == 'POST' and current_user.is_admin:
        if form.validate_on_submit():
            student.update(name=form.name.data, email=form.email.data, studentcode=form.studentcode.data,
                           universityid=form.university.data, collegeid=form.college.data)
            redirect(url_for('view_student', studentcode=studentcode))
        return student.view_student_template(form)


@app.route('/viewtutor?tutorid=<tutorid>', methods=['GET', 'POST'])
@login_required
def view_tutor(tutorid):
    tutor = Tutor.query.get(tutorid)
    form = EditTutorForm(obj=tutor)
    users = User.get_all()
    choices = [(-1, "")]
    for user in users:
        choices.append((int(user.id), user.username))
    form.user.choices = choices
    if current_user.is_admin == '1' or int(current_user.tutor.id) == int(tutorid):
        if request.method == 'GET':
            if tutor.user is not None:
                form.user.data = tutor.user.id
            return tutor.view_tutor_template(form)
        elif request.method == 'POST':
            if form.validate_on_submit():
                tutor.name = form.name.data
                tutor.email = form.email.data
                if form.user.data != -1:
                    tutor.user = User.query.get(form.user.data)
                    db.session.commit()
                else:
                    tutor.user = None
                    db.session.commit()
            return redirect(url_for('view_tutor', tutorid=tutorid))
    else:
        return redirect('/')


@app.route('/subject?subcode=<subcode>', methods=['GET', 'POST'])
@login_required
def view_subject(subcode):
    subject = Subject.get(subcode=subcode)
    form = AddSubjectForm(obj=subject)
    if current_user.is_admin == '1' or current_user.tutor == subject.tutor:
        if request.method == 'GET':
            return subject.view_subject_template(form)
        elif request.method == 'POST':
            if form.validate_on_submit():
                subject.update(**form.data)
                # subject.subcode = form.subcode.data
                # subject.subname = form.subname.data
                # db.session.commit()
            return redirect(url_for('view_subject', subcode=subcode))
    else:
        return redirect('/')

@app.route('/viewuser?username=<username>')
@login_required
def view_user(username):
    user = User.get(username=username)
    return user.view_user_template()


@app.route('/runtimetableprogram', methods=['GET', 'POST'])
@admin_permission.require()
def run_timetable_program():
    preparetimetable()
    return "Done"


# APP ERROR HANDLERS
@app.errorhandler(404)
def page_not_found(e):
    app.logger.error('Page not found: %s', (request.path))
    return render_template("ErrorPage.html", code=404), 404


@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error('Server Error: %s', (error))
    return render_template('ErrorPage.html', code=500), 500


# AJAX ROUTES
@app.route('/viewtimeslotsajax')
@admin_permission.require()
def viewtimeslots_ajax():
    data = Timeslot.get_all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
        row['timetabledclasses'] = []
        row['tutor'] = []
        row['availabiletutors'] = []
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewtimetableajax')
@login_required
def viewtimetable_ajax():
    data = TimetabledClass.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod()).options(
        joinedload('tutor'), joinedload('room')).all()
    data2 = []

    for row3 in data:
        data2.append(row3.__dict__)
    for i in range(len(data2)):
        data2[i]['timeslot'] = Timeslot.query.get(data2[i]['time'])
        data2[i]['tutor'] = Tutor.query.filter_by(id=data2[i]['tutorid']).first()
        data2[i]['subject'] = Subject.query.filter_by(id=data2[i]['subjectid']).first()
    for i in range(len(data2)):
        data2[i]['tutor'] = data2[i]['tutor'].__dict__
        data2[i]['tutor']['_sa_instance_state'] = ""
        data2[i]['subject'] = data2[i]['subject'].__dict__
        data2[i]['subject']['_sa_instance_state'] = ""
        data2[i]['subject']['students'] = []
        data2[i]['subject']['tutor'] = ""
        data2[i]['students'] = []
        data2[i]['_sa_instance_state'] = ""
        data2[i]['timeslot'] = data2[i]['timeslot'].__dict__
        data2[i]['timeslot']['_sa_instance_state'] = ""
        data2[i]['timeslot']['availabiletutors'] = []
        data2[i]['timeslot']['timetabledclasses'] = []
        data2[i]['timetabledclasses'] = []
        if data2[i]['room'] is not None:
            data2[i]['room'] = data2[i]['room'].__dict__
            data2[i]['room']['_sa_instance_state'] = ""
        else:
            data2[i]['room'] = {}
            data2[i]['room']['name'] = ""
    data = json.dumps(data2)

    return '{ "data" : ' + data + '}'


@app.route('/viewtutorsajax')
@admin_permission.require()
def viewtutors_ajax():
    data = Tutor.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod()).options(
        joinedload('subjects'), joinedload('availabletimes')).all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        data3 = []
        data4 = []
        row['_sa_instance_state'] = ""
        for sub in row['subjects']:
            q = sub.__dict__
            q['_sa_instance_state'] = ""
            data3.append(q)
        for time in row['availabletimes']:
            q = time.__dict__
            q['_sa_instance_state'] = ""
            data4.append(q)
        row['subjects'] = data3
        row['availabletimes'] = data4
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewroomsajax')
@admin_permission.require()
def viewrooms_ajax():
    data = Room.query.all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewuniversitiesajax')
@admin_permission.require()
def viewuniversities_ajax():
    data = University.query.all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewcollegesajax')
@admin_permission.require()
def viewcolleges_ajax():
    data = College.query.all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'

@app.route('/viewusersajax')
@admin_permission.require()
def viewusers_ajax():
    data = User.query.options(joinedload('tutor')).all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
        if row['tutor'] is not None:
            row['tutor'] = row['tutor'].__dict__
            row['tutor']['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewstudentsajax')
@admin_permission.require()
def viewstudents_ajax():
    data = Student.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod())
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewcurrentmappedsubjectsajax')
@admin_permission.require()
def viewcurrentmappedsubjects_ajax():
    data = Subject.query.filter(Subject.year == get_current_year(), Subject.studyperiod == get_current_studyperiod(),
                                Subject.tutor != None).options(joinedload('students')).all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
        row['students'] = len(row['students'])
        row['tutor'] = row['tutor'].__dict__
        row['tutor']['_sa_instance_state'] = ""
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/updatepreferredtimeslot', methods=['POST'])
@admin_permission.require()
def update_preferred_timeslot():
    id = int(request.form['id'])
    preferred = int(request.form['preferred'])
    timetabler.models.change_preferred_timeslot(id, preferred)
    return "Done"


@app.route('/updateroomprojector', methods=['POST'])
@admin_permission.require()
def update_room_projector2():
    roomid = int(request.form['roomid'])
    value = int(request.form['value'])
    timetabler.models.change_room_projector(roomid, value)
    return "Done"


@app.route('/vieweligiblesubjectsajax')
@admin_permission.require()
def vieweligiblesubjects_ajax():
    data = Subject.query.options(joinedload('students')).filter(Subject.year == get_current_year(),
                                                                Subject.studyperiod == get_current_studyperiod(),
                                                                Subject.tutor == None).all()
    data2 = []
    for subject in data:
        if len(subject.students) >= 3:
            data2.append(subject)
    data3 = []
    for row in data2:
        data3.append(row.__dict__)
    for row in data3:
        row['_sa_instance_state'] = ""
        row['students'] = len(row['students'])
    data = json.dumps(data3)
    return '{ "data" : ' + data + '}'



@app.route('/numbereligiblesubjectsmappedajax')
@login_required
def num_eligible_subjects_mapped():
    subjects = Subject.query.filter(Subject.tutor != None, Subject.year == get_current_year(),
                                    Subject.studyperiod == get_current_studyperiod()).all()

    allsubjects = Subject.query.filter(Subject.tutor == None, Subject.year == get_current_year(),
                                       Subject.studyperiod == get_current_studyperiod()).all()
    eligiblesubjects = [subject for subject in allsubjects if len(subject.students) >= 3]
    data = {}
    data['Eligible Subjects'] = len(eligiblesubjects)
    data['Mapped Subjects'] = len(subjects)
    data = json.dumps(data)
    return data


@app.route('/viewclashesajax')
@admin_permission.require()
def viewclashreportajax():
    timeslots = Timeslot.get_all()
    clashes = {}
    for timeslot in timeslots:
        clashestimeslot = {}
        students = []
        clashstudents = []
        for timeclass in timeslot.timetabledclasses:
            for student in timeclass.students:
                if student not in students:
                    clashestimeslot[student.id] = {}
                    clashestimeslot[student.id]['student'] = student
                    clashestimeslot[student.id]['timeslot'] = timeslot
                    clashestimeslot[student.id]['subjects'] = []
                    students.append(student)
                clashestimeslot[student.id]['subjects'].append(timeclass.subject.subname)
                if len(clashestimeslot[student.id]['subjects']) >= 2:
                    clashstudents.append(student.id)
        clashes[timeslot.id] = {key: clashestimeslot[key] for key in clashstudents}
        clashes[timeslot.id]['time'] = timeslot.day + " " + timeslot.time

    data2 = []
    for row in clashes.keys():
        if clashes[row] != {}:
            for key in clashes[row].keys():
                if isinstance(clashes[row][key], dict):
                    data2.append(clashes[row][key])

    for row in data2:
        # row['_sa_instance_state'] = ""

        row['timeslot'] = row['timeslot'].__dict__
        row['timeslot']['_sa_instance_state'] = ""
        row['student'] = row['student'].__dict__
        row['student']['_sa_instance_state'] = ""
        row['timeslot']['availabiletutors'] = []
        row['timeslot']['timetabledclasses'] = []

    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/updatesubjectrepeats', methods=['POST'])
@admin_permission.require()
def update_subject_repeats():
    subject = Subject.query.get(int(request.form['subject']))
    subject.update(repeats=int(request.form['repeats']))
    return "Done"

@app.route('/needsprojectorchange', methods=['POST'])
@admin_permission.require()
def update_needsprojector():
    subject = Subject.query.get(int(request.form['subjectid']))
    value = int(request.form['value'])
    if value == 1:
        subject.needsprojector = True
        db.session.commit()
    elif value == 0:
        subject.needsprojector = False
        db.session.commit()
    return "Done"

@app.route('/changepreferredtime', methods=['POST'])
@admin_permission.require()
def change_preferred_time():
    timeslot = Timeslot.query.get(int(request.form['timeslotid']))
    value = int(request.form['value'])
    if value == 1:
        timeslot.update(preferredtime = True)
    elif value == 0:
        timeslot.update(preferredtime=False)
    return "Done"


@app.route('/updateroomprojector', methods=['POST'])
@admin_permission.require()
def update_room_projector():
    room = Room.query.get(int(request.form['roomid']))
    value = int(request.form['value'])
    if value == 1:
        room.projector = True
        db.session.commit()
    elif value ==0:
        room.projector = False
        db.session.commit()
    return "Done"


@app.route('/viewsubjectsajax')
@login_required
def viewsubjects_ajax():
    data = Subject.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod()).options(
        joinedload('students')).all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
        row['students'] = len(row['students'])
        row['tutor'] = []
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/viewmysubjectsajax')
@login_required
def viewmysubjects_ajax():
    data = Subject.query.filter_by(year=get_current_year(), studyperiod=get_current_studyperiod(),
                                   tutor=current_user.tutor).options(
        joinedload('students')).all()
    data2 = []
    for row in data:
        data2.append(row.__dict__)
    for row in data2:
        row['_sa_instance_state'] = ""
        row['students'] = len(row['students'])
        row['tutor'] = []
    data = json.dumps(data2)
    return '{ "data" : ' + data + '}'


@app.route('/useradminajax', methods=['POST'])
@admin_permission.require()
def user_admin_ajax():
    user = User.query.get(int(request.form['user_id']))
    adminvalue = int(request.form['admin'])
    if user.is_admin == '1' and user.username != 'admin':
        if adminvalue == 0:
            user.is_admin = '0'
            db.session.commit()
    else:
        if adminvalue == 1:
            print(adminvalue)
            user.is_admin = '1'
            db.session.commit()
    print(user.is_admin)
    return "Done"


@app.route('/maptutoruserajax', methods=['POST'])
@admin_permission.require()
def user_tutor_mapping():
    user = User.query.get(int(request.form['user_id']))
    if int(request.form['tutor_id']) != -1:
        tutor = Tutor.query.get(int(request.form['tutor_id']))
        user.tutor = tutor
        db.session.commit()
    else:
        user.tutor = None
        db.session.commit()
    return "Done"


@app.route('/updatetutoravailabilityajax', methods=['POST'])
@login_required
def update_tutor_availability_ajax():
    timeslotid = int(request.form['timeslotid'])
    tutorid = int(request.form['tutorid'])
    timeslot = Timeslot.query.get(timeslotid)
    tutor = Tutor.query.get(tutorid)
    if timeslot in tutor.availabletimes:
        tutor.availabletimes.remove(timeslot)
    else:
        tutor.availabletimes.append(timeslot)
    db.session.commit()
    return json.dumps("Done")


@app.route('/updateclassroomajax', methods=['POST'])
@login_required
def update_class_room_ajax():
    timeclass = TimetabledClass.get(id=int(request.form['timeclassid']))
    if int(request.form['roomid']) != -1:
        room = Room.query.get(int(request.form['roomid']))
        timeclass.update(room=room)
    else:
        timeclass.update(room=None)
    return json.dumps("Done")


@app.route('/updatestudentscheduledclassajax', methods=['POST'])
@login_required
def update_student_scheduled_class_ajax():
    timeclassid = int(request.form['timeclassid'])
    studentid = int(request.form['studentid'])
    timeclass = TimetabledClass.query.get(timeclassid)
    student = Student.query.get(studentid)
    subject = timeclass.subject
    if student not in timeclass.students:
        for timeclass2 in subject.timetabledclasses:
            if student in timeclass2.students:
                timeclass2.students.remove(student)
        timeclass.students.append(student)
    db.session.commit()
    return json.dumps("Done")


@app.route('/downloadroll?classid=<classid>')
@login_required
def download_roll(classid):
    document = get_roll(classid)
    return send_file(document, as_attachment=True)


@app.route('/downloadrolls')
@login_required
def download_all_rolls():
    document = get_all_rolls()
    return send_file(document, as_attachment=True)


@app.route('/downloadtimetable')
@login_required
def download_timetable():
    timetable = format_timetable_data_for_export()
    timetable = create_excel(timetable)
    return send_file(timetable, as_attachment=True)


@app.route('/downloadindividualtimetables')
@login_required
def download_individual_student_timetables():
    timetable = format_student_timetable_data_for_export()
    timetable = create_excel(timetable)
    return send_file(timetable, as_attachment=True)
