from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime, timezone
import pytz
import json
import os

app = Flask(__name__)
# This will enable CORS for all routes
CORS(app)  


# Swagger UI configuration
# URL for exposing Swagger UI (frontend)
SWAGGER_URL = "/api/docs"
# Path to Swagger JSON spec  
API_URL = "/static/masterblog.json"  

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': 'Masterblog API'}
)

app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, "data", "posts.json")


def parse_berlin_datetime(date_input):
    """
    Parse date/time input (str or datetime object) 
    and return a timezone-aware datetime in Berlin time.
    """
    # pytz = Python TimeZone (library for handling time zones)
    # <.timezone> function to get timezone object
    berlin = pytz.timezone("Europe/Berlin")

    if isinstance(date_input, datetime):
        # If already timezone-aware (like UTC), convert to Berlin
        # <tzinfo> = timezone info included (aware datetime)
        if date_input.tzinfo:
            # "As timezone" converts datetime into new timezone
            # <.astimezone()> only works on aware datetime
            return date_input.astimezone(berlin)
        # If naive datetime (no tzinfo), localize to Berlin
        return berlin.localize(date_input)
    
    elif isinstance(date_input, str):
        # Parse from string and localize to Berlin
        try:
            dt = datetime.strptime(date_input, "%Y-%m-%d %H:%M:%S")
            return berlin.localize(dt)
        except ValueError:
            raise ValueError("Date string must be in format 'YYYY-MM-DD HH:MM:SS'")
    
    else:
        raise TypeError("date_input must be a datetime object or a string.")


def load_data():
    if not os.path.exists(DATA):
        return []
    
    try:
        with open(DATA, 'r', encoding='utf-8') as handle:
            posts = json.load(handle)
            # Convert 'date' strings back to datetime obj
            for post in posts:
                post['date'] = parse_berlin_datetime(post['date'])
            return posts
    
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {DATA}: {e}")
        return []
    

def save_data(posts):
    try:
        # Convert datetime obj to strings
        posts_to_save = []
        for post in posts:
            post_copy = post.copy()
            post_copy['date'] = post_copy['date'].strftime("%Y-%m-%d %H:%M:%S")
            posts_to_save.append(post_copy)
        
        with open(DATA, 'w', encoding='utf-8') as handle:
            json.dump(posts_to_save, handle, indent=4)
    
    except IOError as e:
        print(f"Error writing {DATA}: {e}")


def validate_post_data(data):
    required_keys = ["title", "content", "author"]
    # For each key in required_keys returns True if that key exists in data
    # all() checks for all keys
    return all(key in data for key in required_keys)


def find_post_by_id(post_id, posts):
    """
    Find the post with the id <post_id> in list of posts.
    If there is no post with this id, return None.
    """
    return next((post for post in posts if post['id'] == post_id), None)


def serialize_post(post):
    """
    Convert a post dictionary with a datetime object in 'date' field
    into a JSON-serializable dict by formatting the datetime as a string.
    """
    return {
        **post,
        "date": post["date"].strftime("%Y-%m-%d %H:%M:%S")
    }


@app.route('/api/posts', methods=['GET', 'POST'])
def handle_posts():
    posts = load_data()

    if request.method == 'POST':
        # Get the new post data from the client
        new_post = request.get_json()
        if not validate_post_data(new_post):
            return jsonify({"error": "Invalid post data. Must include title, content and author."}), 400
        
        # Generate a new ID for the post
        new_id = max((post['id'] for post in posts if posts), default=0) + 1
        new_post['id'] = new_id
        new_post['date'] = parse_berlin_datetime(datetime.now(timezone.utc))
        
        posts.append(new_post)
        save_data(posts)

        return jsonify(serialize_post(new_post)), 201

    else:
        sort = request.args.get('sort')
        direction = request.args.get('direction')

        # Validate parameters
        if sort and sort not in ['title', 'content', 'author', 'date']:
            return jsonify({"error": f"Invalid sort field {sort}. Must be 'title' or 'content'."}), 400
        
        if direction and direction not in ['asc', 'desc']:
            return jsonify({"error": f"Invalid direction: {direction}. Must be 'asc' or 'desc'."}), 400

        # Sort if params are valid
        if sort:
            # True if descending, in sorted() reverse=True sorts in desc order
            reverse = direction == 'desc'
            if sort == 'date':
                sorted_posts = sorted(posts, key=lambda post: post['date'], reverse=reverse)
            else:
                sorted_posts = sorted(posts, key=lambda post: post[sort].lower(), reverse=reverse)
            return jsonify([serialize_post(post) for post in sorted_posts])

        # No sorting: return original order
        return jsonify([serialize_post(post) for post in posts])


@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    posts = load_data()
    post = find_post_by_id(id, posts)

    if post is None:
        abort(404, description="Post not found")

    # Remove the post from the list
    posts.remove(post)
    save_data(posts)

    # Return deleted post
    return jsonify(serialize_post(post))


@app.route('/api/posts/<int:id>', methods=['PUT'])
def update_post(id):
    posts = load_data()
    post = find_post_by_id(id, posts)

    if post is None:
        abort(404, description="Post not found")

    # If the client didn't send JSON data, return error message (status code: 415)
    if not request.is_json:
        abort(415, description="Request must be JSON")

    new_data = request.get_json()

    # If date is in new_data, parse it to datetime
    if 'date' in new_data:
        try:
            new_data['date'] = parse_berlin_datetime(new_data['date'])
        except ValueError:
            return jsonify({"error": "Date must be in format 'YYYY-MM-DD HH:MM:SS'."}), 400

    # Update blog post fields if present in new_data
    post.update({
        k: v 
        for k, v in new_data.items() 
        if k in ('title', 'content', 'author', 'date')
        })
    
    save_data(posts)

    # Return the updated post
    return jsonify(serialize_post(post))


@app.route('/api/posts/search', methods=['GET'])
def search_post():
    posts = load_data()

     # Handle the GET request with a query parameter
    title = request.args.get('title', '').lower()
    content = request.args.get('content', '').lower()
    author = request.args.get('author', '').lower()
    date = request.args.get('date', '')

    # If not at least one search criteria, return empty list
    if not any([title, content, author, date]):
        return jsonify([])
   
    # Check e.g. if 'title' = substring of post's title if 'title' provided
    # If e.g. 'title' = empty string return False, so no match
    filtered_posts = [
        post for post in posts 
        if (title in post['title'].lower() if title else False)
        or (content in post['content'].lower() if content else False)
        or (author in post['author'].lower() if author else False)
        or (date in post["date"].strftime("%Y-%m-%d %H:%M:%S") if date else False)
    ]

    return jsonify([serialize_post(post) for post in filtered_posts])


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




# SIMPLE EXAMPLE HOW DATETIME/PYTZ WORKS:
# from datetime import datetime
# import pytz

# utc = pytz.utc
# eastern = pytz.timezone("US/Eastern")

# # Step 1: Get naive UTC datetime
# naive_utc = datetime.utcnow()
# print(naive_utc.tzinfo)  # None (naive)

# # Step 2: Make it aware (in UTC)
# dt_utc = naive_utc.replace(tzinfo=utc)
# print(dt_utc.tzinfo)  # UTC (aware)

# # Step 3: Convert to another timezone
# dt_est = dt_utc.astimezone(eastern)
# print(dt_est)  # Converted to US/Eastern time

