import random
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import matplotlib.pyplot as plt
import os, os.path
import csv
from flask import make_response
from werkzeug.utils import secure_filename

TEMP_UPLOAD_FOLDER = 'temp'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///measurements.db'
app.config['TEMP_UPLOAD_FOLDER'] = TEMP_UPLOAD_FOLDER
db = SQLAlchemy(app)


class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    group_name = db.Column(db.String(50))
    voltage = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


@app.route('/', defaults={'path': ''})
@app.route('/<string:path>')
@app.route('/<path:path>')
def catch_random_paths(path):
    """
    Catches all URL paths that aren't specified and sends to the home page.
    """
    return redirect('/home')


@app.route('/home', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        group_name = request.form['group_name']
        voltage_min = float(request.form['voltage_min'])
        voltage_max = float(request.form['voltage_max'])
        temperature_min = float(request.form['temperature_min'])
        temperature_max = float(request.form['temperature_max'])
        humidity_min = float(request.form['humidity_min'])
        humidity_max = float(request.form['humidity_max'])
        num_measurements = int(request.form['num_measurements'])

        last_group = Measurement.query.order_by(Measurement.group_id.desc()).first()
        group_id = 1 if last_group is None else last_group.group_id + 1

        if not group_name:
            group_name = "Measurement"
            suffix = 0
            unique_group_name = group_name
            while Measurement.query.filter_by(group_name=unique_group_name).first():
                suffix += 1
                unique_group_name = f"{group_name} ({suffix})"
            group_name = unique_group_name

        elif Measurement.query.filter_by(group_name=group_name).first():
            suffix = 0
            unique_group_name = group_name
            while Measurement.query.filter_by(group_name=unique_group_name).first():
                suffix += 1
                unique_group_name = f"{group_name} ({suffix})"
            group_name = unique_group_name

        if not num_measurements:
            num_measurements = 50

        for _ in range(num_measurements):
            voltage = random.uniform(voltage_min, voltage_max)
            temperature = random.uniform(temperature_min, temperature_max)
            humidity = random.uniform(humidity_min, humidity_max)

            # voltage = round(random.uniform(voltage_min, voltage_max), 2)
            # temperature = round(random.uniform(temperature_min, temperature_max), 2)
            # humidity = round(random.uniform(humidity_min, humidity_max), 2)

            measurement = Measurement(group_id=group_id, group_name=group_name, voltage=voltage, temperature=temperature, humidity=humidity)
            db.session.add(measurement)
            db.session.commit()

        return redirect('/home')

    groups = Measurement.query.with_entities(Measurement.group_name).distinct()
    return render_template('index.html', groups=groups)


@app.route('/group/<group_name>')
def group_details(group_name):
    group = Measurement.query.filter_by(group_name=group_name).first()
    measurements = Measurement.query.filter_by(group_name=group_name).all()

    x = np.arange(len(measurements))
    voltage_data = [measurement.voltage for measurement in measurements]
    temperature_data = [measurement.temperature for measurement in measurements]
    humidity_data = [measurement.humidity for measurement in measurements]

    if not os.path.isfile(f'static/images/{group_name}-{group.group_id}.jpg'):
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6, 10))
        ax1.plot(x, voltage_data, 'r-', label='Voltage')
        ax1.set_xlabel('Measurement Index')
        ax1.set_ylabel('Voltage')
        ax1.set_xlim(0, len(measurements))

        ax2.plot(x, temperature_data, 'g-', label='Temperature')
        ax2.set_xlabel('Measurement Index')
        ax2.set_ylabel('Temperature')
        ax2.set_xlim(0, len(measurements))

        ax3.plot(x, humidity_data, 'b-', label='Humidity')
        ax3.set_xlabel('Measurement Index')
        ax3.set_ylabel('Humidity')
        ax3.set_xlim(0, len(measurements))

        plt.tight_layout()
        plt.savefig(f'static/images/{group_name}-{group.group_id}.jpg')
        plt.close()

    if 'download' in request.args:

        csv_data = [['Index', 'Voltage', 'Temperature', 'Humidity']]
        for i, measurement in enumerate(measurements):
            csv_data.append([i + 1, measurement.voltage, measurement.temperature, measurement.humidity])

        csv_string = ''
        for row in csv_data:
            csv_string += ','.join([str(item) for item in row]) + '\n'

        response = make_response(csv_string)
        response.headers['Content-Disposition'] = f'attachment; filename={group_name}.csv'
        response.headers['Content-type'] = 'text/csv'
        return response

    return render_template('group_details.html', group_id=str(group.group_id), group_name=group.group_name, measurements=measurements)


@app.route('/delete_group/<group_name>', methods=['POST'])
def delete_group(group_name):
    group = Measurement.query.filter_by(group_name=group_name).first()
    Measurement.query.filter_by(group_name=group_name).delete()
    db.session.commit()
    try:
        os.remove(f'static/images/{group_name}-{group.group_id}.jpg')
    except Exception as e:
        print(str(e))

    return redirect('/home')


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        if csv_file and allowed_file(csv_file.filename):

            group_name = request.form['csv_group_name']
            if not group_name:
                group_name = "Uploaded_csv"
                suffix = 0
                unique_group_name = group_name
                while Measurement.query.filter_by(group_name=unique_group_name).first():
                    suffix += 1
                    unique_group_name = f"{group_name} ({suffix})"
                group_name = unique_group_name

            if Measurement.query.filter_by(group_name=group_name).first():
                suffix = 0
                unique_group_name = group_name
                while Measurement.query.filter_by(group_name=unique_group_name).first():
                    suffix += 1
                    unique_group_name = f"{group_name} ({suffix})"
                group_name = unique_group_name

        last_group = Measurement.query.order_by(Measurement.group_id.desc()).first()
        group_id = 1 if last_group is None else last_group.group_id + 1

        filename = secure_filename(csv_file.filename)
        csv_file.save(os.path.join(app.config['TEMP_UPLOAD_FOLDER'], filename))
        file_path = os.path.join(app.config['TEMP_UPLOAD_FOLDER'], filename)

        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                measurement = Measurement(
                    group_id=group_id,
                    group_name=group_name,
                    voltage=float(row[1]),
                    temperature=float(row[2]),
                    humidity=float(row[3])
                )
                db.session.add(measurement)
                db.session.commit()

        os.remove(file_path)
    return redirect('/home')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
