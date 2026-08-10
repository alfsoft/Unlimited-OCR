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

UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Хранилище задач в памяти
jobs = {}
jobs_lock = threading.Lock()

# Конфигурация LLM
LLM_CONFIG_FILE = '/app/config/llm_config.json'
DEFAULT_CONFIG = {
    "active_provider": "sglang",
    "providers": {
        "sglang": {
            "url": "http://host.docker.internal:30000",
            "model": "default",
            "timeout": 300
        },
        "llamacpp": {
            "url": "http://host.docker.internal:8080",
            "model": "default",
            "timeout": 300
        },
        "ollama": {
            "url": "http://host.docker.internal:11434",
            "model": "llama2",
            "timeout": 300
        }
    }
}

def load_config():
    """Загрузка конфигурации LLM"""
    print("[CONFIG] Loading configuration from", LLM_CONFIG_FILE)
    if os.path.exists(LLM_CONFIG_FILE):
        try:
            with open(LLM_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print("[CONFIG] Configuration loaded successfully")
                return config
        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        print("[CONFIG] Config file not found, using default")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Сохранение конфигурации LLM"""
    try:
        os.makedirs(os.path.dirname(LLM_CONFIG_FILE), exist_ok=True)
        with open(LLM_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print("[CONFIG] Configuration saved successfully")
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")

llm_config = load_config()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файла (старый endpoint для совместимости)"""
    print(f"[API] >>> POST /upload from {request.remote_addr}")
    print(f"[API] Content-Type: {request.content_type}")
    
    # Перенаправление на новый endpoint
    print("[API] Redirecting to /api/v1/ocr/submit")
    return submit_ocr_job()

@app.route('/api/v1/ocr/submit', methods=['POST'])
def submit_ocr_job():
    """Создание задачи OCR"""
    print(f"[API] >>> POST /api/v1/ocr/submit from {request.remote_addr}")
    print(f"[API] Content-Type: {request.content_type}")
    
    if 'file' not in request.files:
        print("[API] ERROR: No file provided")
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("[API] ERROR: Empty filename")
        return jsonify({"error": "Empty filename"}), 400
    
    # Генерация ID задачи
    job_id = str(uuid.uuid4())
    
    # Сохранение файла
    filename = f"{job_id}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    print(f"[API] File saved: {filepath}")
    
    # Получение параметров
    output_format = request.form.get('format', 'txt')
    pages = request.form.get('pages', 'all')
    
    # Создание задачи
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'status': 'pending',
            'filename': file.filename,
            'filepath': filepath,
            'output_format': output_format,
            'pages': pages,
            'created_at': datetime.now().isoformat(),
            'result': None,
            'error': None
        }
    
    print(f"[API] Job created: {job_id}")
    print(f"[API] <<< 202 Accepted for job {job_id}")
    return jsonify({
        "job_id": job_id,
        "status": "pending"
    }), 202

