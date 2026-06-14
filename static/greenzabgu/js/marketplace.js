// 1. Фильтрация по категориям
document.querySelectorAll('.category-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        const category = this.getAttribute('data-category');
        document.querySelectorAll('.offer-card').forEach(card => {
            if (category === 'all' || card.getAttribute('data-category') === category) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
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

// 2. Обмен баллов
function exchangeOffer(offerId) {
    const btn = event.target;
    if (!btn.classList.contains('exchange-btn')) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span> Обмен...';

    fetch(`/main/green-zabgu/marketplace/exchange/${offerId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                // Обновляем баланс в шапке
                const balanceEl = document.getElementById('eco-balance-display');
                if (balanceEl) balanceEl.innerText = data.new_balance;

                // Показываем модалку
                document.getElementById('modal-partner-name').innerText = data.partner_name;
                document.getElementById('modal-promo-code').innerText = data.promo_code;
                document.getElementById('successModal').style.display = 'flex';

                // Меняем кнопку на карточке
                btn.innerText = 'Получено';
                btn.className = 'w-full bg-gray-200 text-gray-500 px-4 py-2 rounded-lg font-semibold text-sm cursor-default';

                // Добавляем промокод в список "Мои промокоды" без перезагрузки
                const promoList = document.getElementById('promo-list');
                const newPromo = document.createElement('div');
                newPromo.className = 'flex items-center justify-between border-b border-gray-100 pb-3 mb-3';
                newPromo.innerHTML = `
                    <div class="flex items-center">
                        <i class="material-icons text-2xl eco-green mr-3">confirmation_number</i>
                        <div>
                            <div class="text-gray-800 font-semibold">${data.message.split(':')[1]}</div>
                            <div class="text-gray-500 text-sm">От: ${data.partner_name}</div>
                        </div>
                    </div>
                    <div class="bg-green-50 px-3 py-1 rounded text-xs font-bold eco-green tracking-wider">${data.promo_code}</div>
                `;
                promoList.prepend(newPromo);

            } else {
                alert(data.error || 'Ошибка');
                btn.disabled = false;
                btn.innerHTML = 'Обменять';
            }
        });
}

function closeModal() {
    document.getElementById('successModal').style.display = 'none';
}