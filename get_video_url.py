import instaloader
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

@app.route('/get_post_details', methods=['GET'])
def get_video_url():
    try:
        # shortcode = request.args.get('shortcode')
        # if not shortcode:
        #     return jsonify({'error': 'Missing shortcode parameter'}), 400
        
        # # Load the post
        # post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        shortcode = request.args.get('shortcode')
        media_id = request.args.get('media_id')

        if not shortcode and not media_id:
            return jsonify({'error': 'Missing shortcode or media_id parameter'}), 400

        if shortcode:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
        else:
            post = instaloader.Post.from_mediaid(L.context, int(media_id))

        # Extract details
        data = {
            "shortcode": post.shortcode,
            "is_video": post.is_video,
            "video_url": post.video_url if post.is_video else None,
            "image_url": post.url if not post.is_video else None,
            "thumbnail_url": post.url,
            "caption": post.caption,
            "hashtags": post.caption_hashtags,
            "mentions": post.caption_mentions,
            "timestamp": post.date_utc.isoformat() + "Z",  # ISO 8601 UTC
            "likes": post.likes,
            "comments": post.comments,
            "owner_username": post.owner_username,
            "owner_id": post.owner_id,
            "location": post.location.name if post.location else None,
            "typename": post.typename,
            "media_id": post.mediaid,
            "accessibility_caption": post.accessibility_caption,
            "carousel_media": []
        }

        # Handle carousel posts
        if post.typename == "GraphSidecar":
            for sidecar_node in post.get_sidecar_nodes():
                data["carousel_media"].append({
                    "is_video": sidecar_node.is_video,
                    "url": sidecar_node.video_url if sidecar_node.is_video else sidecar_node.display_url
                })

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