@app.route('/api/v1/ocr/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Получение статуса задачи"""
    print(f"[API] >>> GET /api/v1/ocr/status/{job_id} from {request.remote_addr}")
    
    with jobs_lock:
        if job_id not in jobs:
            print(f"[API] ERROR: Job {job_id} not found")
            return jsonify({"error": "Job not found"}), 404
        
        job = jobs[job_id]
        print(f"[API] Job {job_id} status: {job['status']}")
        print(f"[API] <<< 200 OK")
        return jsonify({
            "job_id": job_id,
            "status": job['status'],
            "filename": job['filename'],
            "created_at": job['created_at']
        })

@app.route('/api/v1/ocr/result/<job_id>', methods=['GET'])
def get_job_result(job_id):
    """Получение результата задачи"""
    print(f"[API] >>> GET /api/v1/ocr/result/{job_id} from {request.remote_addr}")
    
    with jobs_lock:
        if job_id not in jobs:
            print(f"[API] ERROR: Job {job_id} not found")
            return jsonify({"error": "Job not found"}), 404
        
        job = jobs[job_id]
        
        if job['status'] != 'completed':
            print(f"[API] Job {job_id} not completed yet, status: {job['status']}")
            return jsonify({
                "job_id": job_id,
                "status": job['status'],
                "message": "Processing not completed yet"
            }), 202
        
        print(f"[API] Job {job_id} completed, returning result")
        print(f"[API] <<< 200 OK")
        return jsonify({
            "job_id": job_id,
            "status": "completed",
            "result": job['result'],
            "filename": job['filename']
        })

@app.route('/api/v1/ocr/stream/<job_id>', methods=['GET'])
def stream_job_result(job_id):
    """Потоковая передача результата"""
    print(f"[API] >>> GET /api/v1/ocr/stream/{job_id} from {request.remote_addr}")
    
    def generate():
        max_wait = 300  # 5 минут
        wait_time = 0
        while wait_time < max_wait:
            with jobs_lock:
                if job_id not in jobs:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                    return
                
                job = jobs[job_id]
                
                if job['status'] == 'completed':
                    yield f"data: {json.dumps({'status': 'completed', 'result': job['result']})}\n\n"
                    return
                elif job['status'] == 'failed':
                    yield f"data: {json.dumps({'status': 'failed', 'error': job['error']})}\n\n"
                    return
            
            yield f"data: {json.dumps({'status': 'processing'})}\n\n"
            time.sleep(2)
            wait_time += 2
        
        yield f"data: {json.dumps({'status': 'timeout', 'error': 'Processing timeout'})}\n\n"
    
    print(f"[API] <<< 200 OK (streaming)")
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive',
                       'Access-Control-Allow-Origin': '*'
                   })

