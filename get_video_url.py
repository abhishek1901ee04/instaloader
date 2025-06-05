import instaloader
import logging
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

# Login with credentials from env
L.login('abhitrivediair1@gmail.com', 'abhi@123')

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger()
@app.route('/get_post_details', methods=['GET'])
def get_video_url():
    try:
        shortcode = request.args.get('shortcode')
        media_id = request.args.get('media_id')

        logger.debug(f"Received request with shortcode={shortcode}, media_id={media_id}")

        if not shortcode and not media_id:
            logger.warning("Missing shortcode or media_id parameter in request.")
            return jsonify({'error': 'Missing shortcode or media_id parameter'}), 400

        if shortcode:
            logger.info(f"Fetching post using shortcode: {shortcode}")
            post = instaloader.Post.from_shortcode(L.context, shortcode)
        else:
            logger.info(f"Fetching post using media_id: {media_id}")
            post = instaloader.Post.from_mediaid(L.context, int(media_id))
        
        post_data = post._asdict()
        owner = post_data.get('owner', {})
        profile_pic_url = owner.get('profile_pic_url')

        # 🔥 PRINT THESE IN LOGS
        logger.debug(f"Post Data (partial): {{'shortcode': {post_data.get('shortcode')}, 'typename': {post_data.get('__typename')}}}")
        logger.debug(f"Owner Data: {owner}")
        logger.debug(f"Owner Profile Pic URL: {profile_pic_url}")

        logger.debug(f"Post fetched successfully: shortcode={post.shortcode}, is_video={post.is_video}")

        data = {
            "shortcode": post.shortcode,
            "is_video": post.is_video,
            "video_url": post.video_url if post.is_video else None,
            "image_url": post.url if not post.is_video else None,
            "thumbnail_url": post.url,
            "caption": post.caption,
            "hashtags": post.caption_hashtags,
            "mentions": post.caption_mentions,
            "timestamp": post.date_utc.isoformat() + "Z",
            "likes": post.likes,
            "comments": post.comments,
            "owner_username": post.owner_username,
            "owner_id": post.owner_id,
            "owner_profile_pic_url": profile_pic_url,
            "location": post.location.name if post.location else None,
            "typename": post.typename,
            "media_id": post.mediaid,
            "accessibility_caption": post.accessibility_caption,
            "carousel_media": []
        }

        if post.typename == "GraphSidecar":
            logger.info("Post is a carousel. Extracting sidecar media.")
            for sidecar_node in post.get_sidecar_nodes():
                data["carousel_media"].append({
                    "is_video": sidecar_node.is_video,
                    "url": sidecar_node.video_url if sidecar_node.is_video else sidecar_node.display_url
                })

        logger.info(f"Post details extraction successful for shortcode={post.shortcode}")

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        logger.exception("An error occurred while fetching post details.")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
