document.addEventListener('DOMContentLoaded', function () {
    // Функция получения CSRF токена (обязательно для POST запросов в Django)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    const btn = document.getElementById('log-habit-btn');

    btn.addEventListener('click', function () {
        const habitId = btn.getAttribute('data-habit-id');

        // Блокируем кнопку от двойных кликов
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Проверяем...';

        // Отправляем AJAX
        fetch(`/main/green-zabgu/eco-habits/log/${habitId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Меняем кнопку на уведомление об успехе
                    document.getElementById('action-area').innerHTML = `
                    <div class="alert alert-success mb-0">
                        <h5 class="alert-heading">${data.message}</h5>
                        <hr>
                        <p class="mb-0">Ваш баланс: <strong>${data.new_balance} ECO</strong></p>
                    </div>
                    `;

                    // Обновляем баланс в шапке сайта (если у вас там есть элемент с id="eco-balance-display")
                    const balanceEl = document.getElementById('eco-balance-display');
                    if (balanceEl) balanceEl.innerText = data.new_balance;

                } else {
                    alert(data.error || 'Произошла ошибка');
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-check2-circle me-2"></i> Я сделал это сегодня!';
                }
            })
            .catch(() => {
                alert('Сетевая ошибка, проверьте интернет');
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-check2-circle me-2"></i> Я сделал это сегодня!';
            });
    });
});