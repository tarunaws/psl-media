"""
Dynamic Ad Insertion - Ad Decision Server (ADS)
Provides personalized ad selection based on user profiles
"""

import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify
from flask_cors import CORS

from shared.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

load_environment()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"
DEMO_VIDEO_DIR = FRONTEND_PUBLIC_DIR / "demo_video"
DEMO_THUMB_DIR = DEMO_VIDEO_DIR / "thumbnails"
DEFAULT_SAMPLE_VIDEO = DEMO_VIDEO_DIR / "DynamicAdInsertion.mp4"
DEFAULT_SAMPLE_THUMB = DEMO_THUMB_DIR / "DynamicAdInsertion.jpg"

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION')
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting dynamic ad insertion service")

DEFAULT_MEDIA_BUCKET = os.getenv('MEDIA_S3_BUCKET')
S3_BUCKET = os.getenv('DAI_S3_BUCKET', DEFAULT_MEDIA_BUCKET)

if not S3_BUCKET:
    raise RuntimeError("Set DAI_S3_BUCKET or MEDIA_S3_BUCKET before starting dynamic ad insertion service")

s3_client = boto3.client('s3', region_name=AWS_REGION)

# Mock User Profiles Database
USER_PROFILES = {
    "tech_enthusiast": {
        "id": "tech_enthusiast",
        "name": "Tech Enthusiast",
        "demographics": {
            "age": "25-34",
            "gender": "All",
            "location": "Urban"
        },
        "interests": ["Technology", "Gaming", "Innovation", "AI"],
        "viewing_history": ["Tech Reviews", "Startup Stories", "Gaming Content"]
    },
    "sports_fan": {
        "id": "sports_fan",
        "name": "Sports Fan",
        "demographics": {
            "age": "18-45",
            "gender": "All",
            "location": "All"
        },
        "interests": ["Sports", "Fitness", "Athletics", "Competition"],
        "viewing_history": ["Live Sports", "Highlights", "Sports News"]
    },
    "movie_lover": {
        "id": "movie_lover",
        "name": "Movie Lover",
        "demographics": {
            "age": "22-55",
            "gender": "All",
            "location": "All"
        },
        "interests": ["Movies", "Entertainment", "Streaming", "Cinema"],
        "viewing_history": ["Feature Films", "Documentaries", "Movie Reviews"]
    },
    "family_viewer": {
        "id": "family_viewer",
        "name": "Family Viewer",
        "demographics": {
            "age": "30-50",
            "gender": "All",
            "location": "Suburban"
        },
        "interests": ["Family", "Education", "Kids Content", "Home"],
        "viewing_history": ["Family Shows", "Educational Content", "Kids Programs"]
    },
    "fitness_enthusiast": {
        "id": "fitness_enthusiast",
        "name": "Fitness Enthusiast",
        "demographics": {
            "age": "22-40",
            "gender": "All",
            "location": "Urban"
        },
        "interests": ["Fitness", "Health", "Wellness", "Nutrition", "Yoga"],
        "viewing_history": ["Workout Videos", "Fitness Challenges", "Health Documentaries"]
    },
    "gamer": {
        "id": "gamer",
        "name": "Gamer",
        "demographics": {
            "age": "16-35",
            "gender": "All",
            "location": "All"
        },
        "interests": ["Gaming", "Esports", "Technology", "Streaming", "Virtual Reality"],
        "viewing_history": ["Game Streams", "Esports Tournaments", "Gaming Reviews"]
    },
    "foodie": {
        "id": "foodie",
        "name": "Foodie",
        "demographics": {
            "age": "25-45",
            "gender": "All",
            "location": "Urban"
        },
        "interests": ["Cooking", "Food", "Restaurants", "Culinary Arts", "Wine"],
        "viewing_history": ["Cooking Shows", "Food Reviews", "Recipe Videos"]
    },
    "traveler": {
        "id": "traveler",
        "name": "Traveler",
        "demographics": {
            "age": "25-55",
            "gender": "All",
            "location": "All"
        },
        "interests": ["Travel", "Adventure", "Culture", "Photography", "Nature"],
        "viewing_history": ["Travel Vlogs", "Destination Guides", "Adventure Documentaries"]
    },
    "eco_conscious": {
        "id": "eco_conscious",
        "name": "Eco-Conscious Consumer",
        "demographics": {
            "age": "25-45",
            "gender": "All",
            "location": "Urban"
        },
        "interests": ["Sustainability", "Environment", "Green Living", "Renewable Energy", "Organic"],
        "viewing_history": ["Environmental Documentaries", "Sustainable Living", "Climate Content"]
    },
    "luxury_shopper": {
        "id": "luxury_shopper",
        "name": "Luxury Shopper",
        "demographics": {
            "age": "30-60",
            "gender": "All",
            "location": "Urban"
        },
        "interests": ["Luxury", "Fashion", "Premium Brands", "Travel", "Fine Dining"],
        "viewing_history": ["Fashion Shows", "Luxury Reviews", "High-End Travel Content"]
    }
}

