import datetime
import inspect
import jwt
import os
import psycopg2
import pytz
import time

from flask import Flask, request, jsonify, make_response
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

def get_db_connection():
    conn = psycopg2.connect(host = os.environ.get("host"), database = os.environ.get("database"), user = os.environ.get("user"), password = os.environ.get("password"))
    return conn

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('token')
        if not token:
            return make_response(jsonify({"message": "Missing token"}), 400)
        try:
            login = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    *
                FROM
                    (
                        SELECT
                            user_code,route_name,route_method
                        FROM
                            m_user_route
                        UNION ALL
                        SELECT
                            'administrator' user_code,route_name,route_method
                        FROM
                            b_route
                    ) x
                WHERE
                    user_code = %s AND route_name = %s AND route_method = %s
            """, (login['user_code'], f.__name__, request.method))
            datas = cur.fetchall()
            cur.close()
            conn.close()
            if datas:
                app.config['USER_CODE'] = login['user_code']
            else:
                return make_response(jsonify({"message": "Not authorized"}), 400)
        except:
            return make_response(jsonify({"message": "Invalid ENV"}), 400)
        return f(*args, **kwargs)
    return decorator

def log_response(message, code):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO
            l_user_response(user_code, route_name, route_method, request_time, response_code, response_message)
        VALUES
            (%s, %s, %s, %s, %s, %s)
    """, (app.config['USER_CODE'], calframe[1][3], request.method, datetime.datetime.now(), code, message))
    conn.commit()
    cur.close()
    conn.close()
    return make_response(jsonify({"message": message}), code)

def filter(content):
    filters = []
    if 'filters' in content:
        filters=content['filters']
    filter_type = ""
    if 'filter_type' in content:
        filter_type=content['filter_type']
    temp = '1=1'
    if filter_type == "OR":
        temp = '0=1'
    for filter in filters:
        if filter['operator'] == 'is equal to':
            temp = temp + " " + filter_type + " " + filter['search'] + "='" + filter['value1'] + "' "
        if filter['operator'] == 'is not equal to':
            temp = temp + " " + filter_type + " " + filter['search'] + "<>'" + filter['value1'] + "' "
        if filter['operator'] == 'is less than':
            temp = temp + " " + filter_type + " " + filter['search'] + "<'" + filter['value1'] + "' "
        if filter['operator'] == 'is less than or equal to':
            temp = temp + " " + filter_type + " " + filter['search'] + "<='" + filter['value1'] + "' "
        if filter['operator'] == 'is greater than':
            temp = temp + " " + filter_type + " " + filter['search'] + ">'" + filter['value1'] + "' "
        if filter['operator'] == 'is greater than or equal to':
            temp = temp + " " + filter_type + " " + filter['search'] + ">='" + filter['value1'] + "' "
        if filter['operator'] == 'contains':
            temp = temp + " " + filter_type + " " + filter['search'] + " ILIKE '%" + filter['value1'] + "%' "
        if filter['operator'] == 'does not contain':
            temp = temp + " " + filter_type + " " + filter['search'] + " NOT ILIKE '%" + filter['value1'] + "%' "
        if filter['operator'] == 'is between':
            temp = temp + " " + filter_type + " " + filter['search'] + " BETWEEN '" + filter['value1'] + "' AND '" + filter['value2'] + "' "
        if filter['operator'] == 'is not between':
            temp = temp + " " + filter_type + " NOT(" + filter['search'] + " BETWEEN '" + filter['value1'] + "' AND '" + filter['value2'] + "') "
    return temp

def sort(content):
    sorts = []
    if 'sorts' in content:
        sorts=content['sorts']
    temp = ''
    for sort in sorts:
        if temp == '':
            temp = """
                ORDER BY
                    """ + sort['field'] + """ """ + sort['order']
        else:
            temp = temp + ", " + sort['field'] + " " + sort['order']
    return temp

