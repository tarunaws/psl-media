#!/usr/bin/env python3
"""AI Based Trailer orchestration service.

This service accepts hero footage, pairs it with a viewer profile, and builds an
AI-based trailer plan. The pipeline can operate in a mock mode (default)
for local demos or use cloud AI services when the appropriate credentials and
environment variables are supplied.

AWS services referenced in the workflow:
- Amazon Rekognition — scene, face, and emotion analysis
- Amazon Personalize — viewer-preference ranking and scene scoring
- AWS Elemental MediaConvert — trailer assembly and packaging
- Amazon S3 / AWS Lambda — media storage and background triggers
- Amazon SageMaker — optional custom scoring models
- Amazon Transcribe / Amazon Translate — captions and localization

The default "mock" pipeline simulates these stages so the frontend can render
results without live AWS calls.
"""

from __future__ import annotations

import json
import math
import mimetypes
import os
import random
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

try:  # Optional boto3 import — only required for live AWS mode
	import boto3
	from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - boto3 is optional for mock mode
	boto3 = None
	BotoCoreError = ClientError = Exception


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
JOBS_DIR = BASE_DIR / "jobs"

for directory in (UPLOAD_DIR, OUTPUT_DIR, JOBS_DIR):
	directory.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "m4v", "avi", "webm"}
