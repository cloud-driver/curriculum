import io
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, timedelta
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100))
    location = db.Column(db.String(100))
    day_of_week = db.Column(db.Integer, nullable=False)
    items_to_bring = db.Column(db.Text)
    
    start_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    end_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    
    start_slot = db.relationship('TimeSlot', foreign_keys=[start_slot_id])
    end_slot = db.relationship('TimeSlot', foreign_keys=[end_slot_id])
    
class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(50), nullable=False)
    
def get_display_days():
    """根據資料庫設定，回傳要顯示的星期"""
    show_saturday = Setting.query.get('show_saturday').value == '1'
    show_sunday = Setting.query.get('show_sunday').value == '1'
    
    all_days = [("一", 0), ("二", 1), ("三", 2), ("四", 3), ("五", 4), ("六", 5), ("日", 6)]
    
    displayed_days = all_days[:5]
    if show_saturday:
        displayed_days.append(all_days[5])
    if show_sunday:
        displayed_days.append(all_days[6])
        
    return displayed_days

@app.route('/')
def index():
    time_slots = TimeSlot.query.order_by(TimeSlot.id).all()
    if not time_slots:
        return redirect(url_for('edit_time_slots'))

    all_courses = Course.query.all()
    schedule = {(c.day_of_week, c.start_slot_id): c for c in all_courses}
    
    cells_to_skip = set()
    for course in all_courses:
        if course.start_slot_id != course.end_slot_id:
            for slot_id in range(course.start_slot_id + 1, course.end_slot_id + 1):
                cells_to_skip.add((course.day_of_week, slot_id))

    today_weekday = datetime.today().weekday()
    today_courses = [c for c in all_courses if c.day_of_week == today_weekday]
    today_courses.sort(key=lambda x: x.start_slot.start_time)

    displayed_days = get_display_days()

    return render_template('index.html', time_slots=time_slots, schedule=schedule, cells_to_skip=cells_to_skip, 
                           today_courses=today_courses, displayed_days=displayed_days)
    
@app.route('/edit_course', methods=['GET', 'POST'])
def edit_course():
    day = int(request.args.get('day'))
    start_slot = int(request.args.get('start_slot'))
    end_slot = int(request.args.get('end_slot', start_slot))
    
    if request.method == 'POST':
        existing_courses = Course.query.filter(
            Course.day_of_week == day,
            Course.start_slot_id >= start_slot,
            Course.end_slot_id <= end_slot
        ).all()
        for c in existing_courses:
            db.session.delete(c)
        
        if request.form.get('name'):
            new_course = Course(
                name=request.form['name'],
                teacher=request.form['teacher'],
                location=request.form['location'],
                items_to_bring=request.form['items_to_bring'],
                day_of_week=day,
                start_slot_id=start_slot,
                end_slot_id=end_slot
            )
            db.session.add(new_course)
        
        db.session.commit()
        return redirect(url_for('index'))

    course = Course.query.filter_by(day_of_week=day, start_slot_id=start_slot).first()
    return render_template('course_form.html', course=course, day=day, start_slot=start_slot, end_slot=end_slot)


@app.route('/delete_course/<int:course_id>')
def delete_course(course_id):
    course = Course.query.get_or_44(course_id)
    db.session.delete(course)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/time_slots', methods=['GET', 'POST'])
def edit_time_slots():
    if request.method == 'POST':
        time_slots = TimeSlot.query.all()
        for slot in time_slots:
            slot.start_time = datetime.strptime(request.form[f'start_{slot.id}'], '%H:%M').time()
            slot.end_time = datetime.strptime(request.form[f'end_{slot.id}'], '%H:%M').time()
        
        setting_sat = Setting.query.get('show_saturday')
        setting_sun = Setting.query.get('show_sunday')
        setting_sat.value = '1' if 'show_saturday' in request.form else '0'
        setting_sun.value = '1' if 'show_sunday' in request.form else '0'
        
        db.session.commit()
        return redirect(url_for('index'))
    
    time_slots = TimeSlot.query.order_by(TimeSlot.id).all()
    show_saturday = Setting.query.get('show_saturday').value
    show_sunday = Setting.query.get('show_sunday').value

    return render_template('time_slots.html', time_slots=time_slots, 
                           show_saturday=show_saturday, show_sunday=show_sunday)

