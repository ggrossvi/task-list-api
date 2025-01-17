from flask_sqlalchemy.model import camel_to_snake_case
from tests.test_wave_01 import test_create_task_must_contain_description
from flask import Blueprint
from app import db
from app.models.task import Task
from app.models.goal import Goal
from flask import request, Blueprint, make_response, jsonify
from datetime import datetime
import requests


def order_by_title(task_response):
    return task_response["title"]
    
goal_list_bp = Blueprint("goal_list", __name__, url_prefix = '/goals')

@goal_list_bp.route('', methods = ['GET','POST'])
def handle_goals():
    if request.method == 'GET':
        goals = Goal.query.all()
        goal_response = []
        for goal in goals:
            goal_response.append(goal.serialize())
        return jsonify(goal_response)
    
    elif request.method == 'POST':
        request_body = request.get_json()
        if "title" in request_body:
            new_goal = Goal(
                title = request_body['title']
            )
            db.session.add(new_goal)
            db.session.commit()
            return{
                'goal':
                    new_goal.serialize()
            },201
        else:
            return({
                "details": f'Invalid data'
        },400)
 
@goal_list_bp.route('/<goal_id>', methods = ['GET','PUT', 'DELETE'])  
def handle_goal(goal_id):
    goal = Goal.query.get(goal_id)
    if not goal:
        return "", 404

    if request.method == 'GET':
        #check expected output in test
        return({
            'goal':
                goal.serialize()
            
        })
    elif request.method == 'PUT':
        request_body = request.get_json()
        if 'title' in request_body:
            goal.title = request_body['title']
        db.session.commit()
        return({
            'goal': goal.serialize()
        },200)
    
    elif request.method =='DELETE':
        db.session.delete(goal)
        db.session.commit()
        return({
            "details": f'Goal {goal_id} "{goal.title}" successfully deleted'
        },200)

@goal_list_bp.route('/<goal_id>/tasks', methods = ['GET'])  
def get_tasks_for_goal(goal_id):
    goal = Goal.query.get(goal_id)
    if not goal:
        return "", 404
    
    tasks = goal.tasks
    json_tasks = []
    for task in tasks:
        serializeds_task = task.serialize() # dict
        serializeds_task['goal_id'] = int(goal_id)
        json_tasks.append(serializeds_task)


    return {
        "id": goal.goal_id,
        "title": goal.title,
        "tasks": json_tasks
    }, 200
            
@goal_list_bp.route('/<goal_id>/tasks', methods = ['POST'])  
def add_task_to_goal(goal_id):
    goal = Goal.query.get(goal_id)
    tasks = request.json
    tasks = tasks["task_ids"]  
    if not goal:
         return "", 404
    # task = db.session.query(Task.id)
    query = db.session.query(Task).filter(Task.task_id.in_(tasks))

    results = query.all()
    for task in results:
        task.goal_id = goal.goal_id
        db.session.commit()

    return{
        'id': goal.goal_id,
        'task_ids': tasks   
    },200
        




task_list_bp = Blueprint("task_list", __name__, url_prefix='/tasks')
@task_list_bp.route('', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'GET':
        #return full list of tasks
        
        # allows access to keys - sort
        arg = request.args # better name
        if "sort" in arg:
            if arg['sort'] == "asc":
                tasks = Task.query.order_by(Task.title.asc())
            elif arg['sort'] == "desc":
                tasks = Task.query.order_by(Task.title.desc())
        else:
            tasks = Task.query.all()
        task_response = []
        for task in tasks:
            task_response.append(task.serialize())
                
        return jsonify(task_response)

    elif request.method == 'POST':
        request_body = request.get_json()
        if "title" not in request_body:
            return {
                "details": "Invalid data"
            }, 400
        elif "description" not in request_body:
            return {
                "details": "Invalid data"
            }, 400
        elif "completed_at" not in request_body:
            return {
                "details": "Invalid data"
            }, 400
        stringify_format = "%a, %d %b %Y %H:%M:%S %Z"
        if request_body["completed_at"]:

            new_task = Task(
                title = request_body['title'],
                description = request_body['description'], 
                completed_at = datetime.strptime(request_body["completed_at"], stringify_format)
            )
        else:
             new_task = Task(
                title = request_body['title'],
                description = request_body['description'], 
            )
        db.session.add(new_task)
        db.session.commit()
        return{
            'task':{
                'id': new_task.task_id,
                'title': new_task.title,
                'description': new_task.description,
                'is_complete': new_task.completed_at != None
            }      
        },201


@task_list_bp.route('/<task_id>', methods=['GET','PUT', 'DELETE'])
def handle_task(task_id):  # same name as parameter route
    task = Task.query.get(task_id)
    if not task:
        return "", 404

    if request.method == 'GET':
        return({
            'task': task.serialize()
        })
    elif request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return({
            "details": f'Task {task_id} "{task.title}" successfully deleted' 
        },200)
        

    elif request.method =='PUT':
        request_body = request.get_json()
        if 'title' in request_body:
            task.title = request_body['title']
        if 'description' in request_body:
            task.description = request_body['description']
        if 'completed_at' in request_body:
            task.completed = request_body['completed_at']
        if 'goal_id' in request_body:
            task.goal_id= request_body['goal_id']
        db.session.commit()
        return({
            'task': task.serialize()
        },200)

@task_list_bp.route('/<task_id>/mark_complete',methods = ['PATCH'])
def mark_complete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return "Task not found", 404
    task.completed_at = datetime.utcnow()
    task.notify_slack()
    db.session.commit()
    return{
        'task':{
            'id': task.task_id,
            'title': task.title,
            'description': task.description,
            'is_complete': task.completed_at != None
        }      
    },200
@task_list_bp.route('/<task_id>/mark_incomplete',methods = ['PATCH'])
def mark_incomplete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return "Task Not Found", 404
    task.completed_at = None
    db.session.commit()
    return{
        'task':{
            'id': task.task_id,
            'title': task.title,
            'description': task.description,
            'is_complete': task.completed_at != None
        }      
    },200


    

        
        

    
    
    











        

    



