# Unlimited-OCR API Documentation

## Overview

Unlimited-OCR provides a comprehensive REST API for document recognition using advanced OCR models. The API supports multiple output formats, real-time progress tracking, and streaming responses.

**Base URL:** `http://localhost:5000`

---

## Authentication

Currently, the API does not require authentication. For production use, implement JWT or API key authentication.

---

## API Endpoints

### 1. Health Check

Check if the service is running and get system status.

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00.000000",
  "data": {
    "status": "healthy",
    "active_jobs": 2,
    "version": "1.0.0"
  }
}
```

---

### 2. Get Supported Formats

Retrieve list of supported output formats.

**Endpoint:** `GET /api/v1/formats`

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00.000000",
  "data": {
    "formats": [
      {"id": "txt", "name": "Plain Text", "mime_type": "text/plain"},
      {"id": "csv", "name": "CSV", "mime_type": "text/csv"},
      {"id": "json", "name": "JSON", "mime_type": "application/json"},
      {"id": "html", "name": "HTML", "mime_type": "text/html"}
    ]
  }
}
```

---

### 3. Submit OCR Job

Submit documents for OCR processing.

**Endpoint:** `POST /api/v1/ocr/submit`

**Content Types:**
- `multipart/form-data` (recommended for file uploads)
- `application/json` (for base64 encoded files)

#### Form Data Parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `files` | File[] | Yes | One or more files (PDF, PNG, JPG, JPEG, TIFF) |
| `output_format` | String | No | Output format: `txt`, `csv`, `json`, `html` (default: `txt`) |
| `priority` | String | No | Job priority: `normal`, `high` (default: `normal`) |

#### JSON Body Parameters:

```json
{
  "output_format": "json",
  "priority": "normal",
  "options": {},
  "files": [
    {
      "filename": "document1.pdf",
      "content": "base64_encoded_file_content"
    }
  ]
}
```

**Example (curl with form-data):**
```bash
curl -X POST http://localhost:5000/api/v1/ocr/submit \
  -F "files=@document1.pdf" \
  -F "files=@document2.png" \
  -F "output_format=json" \
  -F "priority=normal"
```

**Example (curl with JSON):**
```bash
curl -X POST http://localhost:5000/api/v1/ocr/submit \
  -H "Content-Type: application/json" \
  -d '{
    "output_format": "json",
    "files": [
      {
        "filename": "document.pdf",
        "content": "JVBERi0xLjQKJeLjz9..."
      }
    ]
  }'
```

**Success Response (202 Accepted):**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00.000000",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "files_count": 2,
    "output_format": "json",
    "estimated_time_seconds": 60
  }
}
```

**Error Responses:**
- `400 Bad Request` - No files provided or invalid format
- `500 Internal Server Error` - Server error

---

### 4. Get Job Status

Check the status and progress of an OCR job.

**Endpoint:** `GET /api/v1/ocr/status/<job_id>`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | UUID | The job ID returned from submit endpoint |

**Example:**
```bash
curl http://localhost:5000/api/v1/ocr/status/550e8400-e29b-41d4-a716-446655440000
```

**Success Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:31:00.000000",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "created_at": "2024-01-15T10:30:00.000000",
    "updated_at": "2024-01-15T10:31:00.000000",
    "output_format": "json",
    "progress": {
      "total_files": 2,
      "processed_files": 1,
      "percent_complete": 50,
      "errors_count": 0
    },
    "errors": []
  }
}
```

**Job Statuses:**
- `queued` - Job is waiting to be processed
- `processing` - Job is currently being processed
- `completed` - Job completed successfully
- `completed_with_errors` - Job completed but some files had errors
- `cancelled` - Job was cancelled

**Error Responses:**
- `404 Not Found` - Job not found

---

### 5. Get Job Results

Retrieve OCR results for a completed job.

**Endpoint:** `GET /api/v1/ocr/result/<job_id>`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | String | job's format | Override output format: `txt`, `csv`, `json`, `html` |
| `download` | Boolean | false | If true, returns file as attachment |

**Example:**
```bash
# Get JSON result
curl http://localhost:5000/api/v1/ocr/result/550e8400-e29b-41d4-a716-446655440000?format=json

# Download as file
curl -O -J http://localhost:5000/api/v1/ocr/result/550e8400-e29b-41d4-a716-446655440000?download=true

# Get HTML format
curl http://localhost:5000/api/v1/ocr/result/550e8400-e29b-41d4-a716-446655440000?format=html
```

**Success Response (JSON format):**
```json
{
  "success": [
    {
      "file": "document1.pdf",
      "text": "Recognized text content...",
      "pages": 5
    },
    {
      "file": "document2.png",
      "text": "Recognized text from image..."
    }
  ],
  "errors": []
}
```

**Error Responses:**
- `404 Not Found` - Job not found
- `202 Accepted` - Job not completed yet
- `404 Not Found` - No results available

---

### 6. Stream Job Results (SSE)