def organization_school_json(data):
    return {'organization_code': data[0], 'employee_code': data[1], 'school_address': data[2], 'school_phone': data[3], 'school_city': data[4], 'organization_school_note': data[5], 'is_active': data[6], 'create_by': data[7], 'create_date': data[8], 'update_by': data[9], 'update_date': data[10]}

@app.route('/organization_schools/', methods = ['GET','POST'])
@token_required
def organization_schools():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_organization_school
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        organization_schools = []
        for data in datas:
            organization_schools.append(organization_school_json(data))
        return make_response(jsonify({"data": organization_schools}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    m_organization_school(organization_code, employee_code, school_address, school_phone, school_city, organization_school_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['organization_code'], content['employee_code'], content['school_address'], content['school_phone'], content['school_city'], content['organization_school_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/organization_school/<organization_code>', methods = ['GET','PUT','DELETE'])
@token_required
def organization_school(organization_code):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_organization_school
            WHERE
                organization_code = %s
        """, (organization_code,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        organization_schools = []
        for data in datas:
            organization_schools.append(organization_school_json(data))
        return make_response(jsonify({"data": organization_schools}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    m_organization_school
                SET
                    organization_code = %s, employee_code = %s, school_address = %s, school_phone = %s, school_city = %s, organization_school_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    organization_code = %s
            """, (content['organization_code'], content['employee_code'], content['school_address'], content['school_phone'], content['school_city'], content['organization_school_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    m_organization_school
                WHERE
                    organization_code = %s
            """, (organization_code,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/organization_school_paging/', methods = ['POST'])
@token_required
def organization_school_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            m_organization_school
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    organization_schools = []
    for data in datas:
        organization_schools.append(organization_school_json(data))
    return make_response(jsonify({"data": organization_schools}), 200)

def school_level_json(data):
    return {'school_level_code': data[0], 'school_level_description': data[1], 'school_level_note': data[2], 'is_active': data[3], 'create_by': data[4], 'create_date': data[5], 'update_by': data[6], 'update_date': data[7]}

@app.route('/school_levels/', methods = ['GET','POST'])
@token_required
def school_levels():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_school_level
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        school_levels = []
        for data in datas:
            school_levels.append(school_level_json(data))
        return make_response(jsonify({"data": school_levels}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    m_school_level(school_level_code, school_level_description, school_level_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['school_level_code'], content['school_level_description'], content['school_level_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/school_level/<school_level_code>', methods = ['GET','PUT','DELETE'])
@token_required
def school_level(school_level_code):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_school_level
            WHERE
                school_level_code = %s
        """, (school_level_code,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        school_levels = []
        for data in datas:
            school_levels.append(school_level_json(data))
        return make_response(jsonify({"data": school_levels}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    m_school_level
                SET
                    school_level_code = %s, school_level_description = %s, school_level_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    school_level_code = %s
            """, (content['school_level_code'], content['school_level_description'], content['school_level_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), school_level_code))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    m_school_level
                WHERE
                    school_level_code = %s
            """, (school_level_code,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/school_level_paging/', methods = ['POST'])
@token_required
def school_level_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            m_school_level
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    school_levels = []
    for data in datas:
        school_levels.append(school_level_json(data))
    return make_response(jsonify({"data": school_levels}), 200)

# m_room
        
def room_json(data):
    return {'room_code': data[0], 'room_name': data[1], 'room_note': data[2], 'is_active': data[3], 'create_by': data[4], 'create_date': data[5], 'update_by': data[6], 'update_date': data[7]}

@app.route('/rooms/', methods = ['GET','POST'])
@token_required
def rooms():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_room
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        rooms = []
        for data in datas:
            rooms.append(room_json(data))
        return make_response(jsonify({"data": rooms}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    m_room(room_code, room_name, room_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['room_code'], content['room_name'], content['room_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/room/<room_code>', methods = ['GET','PUT','DELETE'])
@token_required
def room(room_code,):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_room
            WHERE
                room_code = %s
        """, (room_code,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        rooms = []
        for data in datas:
            rooms.append(room_json(data))
        return make_response(jsonify({"data": rooms}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    m_room
                SET
                    room_code = %s, room_name = %s, room_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    room_code = %s
            """, (content['room_code'], content['room_name'], content['room_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), room_code))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    m_room
                WHERE
                    room_code = %s
            """, (room_code,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/room_paging/', methods = ['POST'])
@token_required
def room_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            m_room
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    rooms = []
    for data in datas:
        rooms.append(room_json(data))
    return make_response(jsonify({"data": rooms}), 200)

# m_document_type
        
def document_type_json(data):
    return {'document_type_code': data[0], 'document_type_description': data[1], 'document_type_note': data[2], 'is_active': data[3], 'create_by': data[4], 'create_date': data[5], 'update_by': data[6], 'update_date': data[7]}

@app.route('/document_types/', methods = ['GET','POST'])
@token_required
def document_types():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_document_type
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        document_types = []
        for data in datas:
            document_types.append(document_type_json(data))
        return make_response(jsonify({"data": document_types}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    m_document_type(document_type_code, document_type_description, document_type_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['document_type_code'], content['document_type_description'], content['document_type_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/document_type/<document_type_code>', methods = ['GET','PUT','DELETE'])
@token_required
def document_type(document_type_code,):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                m_document_type
            WHERE
                document_type_code = %s
        """, (document_type_code,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        document_types = []
        for data in datas:
            document_types.append(document_type_json(data))
        return make_response(jsonify({"data": document_types}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    m_document_type
                SET
                    document_type_code = %s, document_type_description = %s, document_type_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    document_type_code = %s
            """, (content['document_type_code'], content['document_type_description'], content['document_type_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), document_type_code))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    m_document_type
                WHERE
                    document_type_code = %s
            """, (document_type_code,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/document_type_paging/', methods = ['POST'])
@token_required
def document_type_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            m_document_type
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    document_types = []
    for data in datas:
        document_types.append(document_type_json(data))
    return make_response(jsonify({"data": document_types}), 200)

# t_booking
# now = datetime.time
def booking_json(data):
    return {'booking_no': data[0], 'room_code': data[1], 'booking_date': data[2], 'begin_time': data[3].strftime('%H:%M:%S'), 'end_time': data[4].strftime('%H:%M:%S'), 'booking_note': data[5], 'is_active': data[6], 'create_by': data[7], 'create_date': data[8], 'update_by': data[9], 'update_date': data[10]}
# WIB = pytz.timezone('Asia/Jakarta')

@app.route('/bookings/', methods = ['GET','POST'])
@token_required
def bookings():
    if request.method == 'GET':
        # conn = get_db_connection()
        # cur = conn.cursor()
        # cur.execute("""
        #     SELECT
        #         *
        #     FROM
        #         t_booking
        # """)
        # datas = cur.fetchall()
        # cur.close()
        # conn.close()
        # bookings = []
        # begin_timex = int(datetime.time(datas))
        # print(jsonify(begin_timex))
        # return 'a'
        # string_time = time.strftime("%H:%M:%S", datas)
        # integer_time = int(string_time)
        
        # for data in datas:
        #     bookings.append(booking_json(data,integer_time))
        # return make_response(jsonify({"data": bookings}), 200)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                booking_no,
                room_code,
                booking_date,
                begin_time,
                end_time,
                booking_note,
                is_active,
                create_by,
                create_date,
                update_by,
                update_date
            FROM
                t_booking
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        bookings = []
        for data in datas:
            bookings.append(booking_json(data))
        #     begin_time = data[3]
        #     end_time = str(data[4])
        # current_time = begin_time.time()
        # current_time_str = current_time.strftime('%H:%M:%S')
        # return jsonify({'current_time': current_time_str})
        return make_response(jsonify({"data": bookings}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    t_booking(booking_no, room_code, booking_date, begin_time, end_time, booking_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['booking_no'], content['room_code'], content['booking_date'], content['begin_time'], content['end_time'], content['booking_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/booking/<booking_no>', methods = ['GET','PUT','DELETE'])
@token_required
def booking(booking_no,):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                t_booking
            WHERE
                booking_no = %s
        """, (booking_no,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        bookings = []
        for data in datas:
            bookings.append(booking_json(data))
        return make_response(jsonify({"data": bookings}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    t_booking
                SET
                    booking_no = %s, room_code = %s, booking_date = %s, begin_time = %s, end_time = %s, booking_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    booking_no = %s
            """, (content['booking_no'], content['room_code'], content['booking_date'], content['begin_time'], content['end_time'], content['booking_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), booking_no))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    t_booking
                WHERE
                    booking_no = %s
            """, (booking_no,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/booking_paging/', methods = ['POST'])
@token_required
def booking_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            t_booking
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    bookings = []
    for data in datas:
        bookings.append(booking_json(data))
    return make_response(jsonify({"data": bookings}), 200)

# t_document
def document_json(data):
    return {'document_no': data[0], 'organization_code': data[1], 'period_code': data[2], 'document_type_code': data[3], 'document_subject': data[4], 'document_date': data[5], 'document_note': data[6], 'is_active': data[7], 'create_by': data[8], 'create_date': data[9], 'update_by': data[10], 'update_date': data[11]}

@app.route('/documents/', methods = ['GET','POST'])
@token_required
def documents():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                t_document
        """)
        datas = cur.fetchall()
        cur.close()
        conn.close()
        documents = []
        for data in datas:
            documents.append(document_json(data))
        return make_response(jsonify({"data": documents}), 200)
    elif request.method == 'POST':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO
                    t_document(document_no, organization_code, period_code, document_type_code, document_subject, document_date, document_note, is_active, create_by, create_date, update_by, update_date)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (content['document_no'], content['organization_code'], content['period_code'], content['document_type_code'], content['document_subject'], content['document_date'], content['document_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), app.config['USER_CODE'], datetime.datetime.now()))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/document/<document_no>', methods = ['GET','PUT','DELETE'])
@token_required
def document(document_no,):
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                *
            FROM
                t_document
            WHERE
                document_no = %s
        """, (document_no,))
        datas = cur.fetchall()
        cur.close()
        conn.close()
        documents = []
        for data in datas:
            documents.append(document_json(data))
        return make_response(jsonify({"data": documents}), 200)
    elif request.method == 'PUT':
        content = request.get_json()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE
                    t_document
                SET
                    document_no = %s, organization_code = %s, period_code = %s, document_type_code = %s, document_subject = %s, document_date = %s, document_note = %s, is_active = %s, update_by = %s, update_date = %s
                WHERE
                    document_no = %s
            """, (content['document_no'], content['organization_code'], content['period_code'], content['document_type_code'], content['document_subject'], content['document_date'], content['document_note'], content['is_active'], app.config['USER_CODE'], datetime.datetime.now(), document_no))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
    elif request.method == 'DELETE':
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM
                    t_document
                WHERE
                    document_no = %s
            """, (document_no,))
            conn.commit()
        except psycopg2.Error as e:
            return log_response(e.pgerror, 400)
        cur.close()
        conn.close()
        return log_response("Success", 200)
@app.route('/document_paging/', methods = ['POST'])
@token_required
def document_paging():
    content = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            *
        FROM
            t_document
        WHERE
            (""" + filter(content) + """) """ + sort(content) + """
        LIMIT
            """ + content['limit'] + """
        OFFSET
            """ + str(int(content['limit']) * (int(content['page']) - 1)))
    datas = cur.fetchall()
    cur.close()
    conn.close()
    documents = []
    for data in datas:
        documents.append(document_json(data))
    return make_response(jsonify({"data": documents}), 200)