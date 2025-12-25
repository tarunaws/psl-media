from flask import Flask, request, render_template_string, send_from_directory, jsonify
import time
import os
from flask import jsonify
from PIL import Image
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import base64
import datetime
import uuid
import boto3
from botocore.client import Config
from shared.env_loader import load_environment

load_environment()

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

AWS_REGION = os.environ.get('AWS_REGION')
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting image creation service")

BEDROCK_REGION = os.environ.get('BEDROCK_REGION', AWS_REGION)
S3_REGION = os.environ.get('S3_REGION', AWS_REGION)
S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
IMAGE_MODEL_ID = os.environ.get('IMAGE_MODEL_ID', 'amazon.nova-canvas-v1:0')
IMAGE_WIDTH = int(os.environ.get('IMAGE_WIDTH', '1024'))
IMAGE_HEIGHT = int(os.environ.get('IMAGE_HEIGHT', '1024'))
IMAGE_CFG_SCALE = float(os.environ.get('IMAGE_CFG_SCALE', '8'))
IMAGE_QUALITY = os.environ.get('IMAGE_QUALITY', 'premium')
IMAGE_HISTORY_DIR = os.path.join(os.getcwd(), "history")

_session = boto3.session.Session()
_bedrock_client = None
_s3_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = _session.client('bedrock-runtime', region_name=BEDROCK_REGION)
    return _bedrock_client


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = _session.client('s3', region_name=S3_REGION, config=Config(signature_version='s3v4'))
    return _s3_client


def _extract_base64_image(payload: dict | list | None) -> str | None:
    if not payload:
        return None

    def _from_item(item):
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            for key in (
                'imageBase64', 'image', 'base64', 'image_b64',
                'bytesBase64Encoded', 'data', 'b64_json', 'imageData'
            ):
                value = item.get(key)
                if value:
                    return value
        return None

    if isinstance(payload, dict):
        for key in ('images', 'artifacts', 'data', 'outputs'):
            if key in payload and isinstance(payload[key], (list, tuple)):
                for entry in payload[key]:
                    candidate = _from_item(entry)
                    if candidate:
                        return candidate
        direct_candidate = _from_item(payload)
        if direct_candidate:
            return direct_candidate
    elif isinstance(payload, (list, tuple)):
        for entry in payload:
            candidate = _from_item(entry)
            if candidate:
                return candidate
    return None


def _invoke_bedrock(prompt: str) -> bytes:
    client = _get_bedrock_client()
    body = json.dumps({
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "cfgScale": IMAGE_CFG_SCALE,
            "quality": IMAGE_QUALITY
        }
    })

    response = client.invoke_model(
        modelId=IMAGE_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=body
    )

    payload = response.get('body')
    if hasattr(payload, 'read'):
        payload = payload.read()
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode('utf-8')
    if isinstance(payload, str):
        payload = json.loads(payload)

    image_base64 = _extract_base64_image(payload)
    if not image_base64:
        raise RuntimeError('No image returned from Bedrock response')

    try:
        return base64.b64decode(image_base64)
    except Exception as exc:
        raise RuntimeError('Failed to decode image bytes from Bedrock response') from exc


def _upload_to_s3(image_bytes: bytes) -> tuple[str | None, str | None]:
    if not S3_BUCKET:
        return None, None

    now = datetime.datetime.utcnow()
    folder = now.strftime('%Y-%m-%d/%H%M%S')
    key = f"moviePoster/{folder}_{uuid.uuid4().hex}.png"

    client = _get_s3_client()
    try:
        client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType='image/png'
        )

        url = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': S3_BUCKET, 'Key': key},
            ExpiresIn=3600
        )
        return key, url
    except Exception as exc:
        app.logger.warning("Failed to upload generated image to S3, falling back to local URL: %s", exc)
        return None, None


def _ensure_history_dir():
    os.makedirs(IMAGE_HISTORY_DIR, exist_ok=True)


