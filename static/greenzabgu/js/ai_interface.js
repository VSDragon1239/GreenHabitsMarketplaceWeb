// ai_interface.js
(function () {
    const dropzone = document.getElementById('fileDropzone');
    const fileInput = document.getElementById('fileInput');
    const fileListDiv = document.getElementById('fileList');
    const attachedFilesInput = document.getElementById('attachedFilesInput');
    const chatForm = document.getElementById('chatForm');
    const promptInput = document.getElementById('promptInput');
    const submitBtn = document.getElementById('submitBtn');
    const stopBtn = document.getElementById('stopBtn');
    const aiTerminal = document.getElementById('aiTerminal');

    let attachedFiles = [];          // { filename, preview, fileId }
    let abortController = null;      // для прерывания fetch
    let currentStream = null;

    // Функция экранирования HTML
    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function (m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }

    // Отображение списка файлов
    function renderFileList() {
        fileListDiv.innerHTML = attachedFiles.map((file, idx) => `
            <div class="file-item" data-idx="${idx}">
                ${file.preview ? `<img class="preview" src="${file.preview}" alt="">` : '📄'}
                <span>${escapeHtml(file.filename)}</span>
                <span class="remove-file" data-filename="${escapeHtml(file.filename)}">✖</span>
            </div>
        `).join('');
        attachedFilesInput.value = attachedFiles.map(f => f.filename).join(',');
        document.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const filename = btn.getAttribute('data-filename');
                attachedFiles = attachedFiles.filter(f => f.filename !== filename);
                renderFileList();
            });
        });
    }

    // Загрузка файла на сервер
    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        const tempId = 'temp_' + Date.now() + '_' + Math.random();
        const tempDiv = document.createElement('div');
        tempDiv.className = 'file-item';
        tempDiv.id = tempId;
        tempDiv.innerHTML = `<span>${escapeHtml(file.name)}</span><span class="spinner"></span>`;
        fileListDiv.appendChild(tempDiv);

        try {
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const response = await fetch('/upload-file/', {
                method: 'POST',
                body: formData,
                headers: {'X-CSRFToken': csrftoken}
            });
            const data = await response.json();
            if (response.ok && data.success) {
                document.getElementById(tempId)?.remove();
                attachedFiles.push({
                    filename: data.filename,
                    preview: data.preview,
                    fileId: data.file_id
                });
                renderFileList();
            } else {
                throw new Error(data.error || 'Ошибка загрузки');
            }
        } catch (error) {
            const tempElem = document.getElementById(tempId);
            if (tempElem) {
                tempElem.innerHTML = `<span style="color:red;">Ошибка: ${escapeHtml(file.name)}</span>`;
                setTimeout(() => tempElem.remove(), 3000);
            }
        }
    }

    // Потоковое чтение ответа и вывод
    async function sendChatRequest(prompt, attachedFilesList) {
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('attached_files', attachedFilesList.join(','));

        abortController = new AbortController();
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        try {
            const response = await fetch('/chat-stream/', {
                method: 'POST',
                body: formData,
                headers: {'X-CSRFToken': csrftoken},
                signal: abortController.signal
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            if (!response.body) throw new Error('Stream не поддерживается');

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let answerDiv = null;
            let answerText = '';

            while (true) {
                const {done, value} = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n');
                buffer = lines.pop(); // последний кусок может быть неполным

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.error) {
                                throw new Error(data.error);
                            }
                            if (data.text !== undefined) {
                                if (!answerDiv) {
                                    // Очищаем терминал и создаём новый блок для ответа
                                    aiTerminal.innerHTML = '';
                                    answerDiv = document.createElement('div');
                                    answerDiv.className = 'ai-response';
                                    aiTerminal.appendChild(answerDiv);
                                }
                                answerText += data.text;
                                answerDiv.textContent = answerText;
                                // Автопрокрутка вниз
                                aiTerminal.scrollTop = aiTerminal.scrollHeight;
                            }
                            if (data.done) {
                                break;
                            }
                        } catch (e) {
                            console.warn('Ошибка парсинга JSON:', e);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Запрос прерван');
                if (aiTerminal.lastChild && aiTerminal.lastChild.classList.contains('ai-response')) {
                    const last = aiTerminal.lastChild;
                    last.textContent += '\n\n[Генерация остановлена пользователем]';
                } else {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'ai-response';
                    errorDiv.textContent = '[Генерация остановлена пользователем]';
                    aiTerminal.appendChild(errorDiv);
                }
            } else {
                console.error('Ошибка:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'ai-response';
                errorDiv.textContent = `Ошибка: ${error.message}`;
                aiTerminal.appendChild(errorDiv);
            }
        } finally {
            abortController = null;
            currentStream = null;
            submitBtn.disabled = false;
            submitBtn.querySelector('.spinner').style.display = 'none';
            stopBtn.style.display = 'none';
            promptInput.disabled = false;
        }
    }

    // Обработчик отправки формы
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = promptInput.value.trim();
        if (!prompt && attachedFiles.length === 0) {
            alert('Введите вопрос или прикрепите файл');
            return;
        }

        if (currentStream) return; // уже идёт запрос

        // Отключаем элементы интерфейса
        submitBtn.disabled = true;
        submitBtn.querySelector('.spinner').style.display = 'inline-block';
        stopBtn.style.display = 'inline-block';
        promptInput.disabled = true;

        // Очищаем терминал для нового ответа
        aiTerminal.innerHTML = '<div class="ai-placeholder">> Генерация ответа...</div>';
        currentStream = sendChatRequest(prompt, attachedFiles.map(f => f.filename));
        await currentStream;
    });

    // Остановка генерации
    stopBtn.addEventListener('click', () => {
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
    });

    // Загрузка файлов
    fileInput.addEventListener('change', (e) => {
        Array.from(e.target.files).forEach(file => uploadFile(file));
        fileInput.value = '';
    });

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        Array.from(e.dataTransfer.files).forEach(file => uploadFile(file));
    });
})();