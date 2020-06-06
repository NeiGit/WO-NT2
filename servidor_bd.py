# ORM: Object Relational Map
from flask import Flask, request, Response
from flask import json

import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship, backref

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask_cors import CORS


Base = declarative_base()

class ToJson():
    def to_json(self):
        return json.dumps({col.name: getattr(self, col.name) for col in self.__table__.columns })


class Workout(Base, ToJson):
    __tablename__ = 'workout'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    
class Set(Base, ToJson):
    __tablename__ = 'set'
    id = Column(Integer, primary_key=True)
    reps = Column(Integer)
    workout_id = Column(Integer, ForeignKey('workout.id'))
    workout = relationship(
        Workout,
        backref=backref('sets', uselist=True, cascade='delete,all')
    )

class Exercise(Base, ToJson):
    __tablename__ = 'exercise'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    reps = Column(Integer)
    weight = Column(Numeric)
    set_id = Column(Integer, ForeignKey('set.id'))
    parentSet = relationship(
        Set,
        backref=backref('exercises', uselist=True, cascade='delete,all')
    )


engine = create_engine('sqlite:///workouts_db.sqlite')

session = sessionmaker()
session.configure(bind=engine)

app = Flask(__name__) 
CORS(app)

@app.route('/createdb')
def crear_base():
    Base.metadata.create_all(engine)
    return 'Ok'


@app.route('/workout', methods=['POST'])
def create_workout():
    if not 'title' in request.form:
        return Response("Title not specified", status=400)

    title = request.form['title']
    if title == '':
        return Response("{'error_msg':'Empty title'}", status=400, mimetype='application/json')

    workout = Workout()
    workout.title = title

    s = session()
    s.add(workout)
    s.commit()

    return Response(str(workout.id), status=201, mimetype='application/json')

@app.route('/workout/<int:id>')
def get_workout(id):
    s = session()

    # Busco el workout en la base
    workout = s.query(Workout).filter(Workout.id==id).one()

    # Busco las sets asociadas al workout (children)
    sets = s.query(Set).filter(Set.workout_id==workout.id).all()

    # Armo un json con la colección de sets del workout
    setsJson = json.dumps([s.to_json() for s in sets])

    # Armo un dataframe con los datos del workout y le agrego el json de sets
    combinedData = {
        "id" : workout.id,
        "title": workout.title,
        "date": workout.date,
        "sets" : setsJson
    }
    # Devuelvo una respuesta con el dataFrame convertido a json
    return Response(json.dumps(combinedData), status=200, mimetype='application/json')

@app.route('/workoutSets/<int:id>')
def get_workoutSets(id):
    s = session()
    w = s.query(Workout).filter(Workout.id==id).one()
    sets = s.query(Set).filter(Set.workout_id==w.id).all()
    return Response(json.dumps([s.to_json() for s in sets]), status=200, mimetype='application/json')

@app.route('/workout')
def list_workout():
    s = session()
    workouts = s.query(Workout)
    return Response(json.dumps([w.to_json() for w in workouts]), status=200, mimetype='application/json')

@app.route('/workout', methods=['PUT'])
def put_workout():
    id = request.form['id']
    title = request.form['title']
    
    s = session()
    w = s.query(Workout).filter(Workout.id==id).one()
    w.title = title
    s.commit()
    
    return Response(status=204)


@app.route('/set', methods=['POST'])
def create_set():
    if not 'reps' in request.form:
        return Response("Reps not specified", status=400)

    reps = request.form['reps']
    if reps == '':
        return Response("{'error_msg':'Empty reps'}", status=400, mimetype='application/json')

    if not 'workout_id' in request.form:
        return Response("Workout not specified", status=400)

    workout_id = request.form['workout_id']
    if workout_id == '':
        return Response("{'error_msg':'Empty workout_id'}", status=400, mimetype='application/json')

    s = session()
    w = s.query(Workout).filter(Workout.id==workout_id).first()    

    if w is None:
        return Response("{'error_msg':'There is no workout with that id'}", status=400, mimetype='application/json')

    newSet = Set()
    newSet.workout_id = w.id
    newSet.workout = w
    newSet.reps = reps

    w.sets.append(newSet)

    s.merge(w)
    s.add(newSet)
    s.commit()

    return Response(str(newSet.id), status=201, mimetype='application/json')    


@app.route('/exercise', methods=['POST'])
def create_exercise():
    if not 'name' in request.form:
        return Response("Name not specified", status=400)

    name = request.form['name']
    if name == '':
        return Response("{'error_msg':'Empty name'}", status=400, mimetype='application/json')

    if not 'set_id' in request.form:
        return Response("Set not specified", status=400)

    set_id = request.form['set_id']
    if set_id == '':
        return Response("{'error_msg':'Empty set_id'}", status=400, mimetype='application/json')

    s = session()
    existingSet = s.query(Set).filter(Set.id==set_id).first()    

    if existingSet is None:
        return Response("{'error_msg':'There is no set with that id'}", status=400, mimetype='application/json')

    newExercise = Exercise()
    newExercise.name = name
    newExercise.set_id = existingSet.id
    newExercise.set = existingSet
    if 'reps' in request.form:
        newExercise.reps = request.form['reps']
    if 'weight' in request.form:
        newExercise.weight = request.form['weight']
            
    s.add(newExercise)
    s.commit()

    return Response(str(newExercise.id), status=201, mimetype='application/json')    

if __name__ == '__main__':
    app.run(port=5501)
