document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('complete-task-btn');
    if (!btn) return;

    const taskType = btn.getAttribute('data-task-type');
    const proofSection = document.getElementById('proof-section');

    // 1. Показываем нужное поле ввода
    if (taskType === 'text_code') {
        proofSection.classList.remove('hidden');
        document.getElementById('input-text-code').classList.remove('hidden');
    } else if (taskType === 'photo') {
        proofSection.classList.remove('hidden');
        document.getElementById('input-photo').classList.remove('hidden');

        const fileInput = document.getElementById('proof_image');
        const imgPreview = document.getElementById('image-preview');
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                imgPreview.src = URL.createObjectURL(file);
                imgPreview.classList.remove('hidden');
            }
        });
    }

    // 2. Обработка отправки
    btn.addEventListener('click', function () {
        if (btn.disabled) return;
        const taskId = btn.getAttribute('data-task-id');

        if (taskType === 'text_code' && !document.getElementById('proof_text').value) {
            alert('Пожалуйста, введите код!');
            return;
        }
        if (taskType === 'photo' && !document.getElementById('proof_image').files.length) {
            alert('Пожалуйста, сделайте или выберите фото!');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<svg class="animate-spin h-5 w-5 mr-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Отправка...`;

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

        if (taskType === 'text_code') {
            formData.append('proof_text', document.getElementById('proof_text').value);
        }
        if (taskType === 'photo') {
            formData.append('proof_image', document.getElementById('proof_image').files[0]);
        }

        fetch(`/main/green-zabgu/eco-tasks/complete/${taskId}/`, {
            method: 'POST',
            body: formData,
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('action-area').innerHTML = `
                                <div class="flex items-center bg-yellow-50 p-4 rounded-xl border border-yellow-200">
                                    <i class="material-icons text-3xl text-yellow-600 mr-4">hourglass_top</i>
                                    <div>
                                        <h4 class="font-bold text-gray-800">${data.message}</h4>
                                        <p class="text-gray-600 text-sm mt-1">Ожидает модерации.</p>
                                    </div>
                                </div>`;
                } else {
                    alert(data.error || 'Ошибка отправки');
                    btn.disabled = false;
                    btn.innerHTML = '<i class="material-icons mr-2">bolt</i> Отправить на проверку';
                }
            })
            .catch(() => {
                alert('Сетевая ошибка');
                btn.disabled = false;
                btn.innerHTML = '<i class="material-icons mr-2">bolt</i> Отправить на проверку';
            });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.substring(0, name.length + 1) === (name + '=')) cookieValue = decodeURIComponent(c.substring(name.length + 1));
        });
    }
    return cookieValue;
}