Receive real-time updates via Server-Sent Events.

**Endpoint:** `GET /api/v1/ocr/stream/<job_id>`

**Example:**
```bash
curl -N http://localhost:5000/api/v1/ocr/stream/550e8400-e29b-41d4-a716-446655440000
```

**Event Stream Format:**

Progress event:
```
data: {"type":"progress","job_id":"...","status":"processing","current":1,"total":2,"percent":50}
```

Complete event:
```
data: {"type":"complete","job_id":"...","status":"completed","results":{...}}
```

Heartbeat event:
```
data: {"type":"heartbeat","timestamp":"2024-01-15T10:30:00.000000"}
```

**JavaScript Example:**
```javascript
const eventSource = new EventSource('http://localhost:5000/api/v1/ocr/stream/550e8400-e29b-41d4-a716-446655440000');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    console.log(`Progress: ${data.percent}%`);
  } else if (data.type === 'complete') {
    console.log('OCR Complete!', data.results);
    eventSource.close();
  }
};
```

---

### 7. Cancel Job

Cancel a queued OCR job.

**Endpoint:** `POST /api/v1/ocr/cancel/<job_id>`

**Example:**
```bash
curl -X POST http://localhost:5000/api/v1/ocr/cancel/550e8400-e29b-41d4-a716-446655440000
```

**Success Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00.000000",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled"
  }
}
```

**Error Responses:**
- `404 Not Found` - Job not found
- `409 Conflict` - Cannot cancel job that is already processing or completed

---

### 8. List Jobs

List all OCR jobs with filtering and pagination.

**Endpoint:** `GET /api/v1/ocr/list`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | String | all | Filter by status: `queued`, `processing`, `completed`, `cancelled` |
| `limit` | Integer | 50 | Maximum jobs to return (max: 100) |
| `offset` | Integer | 0 | Pagination offset |

**Example:**
```bash
# Get completed jobs
curl "http://localhost:5000/api/v1/ocr/list?status=completed&limit=10&offset=0"

# Get all jobs
curl "http://localhost:5000/api/v1/ocr/list"
```

**Success Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00.000000",
  "data": {
    "jobs": [
      {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "created_at": "2024-01-15T10:30:00.000000",
        "files_count": 2,
        "output_format": "json",
        "progress_percent": 100
      }
    ],
    "pagination": {
      "total": 25,
      "limit": 10,
      "offset": 0,
      "has_more": true
    }
  }
}
```

---

## Legacy Endpoints

These endpoints are maintained for backward compatibility with the web UI.

### Upload Files (Legacy)
**POST /api/upload**

### Get Progress (Legacy)
**GET /api/progress/<job_id>**

### Get Result (Legacy)
**GET /api/result/<job_id>**

### Get Formats (Legacy)
**GET /api/formats**

---

## Error Handling

All API errors follow a consistent format:

```json
{
  "success": false,
  "timestamp": "2024-01-15T10:30:00.000000",
  "error": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 202 | Accepted (job queued/processing) |
| 400 | Bad Request |
| 404 | Not Found |
| 409 | Conflict |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing:
- Request throttling per IP
- API key-based quotas
- Concurrent job limits

---

## Best Practices

1. **Polling**: Use SSE streaming (`/api/v1/ocr/stream/`) instead of polling for real-time updates
2. **Large Files**: For large PDFs, expect longer processing times (approximately 30 seconds per file)
3. **Error Handling**: Always check the `errors` array in results for partial failures
4. **Job Cleanup**: Implement job cleanup logic to remove old completed jobs
5. **File Validation**: Validate file types before submission to avoid unnecessary processing

---

## Client Libraries

### Python Example

```python
import requests
import time

# Submit job
files = {'files': open('document.pdf', 'rb')}
data = {'output_format': 'json'}
response = requests.post('http://localhost:5000/api/v1/ocr/submit', files=files, data=data)
job_id = response.json()['data']['job_id']

# Poll for completion
while True:
    status_response = requests.get(f'http://localhost:5000/api/v1/ocr/status/{job_id}')
    status = status_response.json()['data']['status']
    
    if status in ['completed', 'completed_with_errors']:
        break
    
    time.sleep(2)

# Get results
result_response = requests.get(f'http://localhost:5000/api/v1/ocr/result/{job_id}')
results = result_response.json()
print(results)
```

### JavaScript Example

```javascript
// Submit job
const formData = new FormData();
formData.append('files', fileInput.files[0]);
formData.append('output_format', 'json');

const submitResponse = await fetch('http://localhost:5000/api/v1/ocr/submit', {
  method: 'POST',
  body: formData
});
const { data: { job_id } } = await submitResponse.json();

// Listen to stream
const eventSource = new EventSource(`http://localhost:5000/api/v1/ocr/stream/${job_id}`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'complete') {
    console.log('Results:', data.results);
    eventSource.close();
  }
};
```

---

## Support

For issues and feature requests, please refer to the project repository.