def _save_history(image_bytes: bytes, timestamp: str) -> tuple[str, str]:
    _ensure_history_dir()
    subfolder = os.path.join(IMAGE_HISTORY_DIR, timestamp)
    os.makedirs(subfolder, exist_ok=True)

    original_path = os.path.join(subfolder, 'original.png')
    with open(original_path, 'wb') as f:
        f.write(image_bytes)

    thumbnail_path = os.path.join(subfolder, 'thumbnail.png')
    with Image.open(BytesIO(image_bytes)) as img:
        img.thumbnail((120, 120))
        img.save(thumbnail_path)

    return original_path, thumbnail_path

# ...existing code...

@app.route('/history_list', methods=['GET'])
def history_list():
    history_dir = IMAGE_HISTORY_DIR
    thumbs = []
    if os.path.exists(history_dir):
        server_url = request.host_url.rstrip('/')
        for folder in sorted(os.listdir(history_dir), reverse=True):
            thumb = os.path.join(history_dir, folder, "thumbnail.png")
            orig = os.path.join(history_dir, folder, "original.png")
            if os.path.exists(thumb) and os.path.exists(orig):
                thumbs.append({
                    "thumb": f"{server_url}/history/{folder}/thumbnail.png",
                    "orig": f"{server_url}/history/{folder}/original.png"
                })
    return jsonify(thumbs)

# ...existing code...

@app.route('/history/<path:filename>')
def history_file(filename):
    return send_from_directory(IMAGE_HISTORY_DIR, filename)

def _email_demo_mode_enabled() -> bool:
    allow_no_smtp = os.environ.get('CONTACT_ALLOW_NO_SMTP', 'true').lower() in ('1', 'true', 'yes')
    smtp_ready = all([
        os.environ.get('SMTP_HOST'),
        os.environ.get('SMTP_USER'),
        os.environ.get('SMTP_PASS')
    ])
    return (not smtp_ready) and allow_no_smtp

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "email_demo_mode": _email_demo_mode_enabled()
    })

@app.route('/contact_logs_list', methods=['GET'])
def contact_logs_list():
    log_dir = os.path.join(os.getcwd(), 'contact_logs')
    files = []
    if os.path.exists(log_dir):
        base = request.host_url.rstrip('/')
        for name in sorted(os.listdir(log_dir), reverse=True):
            path = os.path.join(log_dir, name)
            if os.path.isfile(path) and name.endswith('.json'):
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = None
                files.append({
                    'file': name,
                    'url': f"{base}/contact_logs/{name}",
                    'size': size
                })
    return jsonify(files)

@app.route('/contact_logs/<path:filename>')
def contact_logs_file(filename):
    log_dir = os.path.join(os.getcwd(), 'contact_logs')
    return send_from_directory(log_dir, filename)