MAX_UPLOAD_BYTES = int(os.getenv("PERSONALIZED_TRAILER_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))

PIPELINE_MODE = os.getenv("PERSONALIZED_TRAILER_PIPELINE_MODE", "mock").strip().lower()
AWS_REGION = os.getenv("AI_BASED_TRAILER_REGION") or os.getenv("PERSONALIZED_TRAILER_REGION") or os.getenv("AWS_REGION")
# If the pipeline is running in mock mode we don't require cloud region settings.
if PIPELINE_MODE != "mock" and not AWS_REGION:
	raise RuntimeError(
		"Set AI_BASED_TRAILER_REGION or PERSONALIZED_TRAILER_REGION or AWS_REGION before starting the Personalized Trailer service when not in mock mode"
	)
S3_BUCKET = os.getenv("AI_BASED_TRAILER_S3_BUCKET") or os.getenv("PERSONALIZED_TRAILER_S3_BUCKET") or os.getenv("CONTENT_MODERATION_BUCKET")
S3_PREFIX = (os.getenv("AI_BASED_TRAILER_PREFIX") or os.getenv("PERSONALIZED_TRAILER_PREFIX") or "personalized-trailers").strip("/")

DEFAULT_LANGUAGES = ["en", "es", "fr", "hi", "de", "ja"]
DEFAULT_DURATIONS = [15, 30, 45, 60, 90]
DEFAULT_OUTPUT_FORMATS = ["mp4", "mov"]


PROFILE_PRESETS: List[Dict[str, Any]] = [
	{
		"id": "action_enthusiast",
		"label": "Action Enthusiast",
		"summary": "High-intensity pacing, heroic set pieces, and adrenaline-fueled score cues.",
		"preferences": {
			"dominantEmotions": ["Excited", "Tense"],
			"foregroundTags": ["Explosion", "Chase", "Hero"],
			"audioStyle": "orchestral-hybrid",
		},
	},
	{
		"id": "family_viewer",
		"label": "Family Viewer",
		"summary": "Humor, warmth, ensemble moments, and inclusive storytelling arcs.",
		"preferences": {
			"dominantEmotions": ["Joy", "Calm"],
			"foregroundTags": ["Family", "Friendship", "Heartwarming"],
			"audioStyle": "uplifting-pop",
		},
	},
	{
		"id": "thriller_buff",
		"label": "Thriller Buff",
		"summary": "Mystery hooks, dramatic reveals, and escalating tension beats.",
		"preferences": {
			"dominantEmotions": ["Fear", "Surprise"],
			"foregroundTags": ["Mystery", "Plot Twist", "Shadow"],
			"audioStyle": "pulse-synth",
		},
	},
	{
		"id": "romance_devotee",
		"label": "Romance Devotee",
		"summary": "Intimate character moments, sweeping vistas, and emotive dialogue.",
		"preferences": {
			"dominantEmotions": ["Love", "Hope"],
			"foregroundTags": ["Couple", "Sunset", "Monologue"],
			"audioStyle": "piano-ambient",
		},
	},
]


def _create_app() -> Flask:
	app = Flask(__name__)
	app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

	cors_origins = _resolve_cors_origins()
	if cors_origins == "*":
		CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
	else:
		CORS(app, resources={r"/*": {"origins": cors_origins}}, supports_credentials=False)

	# Attach helpers to app context for easier access inside routes
	app.config.update(
		PIPELINE_MODE=PIPELINE_MODE,
		AWS_REGION=AWS_REGION,
		S3_BUCKET=S3_BUCKET,
		S3_PREFIX=S3_PREFIX,
	)

	_register_routes(app)
	return app


def _resolve_cors_origins() -> Iterable[str] | str:
	configured = os.getenv("PERSONALIZED_TRAILER_ALLOWED_ORIGINS")
	if configured:
		configured = configured.strip()
		if configured == "*":
			return "*"
		origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
		return origins or ["http://localhost:3000", "https://localhost:3000"]

	defaults = [
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		"http://0.0.0.0:3000",
	]
	https_variants = [origin.replace("http://", "https://", 1) for origin in defaults]
	return defaults + https_variants


def _register_routes(app: Flask) -> None:
	def _load_job(job_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
		job_path = JOBS_DIR / f"{job_id}.json"
		if not job_path.exists():
			return None, 404
		try:
			return json.loads(job_path.read_text()), None
		except json.JSONDecodeError as exc:  # pragma: no cover - unexpected
			app.logger.error("Failed to load job %s: %s", job_id, exc)
			return None, 500

	@app.route("/health", methods=["GET"])
	def health() -> Any:
		services = {
			"rekognition": PIPELINE_MODE != "mock",
			"personalize": PIPELINE_MODE != "mock",
			"mediaconvert": PIPELINE_MODE != "mock",
			"s3": bool(S3_BUCKET),
			"sagemaker": PIPELINE_MODE != "mock",
			"transcribe": PIPELINE_MODE != "mock",
			"translate": PIPELINE_MODE != "mock",
		}
		return jsonify(
			{
				"status": "ok",
				"mode": PIPELINE_MODE,
				"region": AWS_REGION,
				"services": services,
				"bucket": S3_BUCKET,
			}
		)

	@app.route("/profiles", methods=["GET"])
	def list_profiles() -> Any:
		return jsonify(
			{
				"profiles": PROFILE_PRESETS,
				"defaults": {
					"languages": DEFAULT_LANGUAGES,
					"durations": DEFAULT_DURATIONS,
					"outputFormats": DEFAULT_OUTPUT_FORMATS,
				},
			}
		)

	@app.route("/options", methods=["GET"])
	def list_options() -> Any:
		return jsonify(
			{
				"languages": DEFAULT_LANGUAGES,
				"durations": DEFAULT_DURATIONS,
				"outputFormats": DEFAULT_OUTPUT_FORMATS,
				"subtitleLanguages": DEFAULT_LANGUAGES,
			}
		)

	@app.route("/jobs/<job_id>", methods=["GET"])
	def fetch_job(job_id: str) -> Any:
		job_data, error_status = _load_job(job_id)
		if job_data is None:
			if error_status == 500:
				return jsonify({"error": "Job data corrupted"}), 500
			return jsonify({"error": "Job not found"}), 404
		return jsonify(job_data)

	@app.route("/jobs/<job_id>/deliverables/<artifact>", methods=["GET"])
	def stream_deliverable(job_id: str, artifact: str):
		job_data, error_status = _load_job(job_id)
		if job_data is None:
			if error_status == 500:
				return jsonify({"error": "Job data corrupted"}), 500
			return jsonify({"error": "Job not found"}), 404
		deliverables = job_data.get("job", {}).get("deliverables", {})
		entry = deliverables.get(artifact)
		if not isinstance(entry, dict):
			return jsonify({"error": "Deliverable not found"}), 404
		rel_path = entry.get("path")
		if not rel_path:
			return jsonify({"error": "Deliverable unavailable"}), 404
		file_path = (BASE_DIR / rel_path).resolve()
		try:
			file_path.relative_to(BASE_DIR)
		except ValueError:
			return jsonify({"error": "Deliverable path invalid"}), 400
		if not file_path.exists():
			return jsonify({"error": "Deliverable file missing"}), 404
		mime_type = entry.get("mimeType")
		if not mime_type:
			mime_type, _ = mimetypes.guess_type(file_path.name)
		download_flag = request.args.get("download", "false").lower() == "true"
		return send_file(
			file_path,
			mimetype=mime_type or "application/octet-stream",
			as_attachment=download_flag,
			download_name=file_path.name,
			conditional=True,
			etag=True,
		)

	@app.route("/jobs/<job_id>/storyboard", methods=["GET"])
	def download_storyboard(job_id: str):
		storyboard_path = OUTPUT_DIR / f"{job_id}_storyboard.json"
		if not storyboard_path.exists():
			return jsonify({"error": "Storyboard not found"}), 404
		return send_file(storyboard_path, mimetype="application/json", as_attachment=True)

	@app.route("/generate", methods=["POST"])
	def generate_trailer() -> Any:
		if "video" not in request.files:
			return jsonify({"error": "Video file is required."}), 400

		video_file = request.files["video"]
		if video_file.filename == "":
			return jsonify({"error": "Video file name is empty."}), 400

		if not _allowed_file(video_file.filename):
			return jsonify({"error": "Unsupported video format."}), 400

		profile_id = request.form.get("profile_id")
		profile = next((item for item in PROFILE_PRESETS if item["id"] == profile_id), None)
		if not profile:
			return jsonify({"error": "Unknown profile selection."}), 400

		target_language = request.form.get("target_language", "en")
		subtitle_language = request.form.get("subtitle_language", target_language)
		max_duration = int(request.form.get("max_duration", "60"))
		output_format = request.form.get("output_format", "mp4")
		include_captions = request.form.get("include_captions", "true").lower() == "true"
		include_storyboard = request.form.get("include_storyboard", "true").lower() == "true"

		job_id = uuid.uuid4().hex
		timestamp = datetime.utcnow().isoformat() + "Z"

		filename = _secure_filename(video_file.filename)
		upload_path = UPLOAD_DIR / f"{job_id}_{filename}"
		video_file.save(upload_path)

		app.logger.info("Saved upload %s (%s) for job %s", filename, upload_path, job_id)

		pipeline_artifacts = _run_pipeline(
			app=app,
			job_id=job_id,
			video_path=upload_path,
			profile=profile,
			target_language=target_language,
			subtitle_language=subtitle_language,
			max_duration=max_duration,
			output_format=output_format,
			include_captions=include_captions,
			include_storyboard=include_storyboard,
		)

		job_payload = {
			"job": {
				"jobId": job_id,
				"status": "completed",
				"submittedAt": timestamp,
				"completedAt": datetime.utcnow().isoformat() + "Z",
				"mode": PIPELINE_MODE,
				"input": {
					"sourceFile": filename,
					"profile": profile,
					"targetLanguage": target_language,
					"subtitleLanguage": subtitle_language,
					"maxDurationSeconds": max_duration,
					"outputFormat": output_format,
				},
				"providers": pipeline_artifacts["providers"],
				"analysis": pipeline_artifacts["analysis"],
				"personalization": pipeline_artifacts["personalization"],
				"assembly": pipeline_artifacts["assembly"],
				"assemblies": pipeline_artifacts.get("assemblies", []),
				"deliverables": pipeline_artifacts["deliverables"],
			}
		}

		job_path = JOBS_DIR / f"{job_id}.json"
		job_path.write_text(json.dumps(job_payload, indent=2))
		app.logger.info("Job %s completed. Outputs saved to %s", job_id, job_path)

		return jsonify(job_payload), 200


def _allowed_file(filename: str) -> bool:
	return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _secure_filename(filename: str) -> str:
	sanitized = filename.replace("..", "").replace("/", "_").replace("\\", "_")
	return sanitized or "upload.mp4"


def _run_pipeline(
	app: Flask,
	job_id: str,
	video_path: Path,
	profile: Dict[str, Any],
	target_language: str,
	subtitle_language: str,
	max_duration: int,
	output_format: str,
	include_captions: bool,
	include_storyboard: bool,
) -> Dict[str, Any]:
	start_time = time.time()
	seed = int(job_id[:8], 16)
	rng = random.Random(seed)

	source_duration = _probe_media_duration(video_path)
	
	# Use AWS Rekognition if available, fallback to mock
	if PIPELINE_MODE == "aws" and boto3:
		try:
			app.logger.info("Job %s: Starting AWS Rekognition analysis...", job_id)
			analysis = _aws_rekognition_analysis(
				job_id=job_id,
				video_path=video_path,
				profile=profile,
				source_duration=source_duration or None,
			)
			app.logger.info("Job %s: AWS Rekognition analysis completed", job_id)
		except Exception as exc:
			app.logger.error("Job %s: AWS Rekognition failed (%s), falling back to mock", job_id, exc, exc_info=True)
			analysis = _mock_rekognition_analysis(
				rng=rng,
				video_path=video_path,
				profile=profile,
				source_duration=source_duration or None,
			)
	else:
		app.logger.info("Job %s: Using mock mode for analysis", job_id)
		analysis = _mock_rekognition_analysis(
			rng=rng,
			video_path=video_path,
			profile=profile,
			source_duration=source_duration or None,
		)
	personalization = _mock_personalize_scenes(rng=rng, analysis=analysis, profile=profile, max_duration=max_duration)
	
	# Generate main assembly using original selected scenes (backward compatible)
	assembly = _mock_assemble_trailer(
		rng=rng,
		personalization=personalization,
		output_format=output_format,
		max_duration=max_duration,
		source_duration=source_duration or None,
	)
	
	# Generate additional variant assemblies
	assemblies = []
	for variant in personalization.get("variants", []):
		# Create a temporary personalization object for this variant
		variant_personalization = dict(personalization)
		variant_personalization["selectedScenes"] = variant.get("scenes", [])
		
		variant_assembly = _mock_assemble_trailer(
			rng=rng,
			personalization=variant_personalization,
			output_format=output_format,
			max_duration=max_duration,
			source_duration=source_duration or None,
		)
		# Add variant metadata
		variant_assembly["variantName"] = variant.get("name", "Unknown")
		variant_assembly["variantDescription"] = variant.get("description", "")
		variant_assembly["distribution"] = variant.get("distribution", {})
		assemblies.append(variant_assembly)
	
	# Generate deliverables for all variants
	deliverables = _generate_deliverables_multivariant(
		job_id=job_id,
		rng=rng,
		assemblies=assemblies,
		primary_assembly=assembly,
		target_language=target_language,
		subtitle_language=subtitle_language,
		include_captions=include_captions,
		include_storyboard=include_storyboard,
		video_path=video_path,
		source_duration=source_duration or None,
	)

	end_time = time.time()

	providers = {
		"rekognition": {
			"mode": PIPELINE_MODE,
			"region": AWS_REGION,
			"analysisMs": analysis["metrics"]["analysisMs"],
		},
		"personalize": {
			"mode": PIPELINE_MODE,
			"selectedScenes": len(personalization["rankedScenes"]),
		},
		"mediaconvert": {
			"mode": PIPELINE_MODE,
			"renditions": len(assembly["renditions"]),
		},
		"transcribe": {
			"mode": PIPELINE_MODE,
			"subtitleLanguage": subtitle_language,
		},
		"translate": {
			"mode": PIPELINE_MODE,
			"targetLanguage": target_language,
		},
		"sagemaker": {
			"mode": PIPELINE_MODE,
			"model": "engagement-ranking-v1",
		},
		"lambda": {
			"mode": PIPELINE_MODE,
			"workflowSeconds": round(end_time - start_time, 2),
		},
	}

	return {
		"providers": providers,
		"analysis": analysis,
		"personalization": personalization,
		"assembly": assembly,
		"assemblies": assemblies,  # All variant assemblies
		"deliverables": deliverables,
	}


def _probe_media_duration(video_path: Path) -> float:
	ffprobe_bin = shutil.which("ffprobe")
	if not ffprobe_bin:
		return 0.0
	cmd = [
		ffprobe_bin,
		"-v",
		"error",
		"-show_entries",
		"format=duration",
		"-of",
		"default=noprint_wrappers=1:nokey=1",
		str(video_path),
	]
	try:
		result = subprocess.run(cmd, capture_output=True, text=True, check=True)
		return max(0.0, float(result.stdout.strip()))
	except Exception:
		return 0.0


def _aws_rekognition_analysis(
	job_id: str,
	video_path: Path,
	profile: Dict[str, Any],
	source_duration: Optional[float] = None,
) -> Dict[str, Any]:
	"""Real AWS Rekognition video analysis with segment detection."""
	import tempfile
	start_time = time.time()
	
	if not boto3:
		raise RuntimeError("boto3 not available")
	
	rekognition = boto3.client("rekognition", region_name=AWS_REGION)
	
	# Calculate video duration
	if not source_duration or source_duration <= 0:
		source_duration = _probe_media_duration(video_path)
		if source_duration <= 0:
			source_duration = 60.0  # Default fallback
	
	# Extract frames at regular intervals for analysis
	frame_interval = max(2.0, source_duration / 30)  # Analyze ~30 frames max
	frame_times = []
	cursor = 0.0
	while cursor < source_duration and len(frame_times) < 30:
		frame_times.append(cursor)
		cursor += frame_interval
	
	# Create temp directory for frames
	temp_dir = Path(tempfile.mkdtemp(prefix=f"trailer_{job_id}_"))
	frame_paths = []
	
	try:
		# Extract frames using FFmpeg
		ffmpeg_bin = shutil.which("ffmpeg")
		if not ffmpeg_bin:
			raise RuntimeError("FFmpeg not found")
		
		for idx, timestamp in enumerate(frame_times):
			frame_path = temp_dir / f"frame_{idx:04d}.jpg"
			cmd = [
				ffmpeg_bin, "-hide_banner", "-loglevel", "error",
				"-ss", str(timestamp),
				"-i", str(video_path),
				"-frames:v", "1",
				"-q:v", "2",
				str(frame_path)
			]
			subprocess.run(cmd, check=True)
			frame_paths.append((timestamp, frame_path))
		
		# Analyze each frame with AWS Rekognition
		scenes = []
		all_labels = []
		all_emotions = []
		all_celebrities = []
		detected_people = 0
		detected_locations = set()
		detected_objects = set()
		
		for timestamp, frame_path in frame_paths:
			with open(frame_path, "rb") as image_file:
				image_bytes = image_file.read()
			
			# Detect labels (objects, scenes, activities)
			try:
				label_response = rekognition.detect_labels(
					Image={"Bytes": image_bytes},
					MaxLabels=25,
					MinConfidence=60.0,
					Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"]
				)
				frame_labels = []
				for label in label_response.get("Labels", []):
					name = label.get("Name")
					confidence = label.get("Confidence", 0)
					frame_labels.append({
						"name": name,
						"confidence": round(confidence, 2),
						"parents": [p.get("Name") for p in label.get("Parents", [])]
					})
					all_labels.append(name)
					
					# Categorize
					for parent in label.get("Parents", []):
						parent_name = parent.get("Name", "")
						if parent_name in ["Building", "Urban", "City"]:
							detected_locations.add("Urban")
						elif parent_name in ["Nature", "Outdoors"]:
							detected_locations.add("Outdoor")
					
					if name in ["Car", "Vehicle", "Weapon", "Building"]:
						detected_objects.add(name)
			except Exception as e:
				frame_labels = []
			
			# Detect faces and emotions
			frame_emotions = []
			frame_characters = []
			try:
				face_response = rekognition.detect_faces(
					Image={"Bytes": image_bytes},
					Attributes=["ALL"]
				)
				for face in face_response.get("FaceDetails", []):
					detected_people += 1
					emotions = face.get("Emotions", [])
					if emotions:
						top_emotion = max(emotions, key=lambda e: e.get("Confidence", 0))
						emotion_type = top_emotion.get("Type")
						emotion_conf = top_emotion.get("Confidence", 0)
						frame_emotions.append(emotion_type)
						all_emotions.append(emotion_type)
						
						# Create character entry
						age_range = face.get("AgeRange", {})
						frame_characters.append({
							"name": "Person",
							"confidence": round(face.get("Confidence", 0), 2),
							"emotion": emotion_type,
							"ageRange": f"{age_range.get('Low', 0)}-{age_range.get('High', 0)}",
							"gender": face.get("Gender", {}).get("Value", "Unknown")
						})
			except Exception:
				pass
			
			# Detect celebrities
			try:
				celeb_response = rekognition.recognize_celebrities(
					Image={"Bytes": image_bytes}
				)
				for celeb in celeb_response.get("CelebrityFaces", []):
					celeb_name = celeb.get("Name")
					if celeb_name:
						all_celebrities.append(celeb_name)
			except Exception:
				pass
		
		# Group frames into scenes (simple segmentation based on label similarity)
		scene_duration = max(10, int(source_duration / 5))  # ~5 scenes
		num_scenes = max(3, int(source_duration / scene_duration))
		
		for scene_idx in range(num_scenes):
			start = scene_idx * scene_duration
			end = min((scene_idx + 1) * scene_duration, source_duration)
			
			# Get labels for this time range
			scene_labels = []
			scene_emotions = []
			scene_characters = []
			
			for timestamp, frame_path in frame_paths:
				if start <= timestamp < end:
					# Re-analyze this frame (simplified - reuse previous data in production)
					with open(frame_path, "rb") as f:
						img_bytes = f.read()
					try:
						resp = rekognition.detect_labels(Image={"Bytes": img_bytes}, MaxLabels=10)
						for lbl in resp.get("Labels", [])[:5]:
							scene_labels.append(lbl.get("Name"))
					except:
						pass
					
					try:
						face_resp = rekognition.detect_faces(Image={"Bytes": img_bytes}, Attributes=["EMOTIONS"])
						for face in face_resp.get("FaceDetails", [])[:3]:
							emots = face.get("Emotions", [])
							if emots:
								scene_emotions.append(max(emots, key=lambda e: e["Confidence"])["Type"])
								scene_characters.append({
									"name": "Person",
									"confidence": 85.0,
									"emotion": scene_emotions[-1]
								})
					except:
						pass
			
			# Remove duplicates but keep order
			unique_labels = list(dict.fromkeys(scene_labels[:5]))
			unique_emotions = list(dict.fromkeys(scene_emotions[:3]))
			
			scenes.append({
				"sceneId": f"scene_{scene_idx + 1}",
				"start": round(start, 2),
				"end": round(end, 2),
				"duration": round(end - start, 2),
				"emotions": unique_emotions or ["Neutral"],
				"labels": unique_labels or ["Unknown"],
				"characters": scene_characters[:3],
				"keyVisual": f"frame_{scene_idx:02d}.jpg",
				"highlights": unique_labels[:2] if unique_labels else []
			})
		
		# Calculate dominant emotions
		from collections import Counter
		emotion_counts = Counter(all_emotions)
		dominant_emotions = [e for e, _ in emotion_counts.most_common(3)]
		if not dominant_emotions:
			dominant_emotions = profile["preferences"].get("dominantEmotions", ["Neutral"])
		
		analysis_ms = int((time.time() - start_time) * 1000)
		
		return {
			"video": video_path.name,
			"totalDuration": round(source_duration, 2),
			"scenes": scenes,
			"dominantEmotions": dominant_emotions,
			"metrics": {
				"analysisMs": analysis_ms,
				"detectedPeople": detected_people,
				"detectedLocations": len(detected_locations),
				"detectedObjects": len(detected_objects),
				"coverageSeconds": source_duration,
				"coverageRatio": 1.0,
				"gapCount": 0,
				"largestGapSeconds": 0.0,
				"framesAnalyzed": len(frame_paths),
				"awsApiCalls": len(frame_paths) * 3,  # labels + faces + celebrities
			}
		}
	
	finally:
		# Cleanup temp files
		try:
			shutil.rmtree(temp_dir, ignore_errors=True)
		except:
			pass


def _mock_rekognition_analysis(
	rng: random.Random,
	video_path: Path,
	profile: Dict[str, Any],
	source_duration: Optional[float] = None,
) -> Dict[str, Any]:
	if source_duration and source_duration > 1:
		base_duration = float(source_duration)
	else:
		base_duration = float(rng.randint(90, 150))

	dominant_emotions = profile["preferences"]["dominantEmotions"]
	tags_pool = profile["preferences"].get("foregroundTags", []) + [
		"Landscape",
		"Dialogue",
		"Crowd",
		"Vehicle",
		"Logo",
	]

	min_scene_len = 6.0
	max_scene_len = 18.0
	# Create enough scenes to cover the full video duration
	target_scene_count = max(10, min(30, int(math.ceil(base_duration / 12.0))))

	cursor = 0.0
	scenes: List[Dict[str, Any]] = []
	scene_index = 0
	while cursor < (base_duration - min_scene_len) and len(scenes) < target_scene_count:
		scene_index += 1
		remaining = max(base_duration - cursor, min_scene_len)
		remaining_slots = max(target_scene_count - len(scenes) - 1, 0)
		max_alloc_for_scene = max(min_scene_len, min(max_scene_len, remaining - (remaining_slots * min_scene_len)))
		min_alloc_for_scene = min(min_scene_len, max_alloc_for_scene)
		scene_length = rng.uniform(min_alloc_for_scene, max_alloc_for_scene)
		start = cursor
		end = min(base_duration, start + scene_length)

		scene_emotions = rng.sample(dominant_emotions + ["Neutral", "Joy", "Fear"], k=2)
		labels = rng.sample(tags_pool, k=min(3, len(tags_pool)))
		characters = [
			{
				"name": rng.choice(["Lead", "Supporting", "Cameo"]),
				"confidence": round(rng.uniform(72, 98), 2),
				"emotion": scene_emotions[0],
			}
			for _ in range(rng.randint(1, 3))
		]

		scenes.append(
			{
				"sceneId": f"scene_{scene_index}",
				"start": round(start, 2),
				"end": round(end, 2),
				"duration": round(end - start, 2),
				"emotions": scene_emotions,
				"labels": labels,
				"characters": characters,
				"keyVisual": f"frame_{scene_index:02d}.jpg",
				"highlights": rng.sample(labels + scene_emotions, k=min(2, len(labels + scene_emotions))),
			}
		)

		cursor = end
		gap_budget = max(0.0, base_duration - cursor - (remaining_slots * min_scene_len))
		if gap_budget > 0:
			cursor += rng.uniform(0.0, min(2.5, gap_budget))

	# Ensure scenes cover the full video - add more scenes if needed to reach the end
	while cursor < base_duration and len(scenes) < target_scene_count * 2:
		scene_index += 1
		remaining = base_duration - cursor
		if remaining < min_scene_len:
			# Extend the last scene to the end
			if scenes:
				scenes[-1]["end"] = round(base_duration, 2)
				scenes[-1]["duration"] = round(base_duration - scenes[-1]["start"], 2)
			break
		
		scene_length = min(remaining, rng.uniform(min_scene_len, max_scene_len))
		start = cursor
		end = min(base_duration, start + scene_length)
		
		scene_emotions = rng.sample(dominant_emotions + ["Neutral", "Joy", "Fear"], k=2)
		labels = rng.sample(tags_pool, k=min(3, len(tags_pool)))
		characters = [
			{
				"name": rng.choice(["Lead", "Supporting", "Cameo"]),
				"confidence": round(rng.uniform(72, 98), 2),
				"emotion": scene_emotions[0],
			}
			for _ in range(rng.randint(1, 3))
		]
		
		scenes.append(
			{
				"sceneId": f"scene_{scene_index}",
				"start": round(start, 2),
				"end": round(end, 2),
				"duration": round(end - start, 2),
				"emotions": scene_emotions,
				"labels": labels,
				"characters": characters,
				"keyVisual": f"frame_{scene_index:02d}.jpg",
				"highlights": rng.sample(labels + scene_emotions, k=min(2, len(labels + scene_emotions))),
			}
		)
		cursor = end

	coverage_seconds = scenes[-1]["end"] if scenes else 0.0
	coverage_ratio = round(coverage_seconds / base_duration, 3) if base_duration else 0.0
	gap_lengths: List[float] = []
	last_end = 0.0
	for scene in scenes:
		if scene["start"] > last_end:
			gap_lengths.append(round(scene["start"] - last_end, 2))
		last_end = scene["end"]

	metrics = {
		"analysisMs": rng.randint(850, 1450),
		"detectedPeople": rng.randint(5, 14),
		"detectedLocations": rng.randint(2, 6),
		"detectedObjects": rng.randint(10, 22),
		"coverageSeconds": round(coverage_seconds, 2),
		"coverageRatio": coverage_ratio,
		"gapCount": len([gap for gap in gap_lengths if gap >= 0.5]),
		"largestGapSeconds": round(max(gap_lengths) if gap_lengths else 0.0, 2),
	}

	return {
		"video": video_path.name,
		"totalDuration": round(base_duration, 2),
		"scenes": scenes,
		"dominantEmotions": dominant_emotions,
		"metrics": metrics,
	}


def _mock_personalize_scenes(
	rng: random.Random,
	analysis: Dict[str, Any],
	profile: Dict[str, Any],
	max_duration: int,
) -> Dict[str, Any]:
	ranked: List[Dict[str, Any]] = []
	total_duration = max(float(analysis.get("totalDuration") or 1.0), 1.0)
	profile_preferences = profile.get("preferences", {})
	preferred_emotions = set(profile_preferences.get("dominantEmotions", []))
	preferred_tags = set(profile_preferences.get("foregroundTags", []))

	for scene in analysis["scenes"]:
		score = rng.uniform(0.6, 0.98)
		weight = 1.0
		for emotion in scene["emotions"]:
			if emotion in preferred_emotions:
				weight += 0.15
		for tag in scene["labels"]:
			if tag in preferred_tags:
				weight += 0.1
		weighted_score = min(1.0, round(score * weight, 3))
		normalized_start = max(0.0, min(0.999, scene["start"] / total_duration))
		ranked.append(
			{
				"sceneId": scene["sceneId"],
				"score": weighted_score,
				"start": scene["start"],
				"end": scene["end"],
				"duration": scene["duration"],
				"labels": scene["labels"],
				"emotions": scene["emotions"],
				"normalizedStart": normalized_start,
			}
		)

	ranked.sort(key=lambda item: item["score"], reverse=True)

	regions = {
		"early": {
			"items": [],
			"quota": max_duration * 0.3,
		},
		"middle": {
			"items": [],
			"quota": max_duration * 0.4,
		},
		"late": {
			"items": [],
			"quota": max_duration * 0.3,
		},
	}

	for item in ranked:
		if item["normalizedStart"] < 1 / 3:
			regions["early"]["items"].append(item)
		elif item["normalizedStart"] < 2 / 3:
			regions["middle"]["items"].append(item)
		else:
			regions["late"]["items"].append(item)

	selected: List[Dict[str, Any]] = []
	selected_ids = set()
	cumulative = 0.0
	max_total = max_duration * 1.05
	min_coverage = max_duration * 0.7

	def try_add(candidate: Dict[str, Any], allow_overshoot: bool = False) -> bool:
		nonlocal cumulative
		if candidate["sceneId"] in selected_ids:
			return False
		duration = max(1.5, float(candidate.get("duration", 0)) or 0)
		future = cumulative + duration
		if not allow_overshoot and cumulative > 0 and future > max_total:
			return False
		selected.append(candidate)
		selected_ids.add(candidate["sceneId"])
		cumulative = future
		return True

	region_metrics: Dict[str, Any] = {}
	for name, meta in regions.items():
		bucket = meta["items"]
		bucket_duration = 0.0
		for candidate in bucket:
			if bucket_duration >= meta["quota"] or cumulative >= max_duration:
				break
			if try_add(candidate):
				bucket_duration += max(1.5, float(candidate.get("duration", 0)) or 0)
		region_metrics[name] = {
			"count": len(bucket),
			"selected": sum(1 for item in selected if item in bucket),
			"quotaSeconds": round(meta["quota"], 2),
			"allocatedSeconds": round(bucket_duration, 2),
		}

	for name, meta in regions.items():
		if not meta["items"]:
			continue
		if any(item in meta["items"] for item in selected):
			continue
		for candidate in meta["items"]:
			if try_add(candidate, allow_overshoot=True):
				break

	for name, meta in regions.items():
		region_metrics[name]["selected"] = sum(1 for item in selected if item in meta["items"])

	if cumulative < max_duration:
		for candidate in ranked:
			if cumulative >= max_duration:
				break
			try_add(candidate)

	if cumulative < min_coverage:
		for candidate in ranked:
			if candidate["sceneId"] in selected_ids:
				continue
			if try_add(candidate, allow_overshoot=True):
				if cumulative >= min_coverage:
					break

	selected.sort(key=lambda item: item["start"])

	# Generate multiple variants with UNIQUE content selections
	# Strategy: Use interleaving and offset selection to minimize overlap
	variants = []
	used_across_variants = set()  # Track scenes used across ALL variants
	
	def select_variant_scenes(
		early_ratio: float, 
		middle_ratio: float, 
		late_ratio: float,
		variant_name: str,
		offset_multiplier: int = 0
	) -> List[Dict[str, Any]]:
		"""
		Select scenes for a variant with minimal overlap to other variants.
		Uses offset and interleaving to maximize unique content.
		"""
		variant_scenes = []
		variant_duration = 0.0
		variant_scene_ids = set()
		target_dur = max_duration
		
		# Calculate how many scenes needed from each region
		early_count = max(1, int((target_dur * early_ratio) / 10))  # ~10s per scene
		middle_count = max(1, int((target_dur * middle_ratio) / 10))
		late_count = max(1, int((target_dur * late_ratio) / 10))
		
		# Early region - use offset and skip pattern to avoid overlap
		early_sorted = sorted(regions["early"]["items"], key=lambda x: x["score"], reverse=True)
		early_taken = 0
		for i in range(offset_multiplier, len(early_sorted), 2):  # Skip every other scene
			if early_taken >= early_count or variant_duration >= target_dur * (early_ratio + 0.1):
				break
			scene = early_sorted[i]
			if scene["sceneId"] not in used_across_variants:
				variant_scenes.append(scene)
				variant_scene_ids.add(scene["sceneId"])
				variant_duration += scene.get("duration", 0)
				early_taken += 1
		
		# If we need more early scenes, take any available (even if used by other variants)
		if early_taken < early_count:
			for scene in early_sorted:
				if scene["sceneId"] not in variant_scene_ids and early_taken < early_count:
					variant_scenes.append(scene)
					variant_scene_ids.add(scene["sceneId"])
					variant_duration += scene.get("duration", 0)
					early_taken += 1
		
		# Middle region - different offset
		middle_sorted = sorted(regions["middle"]["items"], key=lambda x: x["score"], reverse=True)
		middle_taken = 0
		middle_offset = (offset_multiplier + 1) % 2  # Alternate offset
		for i in range(middle_offset, len(middle_sorted), 2):
			if middle_taken >= middle_count or variant_duration >= target_dur * (early_ratio + middle_ratio + 0.1):
				break
			scene = middle_sorted[i]
			if scene["sceneId"] not in used_across_variants:
				variant_scenes.append(scene)
				variant_scene_ids.add(scene["sceneId"])
				variant_duration += scene.get("duration", 0)
				middle_taken += 1
		
		if middle_taken < middle_count:
			for scene in middle_sorted:
				if scene["sceneId"] not in variant_scene_ids and middle_taken < middle_count:
					variant_scenes.append(scene)
					variant_scene_ids.add(scene["sceneId"])
					variant_duration += scene.get("duration", 0)
					middle_taken += 1
		
		# Late region - different offset
		late_sorted = sorted(regions["late"]["items"], key=lambda x: x["score"], reverse=True)
		late_taken = 0
		late_offset = offset_multiplier % 2
		for i in range(late_offset, len(late_sorted), 2):
			if late_taken >= late_count or variant_duration >= target_dur:
				break
			scene = late_sorted[i]
			if scene["sceneId"] not in used_across_variants:
				variant_scenes.append(scene)
				variant_scene_ids.add(scene["sceneId"])
				variant_duration += scene.get("duration", 0)
				late_taken += 1
		
		if late_taken < late_count:
			for scene in late_sorted:
				if scene["sceneId"] not in variant_scene_ids and late_taken < late_count:
					variant_scenes.append(scene)
					variant_scene_ids.add(scene["sceneId"])
					variant_duration += scene.get("duration", 0)
					late_taken += 1
		
		# Mark these scenes as used across variants
		for scene in variant_scenes:
			used_across_variants.add(scene["sceneId"])
		
		# Fallback: if no scenes, use from ranked list with offset
		if not variant_scenes and ranked:
			start_idx = offset_multiplier * 3
			variant_scenes = ranked[start_idx:start_idx + 5]
		
		variant_scenes.sort(key=lambda x: x["start"])
		return variant_scenes
	
	# Variant 1: "Opening Act" - 60% early, 30% middle, 10% late (offset 0)
	variant1_scenes = select_variant_scenes(0.6, 0.3, 0.1, "Opening Act", offset_multiplier=0)
	variants.append({
		"name": "Opening Act",
		"description": "Emphasizes the beginning and setup",
		"scenes": variant1_scenes,
		"distribution": {"early": "60%", "middle": "30%", "late": "10%"}
	})
	
	# Variant 2: "Middle Climax" - 20% early, 60% middle, 20% late (offset 1)
	variant2_scenes = select_variant_scenes(0.2, 0.6, 0.2, "Middle Climax", offset_multiplier=1)
	variants.append({
		"name": "Middle Climax",
		"description": "Showcases the peak action and drama",
		"scenes": variant2_scenes,
		"distribution": {"early": "20%", "middle": "60%", "late": "20%"}
	})
	
	# Variant 3: "Grand Finale" - 10% early, 30% middle, 60% late (offset 0, but late-focused)
	variant3_scenes = select_variant_scenes(0.1, 0.3, 0.6, "Grand Finale", offset_multiplier=0)
	variants.append({
		"name": "Grand Finale",
		"description": "Highlights the climax and resolution",
		"scenes": variant3_scenes,
		"distribution": {"early": "10%", "middle": "30%", "late": "60%"}
	})
	
	# Variant 4: "Balanced Mix" - 33% each (offset 1)
	variant4_scenes = select_variant_scenes(0.33, 0.34, 0.33, "Balanced Mix", offset_multiplier=1)
	variants.append({
		"name": "Balanced Mix",
		"description": "Equal representation from beginning, middle, and end",
		"scenes": variant4_scenes,
		"distribution": {"early": "33%", "middle": "34%", "late": "33%"}
	})

	return {
		"rankedScenes": ranked,
		"selectedScenes": selected,  # Keep original for backward compatibility
		"variants": variants,
		"targetDuration": max_duration,
		"estimatedDuration": round(cumulative, 2),
		"selectionStrategy": {
			"coverage": {
				"targetSeconds": max_duration,
				"achievedSeconds": round(cumulative, 2),
				"minCoverageSeconds": round(min_coverage, 2),
				"maxSeconds": round(max_total, 2),
			},
			"regions": region_metrics,
			"selectedCount": len(selected),
			"variantsGenerated": len(variants),
		},
	}


def _mock_assemble_trailer_variant(
	rng: random.Random,
	variant: Dict[str, Any],
	output_format: str,
	max_duration: int,
	source_duration: Optional[float] = None,
) -> Dict[str, Any]:
	"""Assemble a trailer from a specific variant's scene selection."""
	renditions = [
		{
			"format": output_format,
			"resolution": "1920x1080",
			"bitrate": "8Mbps",
			"storageKey": f"master_{output_format}",
		}
	]
	renditions.append(
		{
			"format": "hls",
			"resolution": "1280x720",
			"bitrate": "4Mbps",
			"storageKey": "adaptive_hls",
		}
	)

	selected_scenes = variant.get("scenes", [])
	timeline = []
	cursor = 0.0
	last_source_end = 0.0
	
	for index, scene in enumerate(selected_scenes):
		if cursor >= max_duration:
			break
		next_scene = selected_scenes[index + 1] if index + 1 < len(selected_scenes) else None
		orig_start = float(scene.get("start", cursor))
		orig_end = float(scene.get("end", orig_start))
		base_duration = max(0.5, float(scene.get("duration", orig_end - orig_start)) or 0.5)

		pad_before = 0.75
		if last_source_end > 0:
			gap_from_previous = max(0.0, orig_start - last_source_end)
			pad_before = min(pad_before, gap_from_previous)
		pad_before = max(0.0, pad_before)

		pad_after = 0.9
		if next_scene is not None:
			next_start = float(next_scene.get("start", orig_end))
			gap_to_next = next_start - orig_end
			if gap_to_next > 0:
				pad_after = min(pad_after, max(0.25, gap_to_next * 0.45))
			else:
				pad_after = 0.3

		source_start = max(0.0, orig_start - pad_before)
		source_end = orig_end + pad_after

		if source_duration is not None:
			source_start = min(source_start, max(0.0, source_duration - 1.5))
			source_end = min(source_end, source_duration)

		clip_duration = max(1.5, source_end - source_start)
		remaining = max(0.0, max_duration - cursor)
		if remaining <= 0.0:
			break
		if clip_duration > remaining:
			source_end = source_start + remaining
			clip_duration = remaining
			pad_after = max(0.1, source_end - orig_end)

		if source_start < last_source_end:
			adjustment = last_source_end - source_start
			source_start += adjustment
			clip_duration = max(1.2, source_end - source_start)
			pad_before = max(0.0, orig_start - source_start)

		if clip_duration <= 0.75:
			continue
		if clip_duration <= 0:
			continue
			
		transition = rng.choice(["cut", "fade", "dip"])
		audio_cue = rng.choice(["rise", "drop", "sting", "motif"])
		pad_before_used = max(0.0, orig_start - source_start)
		pad_after_used = max(0.0, source_end - orig_end)
		
		timeline.append(
			{
				"sceneId": scene["sceneId"],
				"in": cursor,
				"out": cursor + clip_duration,
				"sourceStart": source_start,
				"sourceEnd": source_end,
				"handles": {
					"padBefore": round(pad_before_used, 2),
					"padAfter": round(pad_after_used, 2),
				},
				"transition": transition,
				"audioCue": audio_cue,
			}
		)
		cursor += clip_duration
		last_source_end = source_end

	return {
		"variantName": variant.get("name", "Unknown"),
		"variantDescription": variant.get("description", ""),
		"distribution": variant.get("distribution", {}),
		"timeline": timeline,
		"renditions": renditions,
		"estimatedDuration": min(cursor, max_duration),
		"mixNotes": rng.sample(
			[
				"Accent hero theme under final VO",
				"Layer low percussion for tension",
				"Add crowd texture in stadium beat",
				"Emphasize dialogue reverb on reveal",
			],
			k=2,
		),
		"sourceDuration": source_duration,
	}


def _mock_assemble_trailer(
	rng: random.Random,
	personalization: Dict[str, Any],
	output_format: str,
	max_duration: int,
	source_duration: Optional[float] = None,
) -> Dict[str, Any]:
	renditions = [
		{
			"format": output_format,
			"resolution": "1920x1080",
			"bitrate": "8Mbps",
			"storageKey": f"master_{output_format}",
		}
	]
	renditions.append(
		{
			"format": "hls",
			"resolution": "1280x720",
			"bitrate": "4Mbps",
			"storageKey": "adaptive_hls",
		}
	)

	selected_scenes = list(personalization["selectedScenes"])
	timeline = []
	cursor = 0.0
	last_source_end = 0.0
	for index, scene in enumerate(selected_scenes):
		if cursor >= max_duration:
			break
		next_scene = selected_scenes[index + 1] if index + 1 < len(selected_scenes) else None
		orig_start = float(scene.get("start", cursor))
		orig_end = float(scene.get("end", orig_start))
		base_duration = max(0.5, float(scene.get("duration", orig_end - orig_start)) or 0.5)

		pad_before = 0.75
		if last_source_end > 0:
			gap_from_previous = max(0.0, orig_start - last_source_end)
			pad_before = min(pad_before, gap_from_previous)
		pad_before = max(0.0, pad_before)

		pad_after = 0.9
		if next_scene is not None:
			next_start = float(next_scene.get("start", orig_end))
			gap_to_next = next_start - orig_end
			if gap_to_next > 0:
				pad_after = min(pad_after, max(0.25, gap_to_next * 0.45))
			else:
				pad_after = 0.3

		source_start = max(0.0, orig_start - pad_before)
		source_end = orig_end + pad_after

		if source_duration is not None:
			source_start = min(source_start, max(0.0, source_duration - 1.5))
			source_end = min(source_end, source_duration)

		clip_duration = max(1.5, source_end - source_start)
		remaining = max(0.0, max_duration - cursor)
		if remaining <= 0.0:
			break
		if clip_duration > remaining:
			source_end = source_start + remaining
			clip_duration = remaining
			pad_after = max(0.1, source_end - orig_end)

		if source_start < last_source_end:
			adjustment = last_source_end - source_start
			source_start += adjustment
			clip_duration = max(1.2, source_end - source_start)
			pad_before = max(0.0, orig_start - source_start)

		if clip_duration <= 0.75:
			continue
		if clip_duration <= 0:
			continue
		transition = rng.choice(["cut", "fade", "dip"])
		audio_cue = rng.choice(["rise", "drop", "sting", "motif"])
		pad_before_used = max(0.0, orig_start - source_start)
		pad_after_used = max(0.0, source_end - orig_end)
		timeline.append(
			{
				"sceneId": scene["sceneId"],
				"in": cursor,
				"out": cursor + clip_duration,
				"sourceStart": source_start,
				"sourceEnd": source_end,
				"handles": {
					"padBefore": round(pad_before_used, 2),
					"padAfter": round(pad_after_used, 2),
				},
				"transition": transition,
				"audioCue": audio_cue,
			}
		)
		cursor += clip_duration
		last_source_end = source_end

	return {
		"timeline": timeline,
		"renditions": renditions,
		"estimatedDuration": min(cursor, max_duration),
		"mixNotes": rng.sample(
			[
				"Accent hero theme under final VO",
				"Layer low percussion for tension",
				"Add crowd texture in stadium beat",
				"Emphasize dialogue reverb on reveal",
			],
			k=2,
		),
		"sourceDuration": source_duration,
	}


def _generate_deliverables_multivariant(
	job_id: str,
	rng: random.Random,
	assemblies: List[Dict[str, Any]],
	primary_assembly: Dict[str, Any],
	target_language: str,
	subtitle_language: str,
	include_captions: bool,
	include_storyboard: bool,
	video_path: Path,
	source_duration: Optional[float],
) -> Dict[str, Any]:
	"""Generate deliverables for multiple trailer variants."""
	primary_format = primary_assembly["renditions"][0]["format"]
	primary_ext = str(primary_format).lower()
	mime_map = {
		"mp4": "video/mp4",
		"mov": "video/quicktime",
		"m4v": "video/x-m4v",
		"webm": "video/webm",
	}
	
	deliverables: Dict[str, Any] = {}
	variants_list = []
	
	# Generate a trailer for each variant
	for idx, assembly in enumerate(assemblies):
		variant_name = assembly.get("variantName", f"Variant {idx + 1}")
		variant_key = variant_name.lower().replace(" ", "_")
		variant_path = OUTPUT_DIR / f"{job_id}_trailer_{variant_key}.{primary_ext}"
		
		# Render this variant
		ffmpeg_result = _render_trailer_ffmpeg(
			job_id=job_id,
			video_path=video_path,
			assembly=assembly,
			output_path=variant_path,
			source_duration=source_duration,
		)
		
		variant_entry = {
			"name": variant_name,
			"description": assembly.get("variantDescription", ""),
			"distribution": assembly.get("distribution", {}),
			"path": str(variant_path.relative_to(BASE_DIR)),
			"duration": assembly["estimatedDuration"],
			"format": primary_format,
			"mimeType": mime_map.get(primary_ext, "video/mp4"),
			"downloadUrl": f"/jobs/{job_id}/deliverables/variant_{idx + 1}",
			"sceneCount": len(assembly.get("timeline", [])),
		}
		
		if ffmpeg_result and variant_path.exists():
			variant_entry.update({
				"sizeBytes": ffmpeg_result.get("sizeBytes"),
				"note": ffmpeg_result.get("note", ""),
			})
		else:
			variant_entry["note"] = "FFmpeg unavailable—no trailer rendered."
			variant_entry.pop("downloadUrl", None)
		
		variants_list.append(variant_entry)
		deliverables[f"variant_{idx + 1}"] = variant_entry
	
	# Set the first variant as the master
	deliverables["master"] = variants_list[0] if variants_list else {
		"path": "",
		"note": "No variants generated",
	}
	
	# Generate captions for the primary variant
	if include_captions and assemblies:
		caption_path = OUTPUT_DIR / f"{job_id}.{subtitle_language}.vtt"
		caption_content = _mock_vtt(
			job_id=job_id, 
			language=subtitle_language, 
			timeline=assemblies[0].get("timeline", [])
		)
		caption_path.write_text(caption_content)
		deliverables["captions"] = {
			"path": str(caption_path.relative_to(BASE_DIR)),
			"language": subtitle_language,
			"mimeType": "text/vtt",
			"downloadUrl": f"/jobs/{job_id}/deliverables/captions",
		}
	
	# Generate storyboard for all variants
	if include_storyboard and assemblies:
		storyboard_path = OUTPUT_DIR / f"{job_id}_storyboard_all_variants.json"
		storyboard_payload = {
			"jobId": job_id,
			"variants": []
		}
		
		for idx, assembly in enumerate(assemblies):
			variant_frames = [
				{
					"sceneId": item["sceneId"],
					"in": item["in"],
					"out": item["out"],
					"sourceStart": item.get("sourceStart"),
					"sourceEnd": item.get("sourceEnd"),
					"handling": item.get("handles"),
					"description": rng.choice([
						"Hero sprinting through neon alley",
						"Family laughing during festival",
						"Mysterious figure revealed under rain",
						"Sunset embrace overlooking city skyline",
					]),
				}
				for item in assembly.get("timeline", [])
			]
			
			storyboard_payload["variants"].append({
				"name": assembly.get("variantName", f"Variant {idx + 1}"),
				"description": assembly.get("variantDescription", ""),
				"distribution": assembly.get("distribution", {}),
				"frames": variant_frames,
			})
		
		storyboard_path.write_text(json.dumps(storyboard_payload, indent=2))
		deliverables["storyboard"] = {
			"path": str(storyboard_path.relative_to(BASE_DIR)),
			"variantCount": len(assemblies),
			"mimeType": "application/json",
			"downloadUrl": f"/jobs/{job_id}/deliverables/storyboard",
		}
	
	deliverables["summary"] = {
		"targetLanguage": target_language,
		"subtitleLanguage": subtitle_language,
		"variantsGenerated": len(variants_list),
		"variants": variants_list,
	}
	
	return deliverables


def _generate_deliverables(
	job_id: str,
	rng: random.Random,
	assembly: Dict[str, Any],
	target_language: str,
	subtitle_language: str,
	include_captions: bool,
	include_storyboard: bool,
 	video_path: Path,
 	source_duration: Optional[float],
) -> Dict[str, Any]:
	primary_format = assembly["renditions"][0]["format"]
	primary_ext = str(primary_format).lower()
	master_path = OUTPUT_DIR / f"{job_id}_trailer.{primary_format}"
	mime_map = {
		"mp4": "video/mp4",
		"mov": "video/quicktime",
		"m4v": "video/x-m4v",
		"webm": "video/webm",
	}
	master_entry: Dict[str, Any] = {
		"path": str(master_path.relative_to(BASE_DIR)),
		"duration": assembly["estimatedDuration"],
		"format": primary_format,
		"note": "",
		"mimeType": mime_map.get(primary_ext, "video/mp4"),
	}
	deliverables: Dict[str, Any] = {"master": master_entry}

	if include_captions:
		caption_path = OUTPUT_DIR / f"{job_id}.{subtitle_language}.vtt"
		caption_content = _mock_vtt(job_id=job_id, language=subtitle_language, timeline=assembly["timeline"])
		caption_path.write_text(caption_content)
		deliverables["captions"] = {
			"path": str(caption_path.relative_to(BASE_DIR)),
			"language": subtitle_language,
			"mimeType": "text/vtt",
			"downloadUrl": f"/jobs/{job_id}/deliverables/captions",
		}

	if include_storyboard:
		storyboard_path = OUTPUT_DIR / f"{job_id}_storyboard.json"
		storyboard_payload = {
			"jobId": job_id,
			"frames": [
				{
					"sceneId": item["sceneId"],
					"in": item["in"],
					"out": item["out"],
					"sourceStart": item.get("sourceStart"),
					"sourceEnd": item.get("sourceEnd"),
					"handling": item.get("handles"),
					"description": rng.choice(
						[
							"Hero sprinting through neon alley",
							"Family laughing during festival",
							"Mysterious figure revealed under rain",
							"Sunset embrace overlooking city skyline",
						]
					),
				}
				for item in assembly["timeline"]
			],
		}
		storyboard_path.write_text(json.dumps(storyboard_payload, indent=2))
		deliverables["storyboard"] = {
			"path": str(storyboard_path.relative_to(BASE_DIR)),
			"frameCount": len(assembly["timeline"]),
			"mimeType": "application/json",
			"downloadUrl": f"/jobs/{job_id}/deliverables/storyboard",
		}

	ffmpeg_result = _render_trailer_ffmpeg(
		job_id=job_id,
		video_path=video_path,
		assembly=assembly,
		output_path=master_path,
		source_duration=source_duration,
	)
	if ffmpeg_result and master_path.exists():
		deliverables["master"].update(
			{
				"note": ffmpeg_result.get("note", ""),
				"sizeBytes": ffmpeg_result.get("sizeBytes"),
				"downloadUrl": f"/jobs/{job_id}/deliverables/master",
			}
		)
		if ffmpeg_result.get("hlsPlaylist"):
			deliverables["hls"] = {
				"path": str(ffmpeg_result["hlsPlaylist"].relative_to(BASE_DIR)),
				"variantCount": ffmpeg_result.get("hlsVariants", 0),
				"downloadUrl": f"/jobs/{job_id}/deliverables/hls",
			}
	else:
		deliverables["master"]["note"] = "FFmpeg unavailable—no trailer rendered."
		# Ensure no stale download URL is exposed if rendering fails
		deliverables["master"].pop("downloadUrl", None)

	deliverables["summary"] = {
		"targetLanguage": target_language,
		"subtitleLanguage": subtitle_language,
		"generatedAt": datetime.utcnow().isoformat() + "Z",
	}

	return deliverables
def _render_trailer_ffmpeg(
	job_id: str,
	video_path: Path,
	assembly: Dict[str, Any],
	output_path: Path,
	source_duration: Optional[float],
) -> Optional[Dict[str, Any]]:
	ffmpeg_bin = shutil.which("ffmpeg")
	if not ffmpeg_bin:
		return None

	timeline = list(assembly.get("timeline") or [])
	if not timeline:
		fallback_duration = float(assembly.get("estimatedDuration") or (source_duration or 30.0))
		if source_duration:
			fallback_duration = max(1.0, min(fallback_duration, float(source_duration)))
		else:
			fallback_duration = max(5.0, fallback_duration)
		timeline = [
			{
				"sceneId": "segment_1",
				"sourceStart": 0.0,
				"sourceEnd": fallback_duration,
			}
		]

	segments: List[Path] = []
	job_output_dir = OUTPUT_DIR / job_id
	segments_dir = job_output_dir / "segments"
	segments_dir.mkdir(parents=True, exist_ok=True)
	concat_file = job_output_dir / "concat.txt"
	output_path.parent.mkdir(parents=True, exist_ok=True)

	def _cleanup():
		for segment_file in segments:
			try:
				segment_file.unlink(missing_ok=True)
			except Exception:
				pass
		try:
			concat_file.unlink(missing_ok=True)
		except Exception:
			pass
		try:
			segments_dir.rmdir()
		except Exception:
			pass

	try:
		lines = []
		for index, clip in enumerate(timeline, start=1):
			source_start = float(clip.get("sourceStart", 0.0))
			source_end = float(clip.get("sourceEnd", source_start))
			if source_end <= source_start:
				source_end = source_start + max(0.5, float(clip.get("out", 1)) - float(clip.get("in", 0)))
			if source_duration:
				source_start = max(0.0, min(source_start, max(0.0, source_duration - 0.5)))
				source_end = min(source_duration, max(source_start + 0.5, source_end))
			duration = max(1.0, source_end - source_start)
			segment_path = segments_dir / f"segment_{index:02d}.mp4"
			fade_duration = min(0.6, max(0.15, duration / 4)) if duration > 1.2 else 0.0
			cmd = [
				ffmpeg_bin,
				"-hide_banner",
				"-loglevel",
				"error",
				"-y",
				"-ss",
				str(round(source_start, 3)),
				"-i",
				str(video_path),
				"-t",
				str(round(duration, 3)),
				"-c:v",
				"libx264",
				"-preset",
				"veryfast",
				"-crf",
				"20",
				"-c:a",
				"aac",
				"-b:a",
				"160k",
			]
			if fade_duration > 0:
				fade_out_start = max(fade_duration, duration - fade_duration)
				video_fade = f"fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}"
				audio_fade = f"afade=t=in:st=0:d={fade_duration:.3f},afade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}"
				cmd.extend(["-vf", video_fade, "-af", audio_fade])
			cmd.append(str(segment_path))
			subprocess.run(cmd, check=True)
			segments.append(segment_path)
			lines.append(f"file '{segment_path}'")

		concat_file.write_text("\n".join(lines))

		cmd_concat = [
			ffmpeg_bin,
			"-hide_banner",
			"-loglevel",
			"error",
			"-y",
			"-f",
			"concat",
			"-safe",
			"0",
			"-i",
			str(concat_file),
			"-c:v",
			"libx264",
			"-preset",
			"faster",
			"-crf",
			"18",
			"-c:a",
			"aac",
			"-b:a",
			"160k",
			str(output_path),
		]
		subprocess.run(cmd_concat, check=True)

		size_bytes = output_path.stat().st_size if output_path.exists() else None
		return {
			"note": "Rendered via FFmpeg fallback pipeline.",
			"sizeBytes": size_bytes,
		}
	except Exception:
		if output_path.exists():
			try:
				output_path.unlink()
			except Exception:
				pass
		return None
	finally:
		_cleanup()


def _mock_vtt(job_id: str, language: str, timeline: List[Dict[str, Any]]) -> str:
	lines = ["WEBVTT", ""]
	for index, clip in enumerate(timeline, start=1):
		start = _format_timestamp(clip["in"])
		end = _format_timestamp(clip["out"])
		lines.append(f"{index}")
		lines.append(f"{start} --> {end}")
		lines.append(f"[{language.upper()}] {clip['sceneId']} cue {index}")
		lines.append("")
	return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
	total_ms = max(0, int(round(float(seconds) * 1000)))
	hr_part, rem_ms = divmod(total_ms, 3_600_000)
	min_part, rem_ms = divmod(rem_ms, 60_000)
	sec_part, milli_part = divmod(rem_ms, 1_000)
	return f"{hr_part:02d}:{min_part:02d}:{sec_part:02d}.{milli_part:03d}"


def create_app() -> Flask:
	"""Factory compatible with Flask CLI and tests."""

	return _create_app()


# Default application for gunicorn or `python app.py`
app = _create_app()


__all__ = ["create_app", "app"]

