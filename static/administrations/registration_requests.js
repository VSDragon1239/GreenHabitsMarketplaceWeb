/**
 * Управление пользователями + Модерация заявок
 * Модалки управляются ТОЛЬКО через Tailwind-утилиты (без кастомного CSS)
 */
(function () {
    'use strict';

    // ── Утилиты ───────────────────────────────────────────────

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            document.cookie.split(';').forEach(c => {
                c = c.trim();
                if (c.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(c.substring(name.length + 1));
                }
            });
        }
        return cookieValue;
    }

    /**
     * Показать модалку через Tailwind-классы.
     * overlayEl — внешний div (fixed inset-0)
     * contentEl — внутренний div с белым фоном (для scale-анимации)
     */
    function showModal(overlayEl, contentEl) {
        // 1. Убираем hidden, но элемент ещё прозрачный (opacity-0)
        overlayEl.classList.remove('hidden');
        // 2. Принудительный reflow — чтобы браузер отрисовал opacity-0
        void overlayEl.offsetWidth;
        // 3. Меняем opacity и scale
        overlayEl.classList.remove('opacity-0');
        overlayEl.classList.add('opacity-100');

        if (contentEl) {
            contentEl.classList.remove('scale-95', 'opacity-0');
            contentEl.classList.add('scale-100', 'opacity-100');
        }

        overlayEl.setAttribute('aria-hidden', 'false');
    }

    function hideModal(overlayEl, contentEl) {
        overlayEl.classList.remove('opacity-100');
        overlayEl.classList.add('opacity-0');

        if (contentEl) {
            contentEl.classList.remove('scale-100', 'opacity-100');
            contentEl.classList.add('scale-95', 'opacity-0');
        }

        overlayEl.setAttribute('aria-hidden', 'true');

        // Ждём завершения анимации, потом прячем окончательно
        setTimeout(() => {
            overlayEl.classList.add('hidden');
        }, 200);
    }

    function showToast(message, isSuccess = true) {
        const toast = $('#toast');
        if (!toast) return;
        const icon = $('#toastIcon');
        const msg = $('#toastMessage');

        msg.textContent = message;
        icon.textContent = isSuccess ? 'check_circle' : 'error';
        icon.className = isSuccess
            ? 'material-icons text-green-400'
            : 'material-icons text-red-400';

        toast.classList.remove('hidden');
        void toast.offsetWidth; // reflow
        toast.classList.remove('translate-y-4', 'opacity-0');
        toast.classList.add('translate-y-0', 'opacity-100');

        setTimeout(() => {
            toast.classList.remove('translate-y-0', 'opacity-100');
            toast.classList.add('translate-y-4', 'opacity-0');
            setTimeout(() => toast.classList.add('hidden'), 300);
        }, 3000);
    }

    // ── Данные из шаблона ─────────────────────────────────────
    const usersData = window.__usersData || {};
    const CSRF_TOKEN = window.__csrfToken || getCookie('csrftoken');
    const USER_SUBMIT_URL = window.__userSubmitUrl;
    const MODERATE_URL_TEMPLATE = window.__moderateUrlTemplate;

    // ══════════════════════════════════════════════════════════
    //  ПОДСИСТЕМА 1: Модерация заявок на регистрацию
    // ══════════════════════════════════════════════════════════

    const ApproveModal = {
        currentRequestId: null,
        overlay: null,
        content: null,

        init() {
            this.overlay = $('#approveModal');
            this.content = $('.approve-modal-content');
        },

        open(requestId, fio, group, email) {
            this.currentRequestId = requestId;
            $('#modal-fio').textContent = fio;
            $('#modal-group').textContent = group;
            $('#modal-email').textContent = email;
            showModal(this.overlay, this.content);
        },

        close() {
            hideModal(this.overlay, this.content);
            this.currentRequestId = null;
        },

        async confirmApprove() {
            if (!this.currentRequestId) return;

            const btn = $('#btn-final-approve');
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin material-icons text-sm">refresh</span> Создание...';

            const url = MODERATE_URL_TEMPLATE.replace('{id}', this.currentRequestId);

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': CSRF_TOKEN,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'action=approve',
                });

                const data = await res.json();

                if (data.status === 'success') {
                    this.close();
                    showToast(data.message || 'Пользователь создан', true);
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.message || 'Ошибка при одобрении', false);
                    btn.disabled = false;
                    btn.innerHTML = '<span class="material-icons text-sm">send</span> Создать и отправить';
                }
            } catch (err) {
                showToast('Ошибка сети: ' + err.message, false);
                btn.disabled = false;
                btn.innerHTML = '<span class="material-icons text-sm">send</span> Создать и отправить';
            }
        },

        bindEvents() {
            const approveBtn = $('#btn-final-approve');
            if (approveBtn) {
                approveBtn.addEventListener('click', () => this.confirmApprove());
            }
        },
    };

    async function rejectRequest(requestId) {
        if (!confirm('Вы уверены, что хотите отклонить эту заявку?')) return;

        const url = MODERATE_URL_TEMPLATE.replace('{id}', requestId);

        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=reject',
            });

            const data = await res.json();

            if (data.status === 'success') {
                showToast(data.message || 'Заявка отклонена', true);
                setTimeout(() => location.reload(), 800);
            } else {
                showToast(data.message || 'Ошибка', false);
            }
        } catch (err) {
            showToast('Ошибка сети: ' + err.message, false);
        }
    }

    // Генерация инициалов
    function initInitials() {
        $$('.initials').forEach(el => {
            const parts = (el.dataset.name || '').split(' ').filter(Boolean);
            if (parts.length >= 2) {
                el.textContent = parts[0][0] + parts[1][0];
            } else if (parts.length === 1) {
                el.textContent = parts[0].substring(0, 2);
            } else {
                el.textContent = '??';
            }
        });
    }

    // ══════════════════════════════════════════════════════════
    //  ПОДСИСТЕМА 2: Управление пользователями (CRUD)
    // ══════════════════════════════════════════════════════════

    const UserModal = {
        overlay: null,
        content: null,

        init() {
            this.overlay = $('#userModal');
            this.content = $('.user-modal-content');
        },

        openCreate() {
            const form = $('#userForm');
            form.reset();
            this.clearErrors();

            $('#userModalTitle').textContent = 'Новый пользователь';
            $('#formAction').value = 'create';
            $('#formUserId').value = '';
            $('#passwordHint').textContent = '(обязательно)';
            $('#f_password').setAttribute('required', 'required');
            $('#f_password').value = '';

            $$('.group-checkbox').forEach(cb => {
                cb.checked = false;
            });
            this.updateGroupLabels();

            $('#f_is_active').checked = true;
            $('#f_is_staff').checked = false;
            $('#f_is_superuser').checked = false;

            showModal(this.overlay, this.content);
        },

        openEdit(userId) {
            const form = $('#userForm');
            form.reset();
            this.clearErrors();

            const data = usersData[userId];
            if (!data) {
                showToast('Данные пользователя не найдены', false);
                return;
            }

            $('#userModalTitle').textContent = 'Редактирование пользователя';
            $('#formAction').value = 'edit';
            $('#formUserId').value = userId;

            $('#passwordHint').textContent = '(оставьте пустым, чтобы не менять)';
            $('#f_password').removeAttribute('required');
            $('#f_password').value = '';

            $('#f_username').value = data.username;
            $('#f_first_name').value = data.first_name;
            $('#f_last_name').value = data.last_name;
            $('#f_phone').value = data.phone;
            $('#f_description').value = data.description;
            $('#f_is_active').checked = data.is_active;
            $('#f_is_staff').checked = data.is_staff;
            $('#f_is_superuser').checked = data.is_superuser;

            $$('.group-checkbox').forEach(cb => {
                cb.checked = data.groups.includes(parseInt(cb.value));
            });
            this.updateGroupLabels();

            showModal(this.overlay, this.content);
        },

        close() {
            hideModal(this.overlay, this.content);
        },

        clearErrors() {
            const errorsEl = $('#userFormErrors');
            if (errorsEl) errorsEl.classList.add('hidden');
            const listEl = $('#userErrorList');
            if (listEl) listEl.innerHTML = '';
            $$('.field-error').forEach(el => el.classList.remove('field-error'));
        },

        showErrors(errors) {
            const listEl = $('#userErrorList');
            if (!listEl) return;
            listEl.innerHTML = '';

            if (typeof errors === 'string') {
                const li = document.createElement('li');
                li.textContent = errors;
                listEl.appendChild(li);
            } else if (typeof errors === 'object') {
                for (const [field, messages] of Object.entries(errors)) {
                    (Array.isArray(messages) ? messages : [messages]).forEach(msg => {
                        const li = document.createElement('li');
                        li.textContent = msg;
                        listEl.appendChild(li);
                    });
                    const input = $(`#f_${field}`) || $(`[name="${field}"]`);
                    if (input) input.classList.add('field-error');
                }
            }

            $('#userFormErrors').classList.remove('hidden');
        },

        updateGroupLabels() {
            $$('.group-checkbox-label').forEach(label => {
                const cb = label.querySelector('.group-checkbox');
                label.classList.toggle('group-selected', cb && cb.checked);
            });
        },

        async submit(e) {
            e.preventDefault();
            this.clearErrors();

            const btn = $('#submitBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin material-icons text-sm">refresh</span> Сохранение...';

            const formData = new FormData(e.target);

            try {
                const response = await fetch(USER_SUBMIT_URL, {
                    method: 'POST',
                    body: formData,
                    headers: {'X-CSRFToken': CSRF_TOKEN},
                });

                const data = await response.json();

                if (data.success) {
                    this.close();
                    showToast(data.message, true);
                    setTimeout(() => location.reload(), 1000);
                } else {
                    this.showErrors(data.errors || data.error || 'Произошла ошибка');
                    showToast(data.error || 'Ошибка валидации', false);
                }
            } catch (error) {
                showToast('Ошибка сети: ' + error.message, false);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span class="material-icons text-sm">save</span> Сохранить';
            }
        },
    };

    // ── Модалка удаления ──

    const DeleteModal = {
        overlay: null,
        content: null,

        init() {
            this.overlay = $('#deleteModal');
            this.content = $('.delete-modal-content');
        },

        open(userId, username) {
            $('#deleteUserId').value = userId;
            $('#deleteUserName').textContent = username;
            showModal(this.overlay, this.content);
        },

        close() {
            hideModal(this.overlay, this.content);
        },

        async submit(e) {
            e.preventDefault();

            const formData = new FormData(e.target);
            const userId = formData.get('user_id');

            try {
                const response = await fetch(USER_SUBMIT_URL, {
                    method: 'POST',
                    body: formData,
                    headers: {'X-CSRFToken': CSRF_TOKEN},
                });

                const data = await response.json();

                if (data.success) {
                    this.close();
                    showToast(data.message, true);

                    const row = document.querySelector(`.user-row[data-user-id="${userId}"]`);
                    if (row) {
                        row.classList.add('deleting');
                        setTimeout(() => row.remove(), 400);
                    }
                } else {
                    this.close();
                    showToast(data.error || 'Произошла ошибка', false);
                }
            } catch (error) {
                showToast('Ошибка сети: ' + error.message, false);
            }
        },
    };

    // ══════════════════════════════════════════════════════════
    //  ГЛОБАЛЬНОЕ ДЕЛЕГИРОВАНИЕ СОБЫТИЙ
    // ══════════════════════════════════════════════════════════

    document.addEventListener('click', function (e) {
        const trigger = e.target.closest('[data-action]');
        if (!trigger) return;

        const action = trigger.dataset.action;

        switch (action) {
            // ── Модерация заявок ──
            case 'open-approve-modal':
                ApproveModal.open(
                    parseInt(trigger.dataset.requestId),
                    trigger.dataset.fio,
                    trigger.dataset.group,
                    trigger.dataset.email
                );
                break;

            case 'close-approve-modal':
                ApproveModal.close();
                break;

            case 'reject-request':
                rejectRequest(parseInt(trigger.dataset.requestId));
                break;

            // ── Управление пользователями ──
            case 'open-user-create':
                UserModal.openCreate();
                break;

            case 'open-user-edit':
                UserModal.openEdit(parseInt(trigger.dataset.userId));
                break;

            case 'close-user-modal':
                UserModal.close();
                break;

            case 'confirm-user-delete':
                DeleteModal.open(
                    parseInt(trigger.dataset.userId),
                    trigger.dataset.username
                );
                break;

            case 'close-delete-modal':
                DeleteModal.close();
                break;
        }
    });

    // Подсветка чекбоксов групп
    document.addEventListener('change', function (e) {
        if (e.target.classList.contains('group-checkbox')) {
            UserModal.updateGroupLabels();
        }
    });

    // Закрытие по Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if ($('#approveModal') && !$('#approveModal').classList.contains('hidden')) {
                ApproveModal.close();
            }
            if ($('#userModal') && !$('#userModal').classList.contains('hidden')) {
                UserModal.close();
            }
            if ($('#deleteModal') && !$('#deleteModal').classList.contains('hidden')) {
                DeleteModal.close();
            }
        }
    });

    // ══════════════════════════════════════════════════════════
    //  ИНИЦИАЛИЗАЦИЯ
    // ══════════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', function () {
        initInitials();
        ApproveModal.init();
        ApproveModal.bindEvents();
        UserModal.init();
        DeleteModal.init();

        const userForm = $('#userForm');
        if (userForm) userForm.addEventListener('submit', (e) => UserModal.submit(e));

        const deleteForm = $('#deleteForm');
        if (deleteForm) deleteForm.addEventListener('submit', (e) => DeleteModal.submit(e));
    });

})();