from flask import Flask, jsonify, request
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


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
