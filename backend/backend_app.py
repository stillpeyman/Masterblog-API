from flask import Flask, jsonify, request, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

POSTS = [
    {"id": 1, "title": "First post", "content": "This is the first post."},
    {"id": 2, "title": "Second post", "content": "This is the second post."},
]


def validate_post_data(data):
    if "title" not in data or "content" not in data:
        return False
    return True


def find_post_by_id(post_id):
    """
    Find the post with the id <post_id>.
    If there is no post with this id, return None.
    """
    post = next((post for post in POSTS if post['id'] == post_id), None)
    return post


@app.route('/api/posts', methods=['GET', 'POST'])
def handle_posts():
    if request.method == 'POST':
        # Get the new post data from the client
        new_post = request.get_json()
        if not validate_post_data(new_post):
            return jsonify({"error": "Invalid post data. Must include a title and content"}), 400
        
        # Generate a new ID for the post
        new_id = max(post['id'] for post in POSTS) + 1
        new_post['id'] = new_id
        
        POSTS.append(new_post)
        return jsonify(new_post), 201

    # GET request to return all posts
    return jsonify(POSTS)


@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    post = find_post_by_id(id)

    if post is None:
        abort(404, description="Post not found")

    # Remove the post from the list
    POSTS.remove(post)

    # Return deleted post
    return jsonify(post)


@app.route('/api/posts/<int:id>', methods=['PUT'])
def update_post(id):
    post = find_post_by_id(id)

    if post is None:
        abort(404, description="Post not found")

    # If the client didn't send JSON data, return error message (status code: 415)
    if not request.is_json:
        abort(415, description="Request must be JSON")

    new_data = request.get_json()

    # Update 'title' and 'content' fields if present in new_data
    post.update({k: v for k, v in new_data.items() if k in ('title', 'content')})


    # Return the updated post
    return jsonify(post)


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not Found", "message": error.description}), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({"error": "Method Not Allowed"}), 405


@app.errorhandler(415)
def unsupported_media_type(error):
    return jsonify({"error": "Request must be JSON", "message": error.description}), 415


@app.errorhandler(Exception)
def server_error(error):
    # Catch-all fallback: automatic for unhandled errors
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
