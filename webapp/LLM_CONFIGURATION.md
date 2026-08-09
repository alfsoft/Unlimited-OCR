# LLM Provider Configuration

The OCR service now supports multiple LLM providers for document recognition:

## Supported Providers

### 1. SGLang (Default)
- **API Type**: OpenAI-compatible
- **Default URL**: `http://127.0.0.1:10000`
- **Default Model**: `Unlimited-OCR`
- **Features**: Custom ngram processor, Gundam image mode
- **Best for**: High-accuracy OCR with specialized models

### 2. llama.cpp
- **API Type**: OpenAI-compatible  
- **Default URL**: `http://host.docker.internal:8080`
- **Default Model**: Auto-detected
- **Features**: Standard vision language models
- **Best for**: Local inference with quantized models

### 3. Ollama
- **API Type**: Ollama native API
- **Default URL**: `http://host.docker.internal:11434`
- **Default Model**: `llava`
- **Features**: Easy model management, wide model selection
- **Best for**: Quick setup, testing different models

## Configuration File

Configuration is stored in `/app/config/llm_config.json`:

```json
{
  "providers": {
    "sglang": {
      "name": "SGLang",
      "url": "http://127.0.0.1:10000",
      "model": "Unlimited-OCR",
      "enabled": true,
      "api_type": "openai_compat",
      "prompt": "document parsing.",
      "temperature": 0,
      "timeout": 1200,
      "max_retries": 3,
      "supports_images": true,
      "custom_params": {
        "no_repeat_ngram_size": 35,
        "ngram_window": 128,
        "image_mode": "gundam"
      }
    },
    "llamacpp": {
      "name": "llama.cpp",
      "url": "http://host.docker.internal:8080",
      "model": "",
      "enabled": false,
      "api_type": "openai_compat",
      "prompt": "Extract all text from this document image accurately.",
      "temperature": 0.1,
      "timeout": 300,
      "max_retries": 3,
      "supports_images": true,
      "custom_params": {
        "max_tokens": 4096,
        "stop": []
      }
    },
    "ollama": {
      "name": "Ollama",
      "url": "http://host.docker.internal:11434",
      "model": "llava",
      "enabled": false,
      "api_type": "ollama",
      "prompt": "Extract all text from this document image accurately.",
      "temperature": 0.1,
      "timeout": 300,
      "max_retries": 3,
      "supports_images": true,
      "custom_params": {
        "num_predict": 4096,
        "keep_alive": "5m"
      }
    }
  },
  "active_provider": "sglang"
}
```

## API Endpoints

### Get Available Providers
```bash
curl http://localhost:5000/api/v1/llm/providers
```

Response:
```json
{
  "success": true,
  "timestamp": "2024-01-01T00:00:00",
  "data": {
    "providers": [
      {
        "key": "sglang",
        "name": "SGLang",
        "url": "http://127.0.0.1:10000",
        "model": "Unlimited-OCR",
        "enabled": true,
        "api_type": "openai_compat",
        "is_active": true
      },
      {
        "key": "llamacpp",
        "name": "llama.cpp",
        "url": "http://host.docker.internal:8080",
        "model": "",
        "enabled": false,
        "api_type": "openai_compat",
        "is_active": false
      },
      {
        "key": "ollama",
        "name": "Ollama",
        "url": "http://host.docker.internal:11434",
        "model": "llava",
        "enabled": false,
        "api_type": "ollama",
        "is_active": false
      }
    ],
    "active_provider": "sglang"
  }
}
```

### Get Current Configuration
```bash
curl http://localhost:5000/api/v1/llm/config
```

### Update Configuration
```bash
curl -X POST http://localhost:5000/api/v1/llm/config \
  -H "Content-Type: application/json" \
  -d '{
    "active_provider": "ollama",
    "providers": {
      "ollama": {
        "url": "http://host.docker.internal:11434",
        "model": "llava:13b"
      }
    }
  }'
```

### Test Provider Connection
```bash
curl http://localhost:5000/api/v1/llm/test/ollama
```

Response:
```json
{
  "success": true,
  "timestamp": "2024-01-01T00:00:00",
  "data": {
    "success": true,
    "models": ["llava", "llava:13b", "mistral"],
    "message": "Connected to Ollama. Found 3 models."
  }
}
```

### Submit Job with Specific Provider
```bash
curl -X POST http://localhost:5000/api/v1/ocr/submit \
  -F "files=@document.pdf" \
  -F "output_format=json" \
  -F "provider=ollama"
```

## Docker Network Configuration

For Docker Desktop on Windows, the services running on your host machine are accessible via `host.docker.internal`:

### Running llama.cpp server
```bash
# On Windows host
./server.exe -m models/llava-v1.5-7b.Q4_K_M.gguf --port 8080 --host 0.0.0.0
```

### Running Ollama
```bash
# On Windows host - ensure Ollama allows network connections
set OLLAMA_HOST=0.0.0.0
ollama serve
```

Then pull a vision model:
```bash
ollama pull llava
ollama pull llava:13b
```

## Web Interface Configuration

The web interface includes an LLM configuration panel where you can:
1. View all configured providers
2. Switch active provider
3. Update URLs and model names
4. Test connections
5. Save configuration

Access the configuration panel at: `http://localhost:8080` (click the Settings icon)

## Best Practices

1. **Enable only needed providers**: Set `enabled: false` for unused providers
2. **Test before switching**: Use the test endpoint to verify connectivity
3. **Adjust timeouts**: Vision models may need longer timeouts for large documents
4. **Model selection**: Use appropriate vision-language models (llava, bakllava, etc.)
5. **Resource management**: Don't run multiple heavy models simultaneously

## Troubleshooting

### Connection refused
- Ensure the LLM server is running
- Check firewall settings on Windows
- Verify `host.docker.internal` resolves correctly

### Model not found
- Pull the model: `ollama pull llava`
- Check model name spelling
- Verify model is loaded in llama.cpp

### Timeout errors
- Increase `timeout` value in provider config
- Reduce document size or DPI
- Use a smaller/faster model

### Poor OCR quality
- Adjust the `prompt` for better instructions
- Lower `temperature` for more deterministic output
- Try a different model specialized for OCR
