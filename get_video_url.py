import instaloader
import logging
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

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

        logger.debug(f"Received request with shortcode={shortcode}, media_id={media_id}")

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
            "owner_username": post.owner_username,
            "owner_id": post.owner_id,
            "location": None  # Default null
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