# Mock Ad Inventory Database
AD_INVENTORY = {
    "tech_gadget_ad": {
        "id": "tech_gadget_ad",
        "name": "Latest Smartphone Launch",
        "duration": 10,
        "category": "Technology",
        "targeting": {
            "interests": ["Technology", "Gaming", "Innovation"],
            "age_range": "18-45"
        },
        "generation_id": "864f4e14-dab4-4335-a285-bb45e6bd369a",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "sports_drink_ad": {
        "id": "sports_drink_ad",
        "name": "Energy Sports Drink",
        "duration": 10,
        "category": "Sports & Fitness",
        "targeting": {
            "interests": ["Sports", "Fitness", "Athletics"],
            "age_range": "18-45"
        },
        "generation_id": "2dcfe1d1-0634-49e3-b3b3-e9f1eaf7dcbe",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "streaming_service_ad": {
        "id": "streaming_service_ad",
        "name": "Premium Streaming Service",
        "duration": 10,
        "category": "Entertainment",
        "targeting": {
            "interests": ["Movies", "Entertainment", "Streaming"],
            "age_range": "18-55"
        },
        "generation_id": "c144f25c-46d6-4f2a-a7fb-5d84c704d838",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "family_vacation_ad": {
        "id": "family_vacation_ad",
        "name": "Family Vacation Package",
        "duration": 10,
        "category": "Travel & Family",
        "targeting": {
            "interests": ["Family", "Travel", "Home"],
            "age_range": "30-55"
        },
        "generation_id": "a3cbdc6d-3908-47f5-96c2-53e258ea949e",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "fitness_equipment_ad": {
        "id": "fitness_equipment_ad",
        "name": "Premium Fitness Equipment",
        "duration": 10,
        "category": "Fitness",
        "targeting": {
            "interests": ["Fitness", "Health", "Wellness"],
            "age_range": "22-45"
        },
        "generation_id": "cfaf9984-4e94-40b9-9235-785f3cde6cd7",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "gaming_console_ad": {
        "id": "gaming_console_ad",
        "name": "Next-Gen Gaming Console",
        "duration": 10,
        "category": "Gaming",
        "targeting": {
            "interests": ["Gaming", "Esports", "Technology"],
            "age_range": "16-40"
        },
        "generation_id": "586d4158-b513-40e5-bfdf-90f65e86772e",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "gourmet_food_ad": {
        "id": "gourmet_food_ad",
        "name": "Gourmet Food Delivery",
        "duration": 10,
        "category": "Food & Dining",
        "targeting": {
            "interests": ["Cooking", "Food", "Restaurants"],
            "age_range": "25-50"
        },
        "generation_id": "xzghmvj70pqk",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "travel_booking_ad": {
        "id": "travel_booking_ad",
        "name": "Adventure Travel Booking",
        "duration": 10,
        "category": "Travel",
        "targeting": {
            "interests": ["Travel", "Adventure", "Culture"],
            "age_range": "25-60"
        },
        "generation_id": "44801165-cca2-4360-89ff-2b81e9bd8e12",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "eco_products_ad": {
        "id": "eco_products_ad",
        "name": "Sustainable Eco Products",
        "duration": 10,
        "category": "Sustainability",
        "targeting": {
            "interests": ["Sustainability", "Environment", "Green Living"],
            "age_range": "25-50"
        },
        "generation_id": "c5490916-79cc-4ae2-92ed-dad79e06112f",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "luxury_watch_ad": {
        "id": "luxury_watch_ad",
        "name": "Luxury Watch Collection",
        "duration": 10,
        "category": "Luxury",
        "targeting": {
            "interests": ["Luxury", "Fashion", "Premium Brands"],
            "age_range": "30-65"
        },
        "generation_id": "88fca849-e73e-46f0-9ffb-8509aac9a84a",
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    },
    "default_ad": {
        "id": "default_ad",
        "name": "General Brand Advertisement",
        "duration": 10,
        "category": "General",
        "targeting": {
            "interests": [],
            "age_range": "All"
        },
        "video_url": None,
        "hls_url": None,
        "thumbnail": None
    }

}


def _ensure_sample_path(env_key: str, default_path: Path) -> Path:
    candidate = os.environ.get(env_key)
    if candidate:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            return candidate_path
        app.logger.warning("%s=%s not found; using default sample asset", env_key, candidate)
    return default_path


SAMPLE_AD_VIDEO = _ensure_sample_path("DAI_SAMPLE_VIDEO_PATH", DEFAULT_SAMPLE_VIDEO)
SAMPLE_AD_THUMB = _ensure_sample_path("DAI_SAMPLE_THUMB_PATH", DEFAULT_SAMPLE_THUMB)


def _generate_presigned_url(key: Optional[str], expires: int = 3600) -> Optional[str]:
    if not key:
        return None
    try:
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': key},
            ExpiresIn=expires
        )
    except ClientError as exc:
        app.logger.error(f"Failed to presign {key}: {exc}")
        return None


def _object_exists(key: str) -> bool:
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response["Error"].get("Code", "")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def _upload_asset_if_missing(key: str, path: Path, content_type: str) -> None:
    if not path.exists():
        app.logger.warning("Sample asset missing on disk: %s", path)
        return
    if _object_exists(key):
        return
    app.logger.info("Uploading sample asset %s to s3://%s/%s", path.name, S3_BUCKET, key)
    s3_client.upload_file(str(path), S3_BUCKET, key, ExtraArgs={"ContentType": content_type})


def _bootstrap_demo_media() -> None:
    media_plan = []
    for ad_id in AD_INVENTORY.keys():
        prefix = f"ads/{ad_id}"
        media_plan.append((f"{prefix}/creative.mp4", SAMPLE_AD_VIDEO, "video/mp4"))
        media_plan.append((f"{prefix}/thumbnail.jpg", SAMPLE_AD_THUMB, "image/jpeg"))

    for key, path, content_type in media_plan:
        try:
            _upload_asset_if_missing(key, path, content_type)
        except ClientError as exc:
            app.logger.error("Failed to sync demo media %s: %s", key, exc)


_bootstrap_demo_media()


def _attach_media_links(ad_payload: dict) -> dict:
    enriched = ad_payload.copy()
    ad_id = enriched.get('id')
    if not ad_id:
        return enriched

    # Derive asset keys per ad
    video_key = f"ads/{ad_id}/creative.mp4"
    thumb_key = f"ads/{ad_id}/thumbnail.jpg"

    video_url = _generate_presigned_url(video_key)
    thumb_url = _generate_presigned_url(thumb_key)

    if video_url:
        enriched['video_url'] = video_url
        # Use MP4 fallback for HLS demos if dedicated playlist missing
        enriched['hls_url'] = enriched.get('hls_url') or video_url
    if thumb_url:
        enriched['thumbnail'] = thumb_url

    return enriched


# Ad Request Logs (in-memory)
AD_REQUEST_LOGS = []


def select_ad_for_profile(profile_id: str) -> dict:
    """
    Select the best ad based on user profile.
    Returns ad metadata with targeting match score.
    """
    profile = USER_PROFILES.get(profile_id)
    if not profile:
        app.logger.warning(f"Unknown profile: {profile_id}, using default ad")
        return AD_INVENTORY["default_ad"]
    
    # Calculate match scores for each ad
    best_ad = None
    best_score = 0
    
    for ad_id, ad in AD_INVENTORY.items():
        if ad_id == "default_ad":
            continue
        
        score = 0
        # Check interest matches
        for interest in ad["targeting"]["interests"]:
            if interest in profile["interests"]:
                score += 10
        
        # Basic demographic matching (simplified)
        if ad["targeting"]["age_range"] != "All":
            score += 5
        
        if score > best_score:
            best_score = score
            best_ad = ad
    
    # If no good match, use default
    if best_score < 5:
        app.logger.info(f"No strong match for {profile_id}, using default ad")
        return AD_INVENTORY["default_ad"]
    
    app.logger.info(f"Selected {best_ad['name']} for {profile['name']} (score: {best_score})")
    return best_ad


@app.route("/health", methods=["GET"])
def health_check() -> Any:
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "dynamic-ad-insertion",
        "region": AWS_REGION,
        "s3_bucket": S3_BUCKET
    }), 200


@app.route("/ads", methods=["GET"])
def get_ad() -> Any:
    """
    Ad Decision Server endpoint.
    Accepts user profile and returns targeted ad.
    
    Query params:
    - user_id or profile_id: User profile identifier
    - session_id: Optional session tracking
    """
    try:
        profile_id = request.args.get('user_id') or request.args.get('profile_id', 'default')
        session_id = request.args.get('session_id', str(uuid.uuid4()))
        
        app.logger.info(f"Ad request - Profile: {profile_id}, Session: {session_id}")
        
        # Select appropriate ad
        selected_ad = select_ad_for_profile(profile_id)
        enriched_ad = _attach_media_links(selected_ad)
        
        # Get profile info
        profile = USER_PROFILES.get(profile_id, {
            "id": "unknown",
            "name": "Unknown User",
            "interests": []
        })
        
        # Log the request
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "profile_id": profile_id,
            "profile_name": profile.get("name", "Unknown"),
            "ad_id": selected_ad["id"],
            "ad_name": selected_ad["name"],
            "ad_category": selected_ad["category"],
            "duration": selected_ad["duration"]
        }
        AD_REQUEST_LOGS.append(log_entry)
        
        # Keep only last 100 logs
        if len(AD_REQUEST_LOGS) > 100:
            AD_REQUEST_LOGS.pop(0)
        
        # Return ad response
        response = {
            "ad_id": enriched_ad.get("id", selected_ad["id"]),
            "ad_name": enriched_ad.get("name", selected_ad["name"]),
            "duration": enriched_ad.get("duration", selected_ad["duration"]),
            "category": enriched_ad.get("category", selected_ad["category"]),
            "video_url": enriched_ad.get("video_url", selected_ad.get("video_url")),
            "hls_url": enriched_ad.get("hls_url", selected_ad.get("hls_url")),
            "thumbnail": enriched_ad.get("thumbnail", selected_ad.get("thumbnail")),
            "targeting_reason": f"Matched interests: {', '.join(profile.get('interests', [])[:3])}",
            "session_id": session_id
        }
        
        app.logger.info(f"Serving ad: {selected_ad['name']} to {profile.get('name')}")
        
        return jsonify(response), 200
        
    except Exception as e:
        app.logger.error(f"Error in ad decision: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/profiles", methods=["GET"])
def get_profiles() -> Any:
    """Get all available user profiles."""
    return jsonify({
        "profiles": list(USER_PROFILES.values())
    }), 200


@app.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: str) -> Any:
    """Get specific user profile details."""
    profile = USER_PROFILES.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile), 200


@app.route("/ads/inventory", methods=["GET"])
def get_ad_inventory() -> Any:
    """Get all available ads in inventory."""
    return jsonify({
        "ads": list(AD_INVENTORY.values()),
        "total": len(AD_INVENTORY)
    }), 200


@app.route("/logs", methods=["GET"])
def get_logs() -> Any:
    """Get ad request logs."""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        "logs": AD_REQUEST_LOGS[-limit:],
        "total": len(AD_REQUEST_LOGS)
    }), 200


@app.route("/logs/clear", methods=["POST"])
def clear_logs() -> Any:
    """Clear all ad request logs."""
    global AD_REQUEST_LOGS
    AD_REQUEST_LOGS = []
    return jsonify({"message": "Logs cleared"}), 200


@app.route("/stats", methods=["GET"])
def get_stats() -> Any:
    """Get ad serving statistics."""
    # Calculate stats from logs
    stats = {
        "total_requests": len(AD_REQUEST_LOGS),
        "unique_sessions": len(set(log["session_id"] for log in AD_REQUEST_LOGS)),
        "ads_by_category": {},
        "ads_by_profile": {}
    }
    
    for log in AD_REQUEST_LOGS:
        # Count by category
        category = log["ad_category"]
        stats["ads_by_category"][category] = stats["ads_by_category"].get(category, 0) + 1
        
        # Count by profile
        profile = log["profile_name"]
        stats["ads_by_profile"][profile] = stats["ads_by_profile"].get(profile, 0) + 1
    
    return jsonify(stats), 200


if __name__ == "__main__":
    app.logger.info("Starting Dynamic Ad Insertion Service...")
    app.logger.info(f"AWS Region: {AWS_REGION}")
    app.logger.info(f"S3 Bucket: {S3_BUCKET}")
    
    # Start Flask app
    app.run(host="0.0.0.0", port=5010, debug=False)
