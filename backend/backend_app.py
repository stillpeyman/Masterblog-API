from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes


# Swagger UI configuration
SWAGGER_URL = "/api/docs"  # URL for exposing Swagger UI (frontend)
API_URL = "/static/masterblog.json"  # Path to your Swagger JSON spec

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': 'Masterblog API'}
)

app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)


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
            return jsonify({"error": "Invalid post data. Must include a title and content."}), 400
        
        # Generate a new ID for the post
        new_id = max(post['id'] for post in POSTS) + 1
        new_post['id'] = new_id
        
        POSTS.append(new_post)
        return jsonify(new_post), 201

    else:
        sort = request.args.get('sort')
        direction = request.args.get('direction')

        # Validate parameters
        if sort and sort not in ['title', 'content']:
            return jsonify({"error": f"Invalid sort field {sort}. Must be 'title' or 'content'."}), 400
        
        if direction and direction not in ['asc', 'desc']:
            return jsonify({"error": f"Invalid direction: {direction}. Must be 'asc' or 'desc'."}), 400

        # Sort if params are valid
        if sort:
            # True if descending, in sorted() reverse=True sorts in desc order
            reverse = direction == 'desc'
            sorted_posts = sorted(POSTS, key=lambda post: post[sort].lower(), reverse=reverse)
            return sorted_posts

        # No sorting: return original order
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


@app.route('/api/posts/search', methods=['GET'])
def search_post():
     # Handle the GET request with a query parameter
    title = request.args.get('title', '').lower()
    content = request.args.get('content', '').lower()

    if not title and not content:
        # Return empty list if no search criteria
        return jsonify([])
   
    # Check if 'title' = substring of post's title if 'title' provided
    # If 'title' = empty string return False, so no match (same for 'content')
    filtered_posts = [
        post for post in POSTS 
        if (title in post['title'].lower() if title else False)
        or (content in post['content'].lower() if content else False)
    ]

    return jsonify(filtered_posts)


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
