<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unlimited OCR - Распознавание документов</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .main-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }

        .upload-section {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }

        .upload-section:hover {
            background: #f0f4ff;
            border-color: #764ba2;
        }

        .upload-section.dragover {
            background: #e8eeff;
            border-color: #764ba2;
        }

        .upload-icon {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 15px;
        }

        .file-input {
            display: none;
        }

        .format-selector {
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .format-selector label {
            font-weight: 600;
            margin-right: 15px;
        }

        .format-selector select {
            padding: 8px 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .progress-section {
            margin-top: 30px;
            display: none;
        }

        .progress-bar-container {
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            height: 30px;
            margin: 15px 0;
        }

        .progress-bar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }

        .status-text {
            text-align: center;
            color: #666;
            margin: 10px 0;
        }

        .results-section {
            margin-top: 30px;
            display: none;
        }

        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .result-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }

        .result-card h4 {
            color: #333;
            margin-bottom: 10px;
            word-break: break-all;
        }

        .result-text {
            background: white;
            padding: 15px;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .download-btn {
            margin-top: 10px;
            padding: 8px 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
        }

        .download-btn:hover {
            background: #218838;
        }

        .file-list {
            margin: 20px 0;
            max-height: 150px;
            overflow-y: auto;
        }

        .file-item {
            padding: 8px 15px;
            background: #f0f4ff;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .file-item .remove {
            color: #dc3545;
            cursor: pointer;
            font-weight: bold;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Unlimited OCR</h1>
            <p>Распознавание документов с использованием передовых моделей ИИ</p>
        </header>

        <div class="main-card">
            <div class="upload-section" id="dropZone">
                <div class="upload-icon">📁</div>
                <h3>Перетащите файлы сюда или кликните для выбора</h3>
                <p style="color: #666; margin-top: 10px;">Поддерживаются: PDF, PNG, JPG, JPEG, WEBP, BMP</p>
                <input type="file" id="fileInput" class="file-input" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp">
            </div>

            <div class="file-list" id="fileList"></div>

            <div class="format-selector">
                <label for="outputFormat">Формат вывода:</label>
                <select id="outputFormat">
                    <option value="txt">TXT (Текст)</option>
                    <option value="csv">CSV (Таблица)</option>
                    <option value="json">JSON (Структурировано)</option>
                    <option value="html">HTML (Веб-страница)</option>
                </select>
                <button class="btn" id="startBtn" style="margin-left: 20px;" onclick="startProcessing()">
                    🚀 Запустить распознавание
                </button>
            </div>

            <div id="messageArea"></div>

            <div class="progress-section" id="progressSection">
                <h3>Прогресс обработки</h3>
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progressBar">0%</div>
                </div>
                <p class="status-text" id="statusText">Ожидание начала обработки...</p>
                <div class="spinner" id="spinner"></div>
            </div>

            <div class="results-section" id="resultsSection">
                <h3>📄 Результаты распознавания</h3>
                <div class="results-grid" id="resultsGrid"></div>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let currentJobId = null;
        let progressInterval = null;

        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const startBtn = document.getElementById('startBtn');
        const progressSection = document.getElementById('progressSection');
        const progressBar = document.getElementById('progressBar');
        const statusText = document.getElementById('statusText');
        const spinner = document.getElementById('spinner');
        const resultsSection = document.getElementById('resultsSection');
        const resultsGrid = document.getElementById('resultsGrid');
        const messageArea = document.getElementById('messageArea');

        // Drag and drop handlers
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        dropZone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        function handleFiles(files) {
            const validTypes = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp'];
            
            for (let file of files) {
                const ext = '.' + file.name.split('.').pop().toLowerCase();
                if (validTypes.includes(ext)) {
                    selectedFiles.push(file);
                } else {
                    showMessage(`Файл "${file.name}" имеет неподдерживаемый формат`, 'error');
                }
            }
            updateFileList();
        }

        function updateFileList() {
            if (selectedFiles.length === 0) {
                fileList.innerHTML = '';
                return;
            }

            fileList.innerHTML = '<h4>Выбранные файлы:</h4>';
            selectedFiles.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <span>📄 ${file.name} (${formatFileSize(file.size)})</span>
                    <span class="remove" onclick="removeFile(${index})">✕</span>
                `;
                fileList.appendChild(item);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function showMessage(text, type) {
            messageArea.innerHTML = `<div class="alert alert-${type}">${text}</div>`;
            setTimeout(() => {
                messageArea.innerHTML = '';
            }, 5000);
        }

        async function startProcessing() {
            if (selectedFiles.length === 0) {
                showMessage('Пожалуйста, выберите файлы для обработки', 'error');
                return;
            }

            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            formData.append('format', document.getElementById('outputFormat').value);

            startBtn.disabled = true;
            progressSection.style.display = 'block';
            resultsSection.style.display = 'none';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                
                if (response.ok) {
                    currentJobId = data.job_id;
                    showMessage(data.message, 'success');
                    startProgressPolling();
                } else {
                    showMessage(data.error || 'Ошибка при загрузке файлов', 'error');
                    startBtn.disabled = false;
                    progressSection.style.display = 'none';
                }
            } catch (error) {
                showMessage('Ошибка соединения: ' + error.message, 'error');
                startBtn.disabled = false;
                progressSection.style.display = 'none';
            }
        }

        function startProgressPolling() {
            progressInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/progress/${currentJobId}`);
                    const data = await response.json();

                    if (response.ok) {
                        const percent = data.progress_percent;
                        progressBar.style.width = percent + '%';
                        progressBar.textContent = percent + '%';
                        statusText.textContent = `Обработано ${data.current} из ${data.total} файлов`;

                        if (data.status === 'completed') {
                            clearInterval(progressInterval);
                            showResults();
                        }
                    }
                } catch (error) {
                    console.error('Error fetching progress:', error);
                }
            }, 1000);
        }

        async function showResults() {
            spinner.style.display = 'none';
            statusText.textContent = 'Обработка завершена!';
            
            try {
                const response = await fetch(`/api/result/${currentJobId}`);
                const data = await response.json();

                if (response.ok) {
                    resultsGrid.innerHTML = '';
                    data.results.forEach((result, index) => {
                        if (result && result.trim()) {
                            const card = document.createElement('div');
                            card.className = 'result-card';
                            const format = document.getElementById('outputFormat').value;
                            card.innerHTML = `
                                <h4>📄 Документ ${index + 1}</h4>
                                <div class="result-text">${escapeHtml(result)}</div>
                                <button class="download-btn" onclick="downloadResult(${index}, '${format}')">
                                    ⬇️ Скачать в ${format.toUpperCase()}
                                </button>
                            `;
                            resultsGrid.appendChild(card);
                        }
                    });
                    resultsSection.style.display = 'block';
                }
            } catch (error) {
                showMessage('Ошибка при получении результатов: ' + error.message, 'error');
            }

            startBtn.disabled = false;
        }

        function downloadResult(index, format) {
            const link = document.createElement('a');
            link.href = `/outputs/result_${index + 1}.${format}`;
            link.download = `result_${index + 1}.${format}`;
            link.click();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