@app.route('/add_time_slot')
def add_time_slot():
    """新增一節課到時間設定中"""
    last_slot = TimeSlot.query.order_by(TimeSlot.id.desc()).first()
    if last_slot:
        new_id = last_slot.id + 1
        last_end_time = datetime.combine(datetime.today(), last_slot.end_time)
        new_start_dt = last_end_time + timedelta(minutes=10)
        new_end_dt = new_start_dt + timedelta(minutes=50)
        new_slot = TimeSlot(id=new_id, start_time=new_start_dt.time(), end_time=new_end_dt.time())
    else:
        new_slot = TimeSlot(id=1, start_time=time(8, 0), end_time=time(8, 50))
    
    db.session.add(new_slot)
    db.session.commit()
    return redirect(url_for('edit_time_slots'))

@app.route('/delete_time_slot/<int:slot_id>')
def delete_time_slot(slot_id):
    """刪除一節課的時間設定（會一併刪除該時段的所有課程）"""
    slot_to_delete = TimeSlot.query.get_or_404(slot_id)
    db.session.delete(slot_to_delete)
    db.session.commit()
    return redirect(url_for('edit_time_slots'))

@app.route('/export')
def export_excel():
    time_slots = TimeSlot.query.order_by(TimeSlot.id).all()
    courses = Course.query.all()
    schedule = {(c.day_of_week, c.start_slot_id): c for c in courses}
    
    displayed_days = get_display_days()
    day_names = [day[0] for day in displayed_days]
    day_indices = [day[1] for day in displayed_days]

    data = []
    for slot in time_slots:
        row_data = {
            "節次": f"第{slot.id}節",
            "時間": f"{slot.start_time.strftime('%H:%M')}\n{slot.end_time.strftime('%H:%M')}"
        }
        for day_name, day_index in zip(day_names, day_indices):
            course = schedule.get((day_index, slot.id))
            if course:
                row_data[day_name] = f"{course.name}\n{course.teacher}\n{course.location}"
            else:
                row_data[day_name] = ""
        data.append(row_data)
        
    df = pd.DataFrame(data)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='我的課表')
        worksheet = writer.sheets['我的課表']

        for course in courses:
            if course.start_slot_id < course.end_slot_id and course.day_of_week in day_indices:
                start_r = course.start_slot_id + 1
                end_r = course.end_slot_id + 1
                col = day_indices.index(course.day_of_week) + 3
                worksheet.merge_cells(start_row=start_r, start_column=col, end_row=end_r, end_column=col)

        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                cell.alignment = cell.alignment.copy(wrap_text=True, vertical='center', horizontal='center')
                try:
                    if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                except: pass
            adjusted_width = (max_length + 2) * 1.2
            worksheet.column_dimensions[column].width = adjusted_width if adjusted_width > 10 else 10

    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='我的課表.xlsx')
    
@app.cli.command("init-db")
def init_db_command():
    db.drop_all()
    db.create_all()
    default_times = [
        ("08:10", "09:00"), ("09:10", "10:00"), ("10:20", "11:10"), ("11:20", "12:10"),
        ("12:20", "13:10"), ("13:30", "14:20"), ("14:30", "15:20"), ("15:40", "16:30"),
        ("16:40", "17:30"), ("17:40", "18:30"), ("18:40", "19:25")
    ]
    for i, (start, end) in enumerate(default_times, 1):
        db.session.add(TimeSlot(id=i, start_time=datetime.strptime(start, '%H:%M').time(), end_time=datetime.strptime(end, '%H:%M').time()))
    
    db.session.add(Setting(key='show_saturday', value='1'))
    db.session.add(Setting(key='show_sunday', value='0'))
    
    db.session.commit()
    print("Initialized the database with default time slots and display settings.")

if __name__ == '__main__':
    app.run(debug=True)