@app.route('/api/v1/ocr/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Отмена задачи"""
    print(f"[API] >>> POST /api/v1/ocr/cancel/{job_id} from {request.remote_addr}")
    
    with jobs_lock:
        if job_id not in jobs:
            print(f"[API] ERROR: Job {job_id} not found")
            return jsonify({"error": "Job not found"}), 404
        
        job = jobs[job_id]
        if job['status'] in ['completed', 'failed']:
            print(f"[API] Job {job_id} already finished, cannot cancel")
            return jsonify({"error": "Cannot cancel finished job"}), 400
        
        job['status'] = 'cancelled'
        print(f"[API] Job {job_id} cancelled")
        print(f"[API] <<< 200 OK")
        return jsonify({"job_id": job_id, "status": "cancelled"})

@app.route('/api/v1/ocr/list', methods=['GET'])
def list_jobs():
    """Список всех задач"""
    print(f"[API] >>> GET /api/v1/ocr/list from {request.remote_addr}")
    
    with jobs_lock:
        job_list = []
        for job_id, job in jobs.items():
            job_list.append({
                "job_id": job_id,
                "status": job['status'],
                "filename": job['filename'],
                "created_at": job['created_at']
            })
    
    print(f"[API] Found {len(job_list)} jobs")
    print(f"[API] <<< 200 OK")
    return jsonify({"jobs": job_list})

@app.route('/api/v1/formats', methods=['GET'])
def get_formats():
    """Получение поддерживаемых форматов"""
    print(f"[API] >>> GET /api/v1/formats from {request.remote_addr}")
    formats = ["txt", "md", "json"]
    print(f"[API] Available formats: {formats}")
    print(f"[API] <<< 200 OK")
    return jsonify({"formats": formats})

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса"""
    print(f"[API] >>> GET /api/v1/health from {request.remote_addr}")
    print(f"[API] <<< 200 OK")
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/v1/llm/providers', methods=['GET'])
def get_providers():
    """Получение списка провайдеров LLM"""
    print(f"[API] >>> GET /api/v1/llm/providers from {request.remote_addr}")
    providers = list(llm_config.get('providers', {}).keys())
    print(f"[API] Available providers: {providers}")
    print(f"[API] <<< 200 OK")
    return jsonify({
        "providers": providers,
        "active": llm_config.get('active_provider')
    })

@app.route('/api/v1/llm/config', methods=['GET', 'POST'])
def llm_config_endpoint():
    """Получение или обновление конфигурации LLM"""
    global llm_config
    print(f"[API] >>> {'POST' if request.method == 'POST' else 'GET'} /api/v1/llm/config from {request.remote_addr}")
    
    if request.method == 'POST':
        new_config = request.json
        llm_config.update(new_config)
        save_config(llm_config)
        print("[CONFIG] Updated provider settings")
        print(f"[API] <<< 200 OK (config updated)")
        return jsonify({"status": "updated", "config": llm_config})
    
    print(f"[API] <<< 200 OK")
    return jsonify(llm_config)

@app.route('/api/v1/llm/test/<provider_key>', methods=['POST'])
def test_llm_connection(provider_key):
    """Тестирование подключения к LLM провайдеру"""
    print(f"[API] >>> POST /api/v1/llm/test/{provider_key} from {request.remote_addr}")
    
    providers = llm_config.get('providers', {})
    if provider_key not in providers:
        print(f"[API] ERROR: Provider {provider_key} not found")
        return jsonify({"error": "Provider not found"}), 404
    
    provider = providers[provider_key]
    url = provider.get('url', '')
    model = provider.get('model', 'default')
    timeout = provider.get('timeout', 300)
    
    print(f"[LLM] Testing connection to {provider_key}")
    print(f"[LLM] URL: {url}, Model: {model}, Timeout: {timeout}s")
    
    try:
        # Пробный запрос к API
        test_payload = {
            "prompt": "Test connection",
            "max_tokens": 1
        }
        
        response = requests.post(
            f"{url}/generate",
            json=test_payload,
            timeout=min(timeout, 10)
        )
        
        if response.status_code == 200:
            print(f"[LLM] Connection successful!")
            print(f"[API] <<< 200 OK")
            return jsonify({
                "status": "success",
                "provider": provider_key,
                "message": "Connection successful"
            })
        else:
            print(f"[LLM] Connection failed with status {response.status_code}")
            print(f"[API] <<< 500 Error")
            return jsonify({
                "status": "error",
                "provider": provider_key,
                "message": f"HTTP {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        print(f"[LLM] Connection timeout")
        print(f"[API] <<< 500 Error (timeout)")
        return jsonify({
            "status": "error",
            "provider": provider_key,
            "message": "Connection timeout"
        }), 500
        
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] Connection error: {str(e)}")
        print(f"[API] <<< 500 Error (connection)")
        return jsonify({
            "status": "error",
            "provider": provider_key,
            "message": "Connection failed"
        }), 500
        
    except Exception as e:
        print(f"[LLM] Unexpected error: {str(e)}")
        print(f"[API] <<< 500 Error")
        return jsonify({
            "status": "error",
            "provider": provider_key,
            "message": str(e)
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Доступ к загруженным файлам"""
    print(f"[API] Serving uploaded file: {filename}")
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/outputs/<filename>')
def output_file(filename):
    """Доступ к выходным файлам"""
    print(f"[API] Serving output file: {filename}")
    return send_from_directory(OUTPUT_FOLDER, filename)

# Обработчик ошибок 404
@app.errorhandler(404)
def not_found(error):
    print(f"[API] ERROR 404: Route not found - {request.method} {request.path}")
    print(f"[API] Available routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
    print(f"[API] <<< 404 for {request.method} {request.path}")
    return jsonify({
        "error": "Route not found",
        "path": request.path,
        "method": request.method,
        "available_routes": [rule.rule for rule in app.url_map.iter_rules()]
    }), 404

if __name__ == '__main__':
    print("=" * 50)
    print("Starting Unlimited OCR Backend")
    print("=" * 50)
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Active LLM provider: {llm_config.get('active_provider')}")
    print("=" * 50)
    
    # Запуск Flask приложения
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
