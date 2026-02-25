import json
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        data = get_default_data()
        save_tasks(data)
        return data
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tasks(data):
    data['meta']['last_updated'] = datetime.now().astimezone().isoformat()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_default_data():
    now = datetime.now().astimezone().isoformat()
    return {
        "meta": {"owner": "DK", "last_updated": now, "version": 1},
        "projects": [],
        "weekly_log": []
    }


def generate_id(prefix, data):
    max_num = 0
    for project in data.get('projects', []):
        if prefix == 'proj':
            try:
                num = int(project['id'].split('_')[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                pass
        for task in project.get('tasks', []):
            if prefix == 'task':
                try:
                    num = int(task['id'].split('_')[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    pass
    return f"{prefix}_{max_num + 1:03d}"


def get_week_start(date_str=None):
    if date_str:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        d = datetime.now().date()
    return (d - timedelta(days=d.weekday())).isoformat()


def find_task(data, task_id):
    for project in data.get('projects', []):
        for task in project.get('tasks', []):
            if task['id'] == task_id:
                return task, project
    return None, None


# Routes

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    return jsonify(load_tasks())


@app.route('/api/summary')
def get_summary():
    data = load_tasks()
    today = datetime.now().strftime('%Y-%m-%d')
    total = completed = in_progress = pending = cancelled = overdue = 0

    for project in data['projects']:
        for task in project['tasks']:
            total += 1
            s = task['status']
            if s == 'completed':
                completed += 1
            elif s == 'in_progress':
                in_progress += 1
                if task.get('estimated_completion') and task['estimated_completion'] < today:
                    overdue += 1
            elif s == 'pending':
                pending += 1
            elif s == 'cancelled':
                cancelled += 1

    return jsonify({
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'cancelled': cancelled,
        'overdue': overdue,
        'completion_rate': round(completed / total * 100) if total > 0 else 0
    })


@app.route('/api/weekly-report')
def get_weekly_report():
    data = load_tasks()
    week = request.args.get('week', get_week_start())
    today = datetime.now().strftime('%Y-%m-%d')

    report = {
        'week_start': week,
        'completed_tasks': [],
        'in_progress_tasks': [],
        'pending_tasks': [],
        'cancelled_tasks': [],
        'log_entries': []
    }

    for project in data['projects']:
        for task in project['tasks']:
            item = {
                'project_name': project['name'],
                'task_id': task['id'],
                'title': task['title'],
                'description': task['description'],
                'notes': task['notes'],
                'priority': task['priority'],
                'progress': task['progress']
            }
            if task['status'] == 'completed':
                item['completed_at'] = task.get('completed_at')
                report['completed_tasks'].append(item)
            elif task['status'] == 'in_progress':
                item['estimated_completion'] = task.get('estimated_completion')
                item['overdue'] = bool(
                    task.get('estimated_completion') and task['estimated_completion'] < today
                )
                report['in_progress_tasks'].append(item)
            elif task['status'] == 'pending':
                item['estimated_restart'] = task.get('estimated_restart')
                report['pending_tasks'].append(item)
            elif task['status'] == 'cancelled':
                item['cancelled_reason'] = task.get('cancelled_reason')
                report['cancelled_tasks'].append(item)

    for wlog in data.get('weekly_log', []):
        if wlog['week_start'] == week:
            report['log_entries'] = wlog.get('entries', [])
            break

    return jsonify(report)


@app.route('/api/projects', methods=['POST'])
def create_project():
    data = load_tasks()
    body = request.get_json()
    now = datetime.now().astimezone().isoformat()
    new_project = {
        'id': generate_id('proj', data),
        'name': body.get('name', '新專案'),
        'description': body.get('description', ''),
        'color': body.get('color', '#3B82F6'),
        'sort_order': len(data['projects']) + 1,
        'created_at': now,
        'updated_at': now,
        'tasks': []
    }
    data['projects'].append(new_project)
    save_tasks(data)
    return jsonify(new_project), 201


@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    data = load_tasks()
    body = request.get_json()
    for project in data['projects']:
        if project['id'] == project_id:
            for key in ('name', 'description', 'color', 'sort_order'):
                if key in body:
                    project[key] = body[key]
            project['updated_at'] = datetime.now().astimezone().isoformat()
            save_tasks(data)
            return jsonify(project)
    return jsonify({'error': '專案不存在'}), 404


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    data = load_tasks()
    data['projects'] = [p for p in data['projects'] if p['id'] != project_id]
    save_tasks(data)
    return jsonify({'ok': True})


@app.route('/api/tasks/<project_id>', methods=['POST'])
def create_task(project_id):
    data = load_tasks()
    body = request.get_json()
    now = datetime.now().astimezone().isoformat()
    for project in data['projects']:
        if project['id'] == project_id:
            new_task = {
                'id': generate_id('task', data),
                'title': body.get('title', '新任務'),
                'description': body.get('description', ''),
                'notes': body.get('notes', ''),
                'status': body.get('status', 'pending'),
                'priority': body.get('priority', 'medium'),
                'progress': body.get('progress', 0),
                'created_at': now,
                'updated_at': now,
                'completed_at': body.get('completed_at'),
                'estimated_completion': body.get('estimated_completion'),
                'estimated_restart': body.get('estimated_restart'),
                'cancelled_reason': body.get('cancelled_reason'),
                'tags': body.get('tags', [])
            }
            project['tasks'].append(new_task)
            project['updated_at'] = now
            save_tasks(data)
            return jsonify(new_task), 201
    return jsonify({'error': '專案不存在'}), 404


@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = load_tasks()
    body = request.get_json()
    task, project = find_task(data, task_id)
    if not task:
        return jsonify({'error': '任務不存在'}), 404

    for key in ('title', 'description', 'notes', 'status', 'priority',
                'progress', 'completed_at', 'estimated_completion',
                'estimated_restart', 'cancelled_reason', 'tags'):
        if key in body:
            task[key] = body[key]

    now = datetime.now().astimezone().isoformat()
    task['updated_at'] = now
    project['updated_at'] = now
    save_tasks(data)
    return jsonify(task)


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    data = load_tasks()
    for project in data['projects']:
        project['tasks'] = [t for t in project['tasks'] if t['id'] != task_id]
    save_tasks(data)
    return jsonify({'ok': True})


@app.route('/api/weekly-log', methods=['POST'])
def add_log_entry():
    data = load_tasks()
    body = request.get_json()
    now = datetime.now()
    week_start = get_week_start()
    entry = {
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M'),
        'content': body.get('content', ''),
        'task_id': body.get('task_id')
    }

    for wlog in data.get('weekly_log', []):
        if wlog['week_start'] == week_start:
            wlog['entries'].append(entry)
            save_tasks(data)
            return jsonify(entry), 201

    data.setdefault('weekly_log', []).append({
        'week_start': week_start,
        'entries': [entry]
    })
    save_tasks(data)
    return jsonify(entry), 201


if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
