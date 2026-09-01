from flask import Blueprint, request, jsonify
from app.services.task_comment_service import add_comment, get_task_comments, delete_comment, CommentError

task_comment_bp = Blueprint('task_comments', __name__)

@task_comment_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
def create_comment(task_id):
    data = request.get_json()
    user_id = data.get('user_id')
    content = data.get('content')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    try:
        comment = add_comment(user_id, task_id, content)
        return jsonify(comment.to_dict()), 201
    except CommentError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@task_comment_bp.route('/tasks/<int:task_id>/comments', methods=['GET'])
def list_comments(task_id):
    user_id = request.args.get('user_id', type=int)
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    try:
        comments = get_task_comments(user_id, task_id)
        return jsonify([c.to_dict() for c in comments]), 200
    except CommentError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@task_comment_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
def remove_comment(comment_id):
    user_id = request.args.get('user_id', type=int)
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    try:
        delete_comment(user_id, comment_id)
        return jsonify({'message': 'Comment deleted successfully'}), 200
    except CommentError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500