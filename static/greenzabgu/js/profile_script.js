// (function () {
//     const logoutBtn = document.getElementById('logoutBtn');
//     const modal = document.getElementById('logoutModal');
//     const form = document.getElementById('logoutForm');
//     const confirmBtn = document.getElementById('confirmLogout');
//     const cancelBtn = document.getElementById('cancelLogout');
//     const modalContent = modal.querySelector('.modal-content');
//
//     // Открыть модалку
//     logoutBtn.addEventListener('click', () => {
//         modal.style.display = 'block';
//         // Зафиксировать фокус внутри
//         modalContent.focus();
//     });
//
//     // Подтверждение — отправляем форму POST
//     confirmBtn.addEventListener('click', () => {
//         form.submit();
//     });
//
//     // Отмена — закрываем модалку
//     function closeModal() {
//         modal.style.display = 'none';
//         logoutBtn.focus();
//     }
//
//     cancelBtn.addEventListener('click', closeModal);
//
//     // Закрытие по Esc и клику по фону
//     modal.addEventListener('click', (e) => {
//         if (e.target === modal || e.target.classList.contains('modal-backdrop')) {
//             closeModal();
//         }
//     });
//     document.addEventListener('keydown', (e) => {
//         if (e.key === 'Escape' && modal.style.display === 'block') {
//             closeModal();
//         }
//     });
// })();
(function () {
    // Получаем элементы из DOM
    const logoutBtn = document.getElementById('logoutBtn'); // Ваша кнопка вызова из профиля
    const modal = document.getElementById('logoutModal');
    const form = document.getElementById('logoutForm');
    const confirmBtn = document.getElementById('confirmLogout');
    const cancelBtn = document.getElementById('cancelLogout');
    const crossBtn = document.getElementById('closeModalCross');
    const modalContent = modal.querySelector('.modal-content');

    // Открыть модальное окно
    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        modal.classList.remove('hidden'); // Показываем окно через Tailwind
        modalContent.focus(); // Переводим фокус для доступности
    });

    // Функция закрытия окна
    function closeModal() {
        modal.classList.add('hidden'); // Скрываем окно
        logoutBtn.focus(); // Возвращаем фокус на кнопку вызова
    }

    // Закрытие только по клику на "Отмена" или "Крестик"
    cancelBtn.addEventListener('click', closeModal);
    crossBtn.addEventListener('click', closeModal);

    // Подтверждение — отправка POST-формы на сервер
    confirmBtn.addEventListener('click', () => {
        form.submit();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            closeModal();
        }
    });
})();