def send_email(subject: str, body: str, to_addr: str, reply_to: str | None = None) -> None:
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    from_addr = os.environ.get('SMTP_FROM', smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError('SMTP not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, and optionally SMTP_FROM, CONTACT_TO env vars.')

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.attach(MIMEText(body, 'plain'))

    # Use STARTTLS by default (port 587); if 465 then use SSL
    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                # Require STARTTLS for common TLS ports like 587
                if smtp_port == 587:
                    server.starttls()
                    server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError("SMTP authentication failed. For Gmail, use an App Password if 2FA is enabled.") from e
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP error: {e}") from e

@app.route('/contact', methods=['POST'])
def contact_submit():
    data = request.get_json(silent=True) or {}
    required = ['firstName', 'lastName', 'email']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            'ok': False,
            'error': f"Missing required fields: {', '.join(missing)}"
        }), 400

    # Compose internal notification email
    internal_to = os.environ.get('CONTACT_TO', 'tarun_bhardwaj@persistent.com')
    submitter_email = data.get('email','')
    subject = f"Website Contact Form - {data.get('firstName','')} {data.get('lastName','')} ({data.get('company','')})"
    internal_lines = [
        "New contact form submission:",
        f"First Name: {data.get('firstName','')}",
        f"Last Name: {data.get('lastName','')}",
        f"Company: {data.get('company','')}",
        f"Email: {submitter_email}",
        f"Phone: {data.get('phone','')}",
        f"Country: {data.get('country','')}",
        "",
        "Comments:",
        data.get('comments','') or '-',
    ]
    internal_body = "\n".join(internal_lines)

    # Compose acknowledgment email to the submitter
    ack_subject = "We received your request"
    ack_lines = [
        f"Hi {data.get('firstName','')},",
        "",
        "Thanks for reaching out to Persistent Systems. We've received your request and will get back to you shortly.",
        "",
        "For your reference, here are the details you submitted:",
        f"Name: {data.get('firstName','')} {data.get('lastName','')}",
        f"Company: {data.get('company','')}",
        f"Email: {submitter_email}",
        f"Phone: {data.get('phone','')}",
        f"Country: {data.get('country','')}",
        "Comments:",
        data.get('comments','') or '-',
        "",
        "— Persistent Systems",
    ]
    ack_body = "\n".join(ack_lines)

    # If SMTP isn't configured, optionally allow a dev fallback to log instead of emailing
    allow_no_smtp = os.environ.get('CONTACT_ALLOW_NO_SMTP', 'true').lower() in ('1', 'true', 'yes')
    smtp_ready = all([
        os.environ.get('SMTP_HOST'),
        os.environ.get('SMTP_USER'),
        os.environ.get('SMTP_PASS')
    ])

    if not smtp_ready and allow_no_smtp:
        # Log the submission to a local file and return success for dev/demo
        try:
            log_dir = os.path.join(os.getcwd(), 'contact_logs')
            os.makedirs(log_dir, exist_ok=True)
            ts = str(int(time.time()))
            log_path = os.path.join(log_dir, f'{ts}.json')
            with open(log_path, 'w') as f:
                json.dump({
                    'internal': {'to': internal_to, 'subject': subject, 'body': internal_body},
                    'ack': {'to': submitter_email, 'subject': ack_subject, 'body': ack_body},
                    'data': data
                }, f, indent=2)
            return jsonify({'ok': True, 'message': 'Received (dev mode): email not sent, saved to contact_logs'}), 200
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Failed to log contact: {e}'}), 500

    try:
        # Send internal notification (reply-to set to submitter)
        send_email(subject, internal_body, internal_to, reply_to=submitter_email or None)
        # Send acknowledgment to the submitter (reply-to set to CONTACT_TO)
        reply_to_contact = internal_to if internal_to else None
        if submitter_email:
            send_email(ack_subject, ack_body, submitter_email, reply_to=reply_to_contact)
        return jsonify({'ok': True, 'message': 'Submitted successfully'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

html_template = """
<!doctype html>
<html>
<head>
    <title>Media and Entertainment Demo</title>
    <style>
        body {
            background: linear-gradient(135deg, #232526 0%, #000000 100%);
            color: #fff;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            margin: 0;
            min-height: 100vh;
        }
        .header {
            text-align: center;
            margin-top: 40px;
            margin-bottom: 10px;
        }
        .title {
            font-size: 2.5em;
            font-weight: bold;
            letter-spacing: 2px;
            color: #fff;
            margin-bottom: 8px;
        }
        .subtitle {
            color: orange;
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 24px;
        }
        .main-container {
            display: flex;
            flex-direction: row;
            width: 100%;
            min-height: 400px;
            box-sizing: border-box;
        }
        .prompt-section {
            flex: 1;
            padding: 40px 20px 20px 40px;
        }
        .image-section {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 40px 40px 20px 20px;
            min-height: 400px;
        }
        textarea[name="prompt"] {
            width: 98%;
            height: 180px;
            font-size: 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            margin-bottom: 16px;
            background: #222;
            color: #fff;
            resize: vertical;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(255,140,0,0.15);
        }
        input[type="submit"], button {
            padding: 6px 18px;
            font-size: 14px;
            border-radius: 8px;
            border: none;
            background: linear-gradient(90deg, orange 0%, #ff9800 100%);
            color: #fff;
            cursor: pointer;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(255,140,0,0.15);
        }
        input[type="submit"]:hover, button:hover {
            background: linear-gradient(90deg, #ff9800 0%, orange 100%);
        }
        h2 {
            color: #fff;
        }
        .image-section img {
            max-width: 68%;
            max-height: 490px;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(255,140,0,0.25);
            border: 2px solid orange;
        }
    </style>
 </head>
 <body>
    <div class="header">
        <div class="title">Media and Entertainment Demo</div>
        <div class="subtitle">Persistent System Limited</div>
    </div>
    <div class="main-container">
        <!-- Left side: Prompt input -->
        <div class="prompt-section">
            <h2>Enter your prompt</h2>
            <form action="/send_prompt" method="post">
                <textarea name="prompt" required>{{ default_prompt }}</textarea>
                <input type="submit" value="Send">
            </form>
            <form action="/" method="get" style="margin-top:20px;">
                <button type="submit">Refresh / Add New Prompt</button>
            </form>
        </div>
        <!-- Right side: Image -->
        <div class="image-section">
            {% if image_url %}
                <div style="width:100%; text-align:center;">
                    <a href="{{ image_url }}" download style="display:inline-block; margin-bottom:8px; color:orange; font-size:16px; font-weight:600; text-decoration:none; background:#222; padding:8px 18px; border-radius:8px; border:2px solid orange;">Download Image</a>
                    <div style="margin-bottom:18px; color:#fff; font-size:15px; font-weight:500;">Total time taken: {{ total_time }} seconds</div>
                </div>
                <img src="{{ image_url }}" alt="API Response Image">
            {% endif %}
        </div>
    </div>
 </body>
 </html>
"""

@app.route('/', methods=['GET'])
def index():
    # On reload, show blank prompt input and no default image
    return render_template_string(
        html_template,
        default_prompt="",
        image_url="",
        total_time=""
    )

@app.route('/send_prompt', methods=['POST'])
def send_prompt():
    import time as _time
    start_time = _time.time()
    data = request.get_json(silent=True) or {}
    prompt = (
        (data.get('prompt') if isinstance(data, dict) else None)
        or request.form.get('prompt')
        or request.values.get('prompt')
        or ''
    ).strip()

    def _wants_html_response() -> bool:
        if request.is_json:
            return False
        accept = (request.headers.get('Accept') or '').lower()
        if 'application/json' in accept and 'text/html' not in accept:
            return False
        return True

    if not prompt:
        if _wants_html_response():
            return render_template_string(
                html_template,
                default_prompt="",
                image_url="",
                total_time="",
                error="Prompt is required",
            ), 400
        return jsonify({'image_url': '', 'total_time': 0, 'error': 'Prompt is required'}), 400

    timestamp = str(int(start_time))
    try:
        app.logger.info(
            "Invoking Bedrock image model %s (region=%s) for prompt (%d chars)",
            IMAGE_MODEL_ID,
            BEDROCK_REGION,
            len(prompt)
        )
        image_bytes = _invoke_bedrock(prompt)
        _save_history(image_bytes, timestamp)

        s3_key, presigned_url = _upload_to_s3(image_bytes)
        total_time = _time.time() - start_time

        if presigned_url:
            image_url = presigned_url
        else:
            image_url = f"{request.host_url.rstrip('/')}/history/{timestamp}/original.png"

        response_payload = {
            'image_url': image_url,
            'total_time': round(total_time, 2),
            'prompt': prompt
        }
        if s3_key:
            response_payload['s3_key'] = s3_key

        if _wants_html_response():
            return render_template_string(
                html_template,
                default_prompt=prompt,
                image_url=image_url,
                total_time=response_payload['total_time'],
                error="",
            )
        return jsonify(response_payload)
    except Exception as exc:
        total_time = _time.time() - start_time
        if _wants_html_response():
            return render_template_string(
                html_template,
                default_prompt=prompt,
                image_url="",
                total_time=round(total_time, 2),
                error=str(exc),
            ), 500
        return jsonify({
            'image_url': '',
            'total_time': round(total_time, 2),
            'error': str(exc),
            'prompt': prompt
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', '5002'))
    debug_flag = os.environ.get('DEBUG', 'false').lower() == 'true'
    use_reloader = os.environ.get('RELOADER', 'false').lower() == 'true'
    print(f"Starting Image Creation Service on port {port} (debug={debug_flag})")
    # Run threaded and without reloader by default to prevent duplicate listeners in background runs
    app.run(debug=debug_flag, host="0.0.0.0", port=port, threaded=True, use_reloader=use_reloader)
