appcfg = {
    # Path to upload files directory
    "upload": '/',
    # Database string
    "dbstring": 'sqlite:///database.sqlite',
    # Secret key for password hashing
    "secretkey": 'SECRET_KEY',
    # Administrator password
    "adminpassword": 'password',
    # Logging file
    "log": 'log.log',
    # Default start and study period
    "startyear": '2020',
    "startstudyperiod": "Semester 1",
    # Rooms avaliable (Name, HasProjector?, Capacity)
    "rooms" : [
        ['GHB1', True, 15],
        ['GHB2', True, 15],
        ['GHB3', True, 15],
        ['GHB4', False, 12],
        ['GHB5', False, 12],
        ['GHB6', False, 13],
        ['GHB7', False, 13],
        ['Peter Waylen', False, 18],
        ['Ronald Cowan', True, 20],
        ['Frank Larkins', False, 14],
        ['Mavis Jackson', True, 15],
        ['Royce Abbey', False, 20],
        ['Library Project Room', False, 6]
    ],
    # Timeslots avaliable and preference (True/False)
    "timeslots": [
        ['Monday 17:30', False],
        ['Monday 19:30', True],
        ['Monday 20:30', True],
        ['Monday 21:30', False],
        ['Tuesday 17:30', False],
        ['Tuesday 19:30', True],
        ['Tuesday 20:30', True],
        ['Tuesday 21:30', False],
        ['Wednesday 17:30', False],
        ['Wednesday 19:30', True],
        ['Wednesday 20:30',True],
        ['Wednesday 21:30', False]
    ],
    # Schema of XLS Enrolment File (mapping between column headers)
    "enrolment_schema": {
        "student_id": "Student Id",
        "student_first_name": "Given Name",
        "student_last_name": "Family Name",
        "subject_code": "Final Subject Code",
        "subject_name": "Final Subject Name",
        "study_period": "Study Period"
    },
    "max_class_size": 16,
    "min_class_size": 0,
    "default_room_capacity": 20
}
