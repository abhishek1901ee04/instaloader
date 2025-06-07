import instaloader
import logging
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv  # 👈 IMPORT THIS
import pprint  # For pretty-printing the owner info

# 👇 Load the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # This will allow cross-origin requests

# Initialize Instaloader
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

print(f"🔑 Username from env: {INSTAGRAM_USERNAME}")
print(f"🔑 Password from env: {INSTAGRAM_PASSWORD}")

# Continue with login
L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
# Login with credentials!
L.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD'))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger()

@app.route('/get_post_details', methods=['GET'])
def get_post_details():
    try:
        shortcode = request.args.get('shortcode')
        media_id = request.args.get('media_id')

        if not shortcode and not media_id:
            logger.warning("Missing shortcode or media_id parameter in request.")
            return jsonify({
                'success': False,
                'error_code': 1000,
                'message': 'Missing shortcode or media_id parameter.'
            }), 400

        # Fetch post
        try:
            if shortcode:
                logger.info(f"Fetching post using shortcode: {shortcode}")
                post = instaloader.Post.from_shortcode(L.context, shortcode)
            else:
                logger.info(f"Fetching post using media_id: {media_id}")
                post = instaloader.Post.from_mediaid(L.context, int(media_id))
        except instaloader.exceptions.QueryReturnedNotFoundException:
            logger.error(f"Post not found for shortcode/media_id: {shortcode or media_id}")
            return jsonify({
                'success': False,
                'error_code': 1001,
                'message': 'Post not found. It may have been deleted or is private.'
            }), 404
        except instaloader.exceptions.ConnectionException as e:
            if "429" in str(e):
                logger.error("Rate limit hit. Please try again later.")
                return jsonify({
                    'success': False,
                    'error_code': 1002,
                    'message': 'Rate limit hit. Please wait before retrying.'
                }), 429
            else:
                logger.error(f"Connection error: {e}")
                return jsonify({
                    'success': False,
                    'error_code': 1003,
                    'message': 'Connection error. Please try again later.'
                }), 503
        except Exception as e:
            logger.error(f"Unexpected error while fetching post: {e}")
            return jsonify({
                'success': False,
                'error_code': 1004,
                'message': 'Unexpected error while fetching post.'
            }), 500

        logger.debug(f"Post fetched successfully: shortcode={post.shortcode}, is_video={post.is_video}")
        # Get owner info properly
        owner = post.owner_profile

        # New owner info
        owner_info = {
            "id": owner.userid,
            "username": owner.username,
            "full_name": owner.full_name,
            "profile_pic_url": owner.profile_pic_url,
            "biography": owner.biography,
            "external_url": owner.external_url,
            "is_private": owner.is_private,
            "is_verified": owner.is_verified,
            "followers": owner.followers,
            "following": owner.followees,
            "media_count": owner.mediacount,
        }
        # Assemble data
        data = {
            "shortcode": post.shortcode,
            "media_id": post.mediaid,
            "is_video": post.is_video,
            "video_url": post.video_url if post.is_video else None,
            "image_url": post.url if not post.is_video else None,
            "thumbnail_url": post.url,
            "caption": post.caption,
            "hashtags": post.caption_hashtags,
            "mentions": post.caption_mentions,
            "timestamp": post.date_utc.isoformat() + "Z" if post.date_utc else None,
            "likes": post.likes,
            "comments": post.comments,
            "post_type": post.typename,
            "carousel_media": [],  # Default empty list for carousel media
            "location": None,  # Default null
            "owner_info": owner_info  # <-- 🚨 add this full owner_info dictionar
        }

        partial = False

        # Safe location fetch
        try:
            location = post.location
            if location:
                data["location"] = location.name
        except Exception as e:
            logger.warning(f"Could not fetch location for post {post.shortcode}: {e}")
            partial = True

        # Safe carousel media extraction
        if post.typename == "GraphSidecar":
            logger.info("Post is a carousel. Extracting sidecar media.")
            carousel_media = []
            try:
                for sidecar_node in post.get_sidecar_nodes():
                    carousel_media.append({
                        "is_video": sidecar_node.is_video,
                        "url": sidecar_node.video_url if sidecar_node.is_video else sidecar_node.display_url
                    })
                data["carousel_media"] = carousel_media
            except Exception as e:
                logger.warning(f"Could not fetch carousel media for post {post.shortcode}: {e}")
                partial = True

        # Validate important fields
        required_fields = ["shortcode", "media_id", "thumbnail_url"]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            logger.warning(f"Post {post.shortcode} missing important fields: {missing_fields}")
            return jsonify({
                'success': False,
                'partial': True,
                'error_code': 1005,
                'message': f'Missing important fields: {missing_fields}',
                'data': data
            }), 206  # 206 Partial Content

        logger.info(f"Post details extraction successful for shortcode={post.shortcode}")

        return jsonify({
            "success": True,
            "partial": partial,
            "message": "Post details fetched successfully.",
            "data": data
        }), 200

    except Exception as e:
        logger.exception("An unhandled error occurred while processing the request.")
        return jsonify({
            'success': False,
            'error_code': 1006,
            'message': 'Internal server error. Please contact support.'
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    logger.info("Starting Flask server on port 5000")