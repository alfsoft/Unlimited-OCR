from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import os
import json
import base64
import tempfile
import threading
import time
import uuid
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from functools import wraps
from datetime import datetime
import hashlib

app = Flask(__name__)
CORS(app)

# Log all requests for debugging
@app.before_request
def log_request_info():
    print(f"[API] >>> {request.method} {request.path} from {request.remote_addr}")
    if request.args:
        print(f"[API] Query params: {dict(request.args)}")
    if request.content_type:
        print(f"[API] Content-Type: {request.content_type}")

@app.after_request
def log_response_info(response):
    print(f"[API] <<< {response.status_code} for {request.method} {request.path}")
    return response

@app.errorhandler(404)
def not_found_error(error):
    print(f"[API] ERROR 404: Route not found - {request.method} {request.path}")
    print(f"[API] Available routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
    return jsonify({'error': 'Not Found', 'path': request.path, 'method': request.method}), 404

UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/outputs'
CONFIG_FILE = '/app/config/llm_config.json'

# Global job tracking
jobs = {}
job_lock = threading.Lock()

# LLM Provider Configuration
class LLMConfig:
    def __init__(self):
        self.providers = {
            'sglang': {
                'name': 'SGLang',
                'url': 'http://127.0.0.1:10000',
                'model': 'Unlimited-OCR',
                'enabled': True,
                'api_type': 'openai_compat',
                'prompt': 'document parsing.',
                'temperature': 0,
                'timeout': 1200,
                'max_retries': 3,
                'supports_images': True,
                'custom_params': {
                    'no_repeat_ngram_size': 35,
                    'ngram_window': 128,
                    'image_mode': 'gundam'
                }
            },
            'llamacpp': {
                'name': 'llama.cpp',
                'url': 'http://host.docker.internal:8080',
                'model': '',  # Auto-detected
                'enabled': False,
                'api_type': 'openai_compat',
                'prompt': 'Extract all text from this document image accurately. Preserve formatting, line breaks, and structure.',
                'temperature': 0.1,
                'timeout': 300,
                'max_retries': 3,
                'supports_images': True,
                'custom_params': {
                    'max_tokens': 4096,
                    'stop': []
                }
            },
            'ollama': {
                'name': 'Ollama',
                'url': 'http://host.docker.internal:11434',
                'model': 'llava',  # Default vision model
                'enabled': False,
                'api_type': 'ollama',
                'prompt': 'Extract all text from this document image accurately. Preserve formatting, line breaks, and structure.',
                'temperature': 0.1,
                'timeout': 300,
                'max_retries': 3,
                'supports_images': True,
                'custom_params': {
                    'num_predict': 4096,
                    'keep_alive': '5m'
                }
            }
        }
        self.active_provider = 'sglang'
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                print(f"[CONFIG] Loading configuration from {CONFIG_FILE}")
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if 'providers' in data:
                        for key, config in data['providers'].items():
                            if key in self.providers:
                                self.providers[key].update(config)
                                print(f"[CONFIG] Updated provider '{key}' settings")
                    if 'active_provider' in data:
                        self.active_provider = data['active_provider']
                        print(f"[CONFIG] Active provider set to: {self.active_provider}")
                print(f"[CONFIG] Configuration loaded successfully")
            else:
                print(f"[CONFIG] Config file not found at {CONFIG_FILE}, using defaults")
        except Exception as e:
            print(f"[CONFIG] ERROR loading config: {e}")
            import traceback
            print(f"[CONFIG] Stack trace: {traceback.format_exc()}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            data = {
                'providers': self.providers,
                'active_provider': self.active_provider
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[CONFIG] Configuration saved to {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"[CONFIG] ERROR saving config: {e}")
            import traceback
            print(f"[CONFIG] Stack trace: {traceback.format_exc()}")
            return False
    
    def get_active_config(self):
        """Get current active provider config"""
        return self.providers.get(self.active_provider, self.providers['sglang'])
    
    def test_connection(self, provider_key=None):
        """Test connection to LLM provider"""
        if provider_key is None:
            provider_key = self.active_provider
        
        config = self.providers.get(provider_key)
        if not config:
            print(f"[LLM] ERROR: Provider '{provider_key}' not found")
            return {'success': False, 'error': 'Provider not found'}
        
        print(f"[LLM] Testing connection to {config['name']} at {config['url']}")
        
        try:
            if config['api_type'] == 'ollama':
                # Test Ollama connection
                print(f"[LLM] Sending GET request to {config['url']}/api/tags")
                resp = requests.get(f"{config['url']}/api/tags", timeout=10)
                print(f"[LLM] Response status code: {resp.status_code}")
                resp.raise_for_status()
                models = resp.json().get('models', [])
                print(f"[LLM] Connected to Ollama. Found {len(models)} models: {', '.join([m['name'] for m in models[:5]])}{'...' if len(models) > 5 else ''}")
                return {
                    'success': True,
                    'models': [m['name'] for m in models],
                    'message': f"Connected to Ollama. Found {len(models)} models."
                }
            else:
                # Test OpenAI-compatible API (llama.cpp, SGLang)
                print(f"[LLM] Sending GET request to {config['url']}/v1/models")
                resp = requests.get(f"{config['url']}/v1/models", timeout=10)
                print(f"[LLM] Response status code: {resp.status_code}")
                resp.raise_for_status()
                models_data = resp.json()
                models = []
                if 'data' in models_data:
                    models = [m.get('id', '') for m in models_data['data']]
                print(f"[LLM] Connected to {config['name']}. Found {len(models)} models: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}")
                return {
                    'success': True,
                    'models': models,
                    'message': f"Connected to {config['name']}. Found {len(models)} models."
                }
        except requests.exceptions.Timeout as e:
            error_msg = f"Connection timeout after 10s"
            print(f"[LLM] ERROR: {error_msg} for {config['name']}")
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            print(f"[LLM] ERROR: {error_msg} for {config['name']}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[LLM] ERROR: {error_msg} for {config['name']}")
            import traceback
            print(f"[LLM] Stack trace: {traceback.format_exc()}")
            return {'success': False, 'error': error_msg}

llm_config = LLMConfig()

def get_ngram_processor_str():
    try:
        print("[OCR] Loading ngram processor from sglang...")
        from sglang.srt.sampling.custom_logit_processor import DeepseekOCRNoRepeatNGramLogitProcessor
        result = DeepseekOCRNoRepeatNGramLogitProcessor.to_str()
        print("[OCR] Ngram processor loaded successfully")
        return result
    except Exception as e:
        print(f"[OCR] ERROR loading ngram processor: {e}")
        import traceback
        print(f"[OCR] Stack trace: {traceback.format_exc()}")
        return None

def pdf_to_images(pdf_path, dpi=300):
    """Convert PDF to images"""
    try:
        print(f"[OCR] Converting PDF to images: {pdf_path} (dpi={dpi})")
        doc = fitz.open(pdf_path)
        tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
        image_paths = []
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for i, page in enumerate(doc):
            out_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
            page.get_pixmap(matrix=mat).save(out_path)
            image_paths.append(out_path)
            print(f"[OCR] Converted page {i + 1}/{len(doc)}")
        doc.close()
        print(f"[OCR] PDF converted to {len(image_paths)} images at {tmp_dir}")
        return image_paths
    except Exception as e:
        print(f"[OCR] ERROR converting PDF to images: {e}")
        import traceback
        print(f"[OCR] Stack trace: {traceback.format_exc()}")
        raise

def encode_image(image_path):
    """Encode image to base64"""
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

def build_content(image_path):
    """Build content for API request"""
    return [{"type": "text", "text": PROMPT}, encode_image(image_path)]

def infer_single(image_path, output_file, job_id, idx, total, provider_config=None):
    """Perform OCR on a single image"""
    # Use provider_config if available, otherwise use global variables
    if provider_config is None:
        server_url = SERVER_URL
        model_name = SERVED_MODEL_NAME
        temperature = TEMPERATURE
        max_retries = MAX_RETRIES
        request_timeout = REQUEST_TIMEOUT
        no_repeat_ngram_size = NO_REPEAT_NGRAM_SIZE
        ngram_window = NGRAM_WINDOW
    else:
        server_url = provider_config.get('url', SERVER_URL)
        model_name = provider_config.get('model', SERVED_MODEL_NAME)
        temperature = provider_config.get('temperature', TEMPERATURE)
        max_retries = provider_config.get('max_retries', MAX_RETRIES)
        request_timeout = provider_config.get('timeout', REQUEST_TIMEOUT)
        no_repeat_ngram_size = provider_config.get('custom_params', {}).get('no_repeat_ngram_size', NO_REPEAT_NGRAM_SIZE)
        ngram_window = provider_config.get('custom_params', {}).get('ngram_window', NGRAM_WINDOW)
    
    print(f"[OCR] Starting inference for file {idx}/{total}: {os.path.basename(image_path)}")
    print(f"[OCR] Server URL: {server_url}, Model: {model_name}, Temperature: {temperature}")
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": build_content(image_path)}],
        "temperature": temperature,
        "skip_special_tokens": False,
        "stream": True,
        "images_config": {"image_mode": "gundam"},
    }
    if no_repeat_ngram_size > 0 and ngram_window > 0:
        payload["custom_logit_processor"] = get_ngram_processor_str()
        payload["custom_params"] = {
            "ngram_size": no_repeat_ngram_size,
            "window_size": ngram_window,
        }
        print(f"[OCR] Using ngram processor: size={no_repeat_ngram_size}, window={ngram_window}")

    name = os.path.basename(image_path)
    result_text = ""
    
    for attempt in range(max_retries):
        try:
            print(f"[OCR] Attempt {attempt + 1}/{max_retries} for {name}")
            print(f"[OCR] Sending POST request to {server_url}/v1/chat/completions")
            
            resp = requests.post(
                f"{server_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=request_timeout,
                stream=True,
            )
            
            print(f"[OCR] Response status code: {resp.status_code}")
            
            if resp.status_code == 502 and attempt < max_retries - 1:
                print(f"[OCR] Got 502 Bad Gateway, retrying...")
                continue
            
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        result_text += delta
                        # Update progress
                        with job_lock:
                            if job_id in jobs:
                                jobs[job_id]['progress']['current'] = idx
                                jobs[job_id]['progress']['output'][idx-1] = result_text
                                jobs[job_id]['progress']['last_updated'] = datetime.utcnow().isoformat()
                except Exception as parse_error:
                    print(f"[OCR] Error parsing response chunk: {parse_error}")
                    print(f"[OCR] Raw chunk data: {line[:200]}")
                    continue
            
            # Save result
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                print(f"[OCR] Result saved to {output_file}")
            
            print(f"[OCR] Successfully processed {name}, text length: {len(result_text)}")
            return {"success": True, "text": result_text}
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout after {request_timeout}s"
            print(f"[OCR] ERROR: {error_msg} for {name}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue
            return {"success": False, "error": error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            print(f"[OCR] ERROR: {error_msg} for {name}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            return {"success": False, "error": error_msg}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {resp.status_code}: {str(e)}"
            print(f"[OCR] ERROR: {error_msg} for {name}")
            print(f"[OCR] Response body: {resp.text[:500] if resp else 'N/A'}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[OCR] ERROR: {error_msg} for {name}")
            import traceback
            print(f"[OCR] Stack trace: {traceback.format_exc()}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            return {"success": False, "error": error_msg}
    
    print(f"[OCR] Max retries ({max_retries}) exceeded for {name}")
    return {"success": False, "error": "Max retries exceeded"}

def process_documents(job_id, files, output_format='txt', provider_config=None):
    """Process multiple documents with full error handling"""
    global jobs
    
    if provider_config is None:
        provider_config = llm_config.get_active_config()
    
    with job_lock:
        jobs[job_id] = {
            'status': 'processing',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'files': files,
            'output_format': output_format,
            'provider': provider_config['name'],
            'progress': {
                'total': len(files),
                'current': 0,
                'status': 'processing',
                'output': [''] * len(files),
                'errors': [],
                'last_updated': datetime.utcnow().isoformat()
            },
            'results': None
        }
    
    results = []
    errors = []
    
    for idx, file_info in enumerate(files, 1):
        file_path = file_info['path']
        filename = file_info['name']
        
        try:
            # Determine output file
            output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # Check if PDF
            if file_path.lower().endswith('.pdf'):
                print(f"[OCR] Processing PDF: {filename}, converting to images...")
                try:
                    images = pdf_to_images(file_path)
                    print(f"[OCR] PDF converted to {len(images)} pages")
                except Exception as pdf_error:
                    error_msg = f"Failed to convert PDF to images: {str(pdf_error)}"
                    print(f"[OCR] ERROR: {error_msg}")
                    errors.append({
                        'file': filename,
                        'error': error_msg
                    })
                    continue
                
                page_results = []
                for img_idx, img_path in enumerate(images, 1):
                    print(f"[OCR] Processing PDF page {img_idx}/{len(images)} from {filename}")
                    result = infer_single(img_path, None, job_id, idx, len(files), provider_config)
                    if result['success']:
                        page_results.append(result['text'])
                    else:
                        error_detail = result.get('error', 'Unknown error')
                        print(f"[OCR] ERROR processing page {img_idx}: {error_detail}")
                        errors.append({
                            'file': f"{filename}_page_{img_idx}",
                            'error': error_detail
                        })
                
                if page_results:
                    combined_text = '\n\n'.join(page_results)
                    results.append({
                        'file': filename,
                        'text': combined_text,
                        'pages': len(images)
                    })
                    
                    # Save combined result
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(combined_text)
                    print(f"[OCR] PDF result saved to {output_path}")
            else:
                print(f"[OCR] Processing image: {filename}")
                result = infer_single(file_path, output_path, job_id, idx, len(files), provider_config)
                if result['success']:
                    results.append({
                        'file': filename,
                        'text': result['text']
                    })
                    print(f"[OCR] Image processed successfully: {filename}")
                else:
                    error_detail = result.get('error', 'Unknown error')
                    print(f"[OCR] ERROR processing image {filename}: {error_detail}")
                    errors.append({
                        'file': filename,
                        'error': error_detail
                    })
        except Exception as e:
            import traceback
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            print(f"[OCR] ERROR processing file {filename}: {error_msg}")
            print(f"[OCR] Stack trace: {stack_trace}")
            errors.append({
                'file': filename,
                'error': error_msg
            })
    
    with job_lock:
        jobs[job_id]['status'] = 'completed' if not errors else 'completed_with_errors'
        jobs[job_id]['updated_at'] = datetime.utcnow().isoformat()
        jobs[job_id]['progress']['status'] = jobs[job_id]['status']
        jobs[job_id]['progress']['errors'] = errors
        jobs[job_id]['results'] = {
            'success': results,
            'errors': errors
        }
    
    return {'success': results, 'errors': errors}


def format_output(data, output_format):
    """Format output data in different formats"""
    if output_format == 'json':
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    elif output_format == 'csv':
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['file', 'text'])
        for item in data.get('success', []):
            writer.writerow([item.get('file', ''), item.get('text', '')])
        return output.getvalue()
    
    elif output_format == 'html':
        html = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='UTF-8'>\n<title>OCR Results</title>\n<style>\nbody { font-family: Arial, sans-serif; margin: 20px; }\n.document { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }\n.filename { font-weight: bold; color: #333; }\n.content { white-space: pre-wrap; background: #f9f9f9; padding: 10px; margin-top: 10px; }\n.error { color: red; }\n</style>\n</head>\n<body>\n<h1>OCR Results</h1>\n"
        for item in data.get('success', []):
            html += f"<div class='document'>\n<div class='filename'>{item.get('file', '')}</div>\n<div class='content'>{item.get('text', '')}</div>\n</div>\n"
        for error in data.get('errors', []):
            html += f"<div class='document error'>Error processing {error.get('file', '')}: {error.get('error', '')}</div>\n"
        html += "</body>\n</html>"
        return html
    
    else:  # txt
        text_output = ""
        for item in data.get('success', []):
            text_output += f"=== {item.get('file', '')} ===\n\n{item.get('text', '')}\n\n"
        for error in data.get('errors', []):
            text_output += f"ERROR: {error.get('file', '')} - {error.get('error', '')}\n"
        return text_output


def api_response(success=True, data=None, error=None, status_code=200):
    """Standard API response formatter"""
    response = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat()
    }
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    return jsonify(response), status_code


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads (legacy endpoint for web UI)"""
    print(f"[API] Received upload request from {request.remote_addr}")
    
    if 'files' not in request.files:
        print(f"[API] ERROR: No files in request")
        return api_response(success=False, error='No files provided'), 400
    
    files = request.files.getlist('files')
    output_format = request.form.get('format', 'txt')
    print(f"[API] Received {len(files)} files, format: {output_format}")
    
    saved_files = []
    for file in files:
        if file.filename:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            try:
                file.save(filepath)
                saved_files.append({
                    'name': file.filename,
                    'path': filepath
                })
                print(f"[API] Saved file: {file.filename} -> {filepath}")
            except Exception as e:
                print(f"[API] ERROR saving file {file.filename}: {e}")
    
    if not saved_files:
        print(f"[API] ERROR: No valid files saved")
        return api_response(success=False, error='No valid files'), 400
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    print(f"[API] Generated job ID: {job_id}")
    
    # Get active provider config
    provider_config = llm_config.get_active_config()
    print(f"[API] Using provider: {provider_config['name']}")
    
    # Start processing in background
    thread = threading.Thread(target=process_documents, args=(job_id, saved_files, output_format, provider_config))
    thread.start()
    print(f"[API] Started background processing thread for job {job_id}")
    
    return jsonify({
        'job_id': job_id,
        'message': f'Processing {len(saved_files)} file(s)',
        'files': [f['name'] for f in saved_files],
        'provider': provider_config['name']
    })


# ============================================================================
# PROFESSIONAL API ENDPOINTS FOR EXTERNAL APPLICATIONS
# ============================================================================

@app.route('/api/v1/ocr/submit', methods=['POST'])
def submit_ocr_job():
    """
    Submit OCR job for processing.
    
    Accepts: multipart/form-data or application/json
    Returns: job_id for tracking progress
    
    Example curl:
    curl -X POST http://localhost:5000/api/v1/ocr/submit \
      -F "files=@document1.pdf" -F "files=@document2.png" \
      -F "output_format=json" -F "priority=normal"
    """
    try:
        print(f"[API] Received OCR submit request from {request.remote_addr}")
        
        # Handle both JSON and form-data
        if request.is_json:
            print(f"[API] Processing JSON request")
            data = request.get_json()
            output_format = data.get('output_format', 'txt')
            priority = data.get('priority', 'normal')
            options = data.get('options', {})
            files_data = data.get('files', [])  # Base64 encoded files
            saved_files = []
            
            for file_data in files_data:
                filename = file_data.get('filename', 'unknown')
                content = file_data.get('content')  # base64
                if content:
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    with open(filepath, 'wb') as f:
                        f.write(base64.b64decode(content))
                    saved_files.append({'name': filename, 'path': filepath})
                    print(f"[API] Decoded and saved file: {filename}")
        else:
            print(f"[API] Processing form-data request")
            if 'files' not in request.files:
                print(f"[API] ERROR: No files in request")
                return api_response(success=False, error='No files provided'), 400
            
            files = request.files.getlist('files')
            output_format = request.form.get('output_format', 'txt')
            priority = request.form.get('priority', 'normal')
            options = {}
            print(f"[API] Received {len(files)} files, format: {output_format}, priority: {priority}")
            
            saved_files = []
            for file in files:
                if file.filename:
                    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                    try:
                        file.save(filepath)
                        saved_files.append({
                            'name': file.filename,
                            'path': filepath
                        })
                        print(f"[API] Saved file: {file.filename} -> {filepath}")
                    except Exception as e:
                        print(f"[API] ERROR saving file {file.filename}: {e}")
        
        if not saved_files:
            print(f"[API] ERROR: No valid files saved")
            return api_response(success=False, error='No valid files provided'), 400
        
        # Validate output format
        valid_formats = ['txt', 'csv', 'json', 'html']
        if output_format not in valid_formats:
            print(f"[API] ERROR: Invalid format '{output_format}'")
            return api_response(success=False, error=f'Invalid format. Choose from: {valid_formats}'), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        print(f"[API] Generated job ID: {job_id}")
        
        # Get provider config - can be overridden via request
        provider_key = request.form.get('provider', options.get('provider', None)) if not request.is_json else data.get('provider', None)
        if provider_key and provider_key in llm_config.providers:
            provider_config = llm_config.providers[provider_key]
            print(f"[API] Using specified provider: {provider_key}")
        else:
            provider_config = llm_config.get_active_config()
            print(f"[API] Using default provider: {provider_config['name']}")
        
        # Create job record
        with job_lock:
            jobs[job_id] = {
                'status': 'queued',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'files': saved_files,
                'output_format': output_format,
                'priority': priority,
                'options': options,
                'provider': provider_config['name'],
                'progress': {
                    'total': len(saved_files),
                    'current': 0,
                    'status': 'queued',
                    'output': [''] * len(saved_files),
                    'errors': [],
                    'last_updated': datetime.utcnow().isoformat()
                },
                'results': None
            }
        print(f"[API] Created job record for {job_id}")
        
        # Start processing in background
        thread = threading.Thread(target=process_documents, args=(job_id, saved_files, output_format, provider_config))
        thread.daemon = True
        thread.start()
        print(f"[API] Started background processing for job {job_id}")
        
        return api_response(success=True, data={
            'job_id': job_id,
            'status': 'queued',
            'files_count': len(saved_files),
            'output_format': output_format,
            'provider': provider_config['name'],
            'estimated_time_seconds': len(saved_files) * 30  # Rough estimate
        }), 202
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        print(f"[API] ERROR submitting OCR job: {error_msg}")
        print(f"[API] Stack trace: {stack_trace}")
        return api_response(success=False, error=error_msg), 500


@app.route('/api/v1/ocr/status/<job_id>', methods=['GET'])
def get_ocr_status(job_id):
    """
    Get OCR job status and progress.
    
    Returns: Current job status, progress percentage, and any errors
    
    Example curl:
    curl http://localhost:5000/api/v1/ocr/status/550e8400-e29b-41d4-a716-446655440000
    """
    with job_lock:
        if job_id not in jobs:
            return api_response(success=False, error='Job not found'), 404
        
        job = jobs[job_id]
        progress = job['progress']
        
        # Calculate progress percentage
        total = progress['total']
        current = progress['current']
        progress_percent = int((current / total) * 100) if total > 0 else 0
        
        return api_response(success=True, data={
            'job_id': job_id,
            'status': job['status'],
            'created_at': job['created_at'],
            'updated_at': job['updated_at'],
            'output_format': job['output_format'],
            'progress': {
                'total_files': total,
                'processed_files': current,
                'percent_complete': progress_percent,
                'errors_count': len(progress.get('errors', []))
            },
            'errors': progress.get('errors', [])
        })


@app.route('/api/v1/ocr/result/<job_id>', methods=['GET'])
def get_ocr_result(job_id):
    """
    Get OCR job results.
    
    Query params:
      - format: Override output format (txt, csv, json, html)
      - download: If true, returns file attachment
    
    Example curl:
    curl http://localhost:5000/api/v1/ocr/result/550e8400-e29b-41d4-a716-446655440000?format=json
    """
    with job_lock:
        if job_id not in jobs:
            return api_response(success=False, error='Job not found'), 404
        
        job = jobs[job_id]
        
        if job['status'] == 'queued' or job['status'] == 'processing':
            return api_response(success=False, error='Job not completed yet', data={'status': job['status']}), 202
        
        if job['results'] is None:
            return api_response(success=False, error='No results available'), 404
        
        # Get requested format
        requested_format = request.args.get('format', job['output_format'])
        
        # Format the output
        formatted_output = format_output(job['results'], requested_format)
        
        # Check if download requested
        if request.args.get('download', 'false').lower() == 'true':
            return Response(
                formatted_output,
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="ocr_results.{requested_format}"'
                }
            )
        
        # Return appropriate content type
        content_types = {
            'json': 'application/json',
            'csv': 'text/csv',
            'html': 'text/html',
            'txt': 'text/plain'
        }
        
        return Response(
            formatted_output,
            mimetype=content_types.get(requested_format, 'text/plain')
        )


@app.route('/api/v1/ocr/stream/<job_id>', methods=['GET'])
def stream_ocr_result(job_id):
    """
    Stream OCR results as they become available (Server-Sent Events).
    
    Returns: SSE stream with progress updates and final results
    
    Example curl:
    curl -N http://localhost:5000/api/v1/ocr/stream/550e8400-e29b-41d4-a716-446655440000
    """
    def generate():
        last_progress = -1
        
        while True:
            with job_lock:
                if job_id not in jobs:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                    return
                
                job = jobs[job_id]
                progress = job['progress']
                current_progress = progress['current']
                
                # Send progress update if changed
                if current_progress != last_progress:
                    last_progress = current_progress
                    event_data = {
                        'type': 'progress',
                        'job_id': job_id,
                        'status': job['status'],
                        'current': current_progress,
                        'total': progress['total'],
                        'percent': int((current_progress / progress['total']) * 100) if progress['total'] > 0 else 0
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Send results when complete
                if job['status'] in ['completed', 'completed_with_errors']:
                    event_data = {
                        'type': 'complete',
                        'job_id': job_id,
                        'status': job['status'],
                        'results': job['results']
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    break
                
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            time.sleep(1)
        
        yield "data: [DONE]\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/v1/ocr/cancel/<job_id>', methods=['POST'])
def cancel_ocr_job(job_id):
    """
    Cancel an OCR job.
    
    Note: Only works for queued jobs, processing jobs cannot be cancelled
    
    Example curl:
    curl -X POST http://localhost:5000/api/v1/ocr/cancel/550e8400-e29b-41d4-a716-446655440000
    """
    with job_lock:
        if job_id not in jobs:
            return api_response(success=False, error='Job not found'), 404
        
        job = jobs[job_id]
        
        if job['status'] == 'processing':
            return api_response(success=False, error='Cannot cancel job that is already processing'), 409
        
        if job['status'] in ['completed', 'completed_with_errors']:
            return api_response(success=False, error='Job already completed'), 409
        
        job['status'] = 'cancelled'
        job['updated_at'] = datetime.utcnow().isoformat()
        job['progress']['status'] = 'cancelled'
        
        return api_response(success=True, data={
            'job_id': job_id,
            'status': 'cancelled'
        })


@app.route('/api/v1/ocr/list', methods=['GET'])
def list_ocr_jobs():
    """
    List all OCR jobs with optional filtering.
    
    Query params:
      - status: Filter by status (queued, processing, completed, cancelled)
      - limit: Maximum number of jobs to return (default: 50)
      - offset: Pagination offset (default: 0)
    
    Example curl:
    curl "http://localhost:5000/api/v1/ocr/list?status=completed&limit=10"
    """
    status_filter = request.args.get('status')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    with job_lock:
        filtered_jobs = []
        for job_id, job in jobs.items():
            if status_filter is None or job['status'] == status_filter:
                filtered_jobs.append({
                    'job_id': job_id,
                    'status': job['status'],
                    'created_at': job['created_at'],
                    'files_count': len(job['files']),
                    'output_format': job['output_format'],
                    'progress_percent': int((job['progress']['current'] / job['progress']['total']) * 100) if job['progress']['total'] > 0 else 0
                })
        
        # Sort by created_at descending
        filtered_jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply pagination
        total_count = len(filtered_jobs)
        paginated_jobs = filtered_jobs[offset:offset + limit]
        
        return api_response(success=True, data={
            'jobs': paginated_jobs,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        })


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Example curl:
    curl http://localhost:5000/api/v1/health
    """
    # Test LLM provider connections
    providers_status = {}
    for key, config in llm_config.providers.items():
        if config.get('enabled', False):
            result = llm_config.test_connection(key)
            providers_status[key] = {
                'name': config['name'],
                'status': 'connected' if result['success'] else 'disconnected',
                'models_count': len(result.get('models', [])),
                'error': result.get('error') if not result['success'] else None
            }
    
    return api_response(success=True, data={
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_jobs': sum(1 for j in jobs.values() if j['status'] in ['queued', 'processing']),
        'version': '1.1.0',
        'llm_providers': providers_status,
        'active_provider': llm_config.active_provider
    })


@app.route('/api/v1/formats', methods=['GET'])
def get_supported_formats():
    """
    Get supported output formats.
    
    Example curl:
    curl http://localhost:5000/api/v1/formats
    """
    return api_response(success=True, data={
        'formats': [
            {'id': 'txt', 'name': 'Plain Text', 'mime_type': 'text/plain'},
            {'id': 'csv', 'name': 'CSV', 'mime_type': 'text/csv'},
            {'id': 'json', 'name': 'JSON', 'mime_type': 'application/json'},
            {'id': 'html', 'name': 'HTML', 'mime_type': 'text/html'}
        ]
    })


@app.route('/api/v1/llm/providers', methods=['GET'])
def get_llm_providers():
    """
    Get configured LLM providers.
    
    Example curl:
    curl http://localhost:5000/api/v1/llm/providers
    """
    providers_info = []
    for key, config in llm_config.providers.items():
        providers_info.append({
            'key': key,
            'name': config['name'],
            'url': config['url'],
            'model': config['model'],
            'enabled': config.get('enabled', False),
            'api_type': config['api_type'],
            'is_active': key == llm_config.active_provider
        })
    
    return api_response(success=True, data={
        'providers': providers_info,
        'active_provider': llm_config.active_provider
    })


@app.route('/api/v1/llm/config', methods=['GET', 'POST'])
def manage_llm_config():
    """
    Get or update LLM provider configuration.
    
    GET: Returns current configuration
    POST: Updates configuration
    
    Example curl (GET):
    curl http://localhost:5000/api/v1/llm/config
    
    Example curl (POST):
    curl -X POST http://localhost:5000/api/v1/llm/config \
      -H "Content-Type: application/json" \
      -d '{"active_provider": "ollama", "providers": {"ollama": {"url": "http://host.docker.internal:11434", "model": "llava"}}}'
    """
    if request.method == 'GET':
        return api_response(success=True, data={
            'providers': llm_config.providers,
            'active_provider': llm_config.active_provider
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Update active provider
            if 'active_provider' in data:
                if data['active_provider'] in llm_config.providers:
                    llm_config.active_provider = data['active_provider']
                else:
                    return api_response(success=False, error='Invalid provider key'), 400
            
            # Update provider configurations
            if 'providers' in data:
                for key, config in data['providers'].items():
                    if key in llm_config.providers:
                        llm_config.providers[key].update(config)
            
            # Save configuration
            if llm_config.save_config():
                return api_response(success=True, data={
                    'message': 'Configuration saved successfully',
                    'active_provider': llm_config.active_provider
                })
            else:
                return api_response(success=False, error='Failed to save configuration'), 500
                
        except Exception as e:
            return api_response(success=False, error=str(e)), 500


@app.route('/api/v1/llm/test/<provider_key>', methods=['GET'])
def test_llm_provider(provider_key):
    """
    Test connection to a specific LLM provider.
    
    Example curl:
    curl http://localhost:5000/api/v1/llm/test/ollama
    """
    if provider_key not in llm_config.providers:
        return api_response(success=False, error='Provider not found'), 404
    
    result = llm_config.test_connection(provider_key)
    
    if result['success']:
        return api_response(success=True, data=result)
    else:
        return api_response(success=False, error=result.get('error', 'Connection failed')), 500


@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/outputs/<filename>')
def serve_output(filename):
    """Serve output files"""
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
