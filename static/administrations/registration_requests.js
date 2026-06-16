/**
 * Управление пользователями + Модерация заявок
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

    function showModal(overlayEl, contentEl) {
        overlayEl.classList.remove('hidden');
        void overlayEl.offsetWidth;
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
        setTimeout(() => overlayEl.classList.add('hidden'), 200);
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
        void toast.offsetWidth;
        toast.classList.remove('translate-y-4', 'opacity-0');
        toast.classList.add('translate-y-0', 'opacity-100');

        setTimeout(() => {
            toast.classList.remove('translate-y-0', 'opacity-100');
            toast.classList.add('translate-y-4', 'opacity-0');
            setTimeout(() => toast.classList.add('hidden'), 300);
        }, 3000);
    }

    function getRawPhone(formatted) {
        return (formatted || '').replace(/\D/g, '');
    }

    // ── Данные из шаблона ─────────────────────────────────────
    const usersData = window.__usersData || {};
    const CSRF_TOKEN = window.__csrfToken || getCookie('csrftoken');
    const USER_SUBMIT_URL = window.__userSubmitUrl;
    const MODERATE_URL_TEMPLATE = window.__moderateUrlTemplate;

    // ══════════════════════════════════════════════════════════
    //  ПОДСИСТЕМА 1: Модерация заявок
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
    //  ПОДСИСТЕMA 2: Управление пользователями (CRUD)
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
            $('#f_is_partner').checked = false;
            $('#f_partner_name').value = '';
            $('#partnerNameGroup').classList.add('hidden');
            $('#f_partner_name').removeAttribute('required');

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

            // TODO: Если у пользователя нет Profile (автосозданный суперпользователь),
            //       POST-запрос на редактирование вернёт 500 (RelatedObjectDoesNotExist).
            //       Исправить в бэкенде: Profile.objects.get_or_create(user=user)

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

            // Партнёр
            const isPartner = data.is_partner;
            $('#f_is_partner').checked = isPartner;
            if (isPartner) {
                $('#partnerNameGroup').classList.remove('hidden');
                $('#f_partner_name').setAttribute('required', 'required');
                $('#f_partner_name').value = data.partner_name;
            } else {
                $('#partnerNameGroup').classList.add('hidden');
                $('#f_partner_name').removeAttribute('required');
                $('#f_partner_name').value = '';
            }

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

            // Преобразуем отформатированный телефон в чистый номер
            const rawPhone = getRawPhone($('#f_phone').value);
            formData.set('phone', rawPhone);

            // Валидация: партнёр без названия
            if ($('#f_is_partner').checked && !$('#f_partner_name').value.trim()) {
                this.showErrors({'partner_name': ['Укажите название организации партнёра']});
                btn.disabled = false;
                btn.innerHTML = '<span class="material-icons text-sm">save</span> Сохранить';
                return;
            }

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
    //  ФИЛЬТРАЦИЯ И СОРТИРОВКА ТАБЛИЦЫ
    // ══════════════════════════════════════════════════════════

    const TableFilter = {
        init() {
            $('#searchInput')?.addEventListener('input', () => this.apply());
            $('#filterRole')?.addEventListener('change', () => this.apply());
            $('#filterStatus')?.addEventListener('change', () => this.apply());
            $('#sortBy')?.addEventListener('change', () => this.apply());
            $('#resetFilters')?.addEventListener('click', () => this.reset());
        },

        /**
         * Парсит data-roles в массив, убирая пустые элементы и пробелы.
         * data-roles="Участники,is_superuser" → ["Участники", "is_superuser"]
         * data-roles=",is_superuser"           → ["is_superuser"]
         */
        _parseRoles(raw) {
            if (!raw) return [];
            return raw.split(',').map(r => r.trim()).filter(Boolean);
        },

        apply() {
            const search = ($('#searchInput')?.value || '').toLowerCase().trim();
            const role = $('#filterRole')?.value || '';
            const status = $('#filterStatus')?.value || '';
            const sortBy = $('#sortBy')?.value || 'name_asc';

            const rows = Array.from($$('.user-row'));
            let visibleCount = 0;

            rows.forEach(row => {
                const name = (row.dataset.name || '').toLowerCase();
                const email = (row.dataset.email || '').toLowerCase();
                const phone = (row.dataset.phone || '').toLowerCase();
                const rowRoles = this._parseRoles(row.dataset.roles);
                const rowStatus = row.dataset.active || '';

                // Фильтр поиска
                const matchSearch = !search ||
                    name.includes(search) ||
                    email.includes(search) ||
                    phone.includes(search);

                // Фильтр по роли — ищем точное совпадение в массиве
                const matchRole = !role || rowRoles.includes(role);

                // Фильтр по статусу
                const matchStatus = !status || rowStatus === status;

                const visible = matchSearch && matchRole && matchStatus;
                row.style.display = visible ? '' : 'none';
                if (visible) visibleCount++;
            });

            // Сортировка видимых строк
            const tbody = $('#usersTableBody');
            const visibleRows = rows.filter(r => r.style.display !== 'none');

            visibleRows.sort((a, b) => {
                switch (sortBy) {
                    case 'name_asc':
                        return (a.dataset.name || '').localeCompare(b.dataset.name || '', 'ru');
                    case 'name_desc':
                        return (b.dataset.name || '').localeCompare(a.dataset.name || '', 'ru');
                    case 'balance_asc':
                        return (parseInt(a.dataset.balance) || 0) - (parseInt(b.dataset.balance) || 0);
                    case 'balance_desc':
                        return (parseInt(b.dataset.balance) || 0) - (parseInt(a.dataset.balance) || 0);
                    case 'date_asc':
                        return (a.dataset.date || '').localeCompare(b.dataset.date || '');
                    case 'date_desc':
                        return (b.dataset.date || '').localeCompare(a.dataset.date || '');
                    default:
                        return 0;
                }
            });

            visibleRows.forEach(row => tbody.appendChild(row));

            // Пустое состояние
            const emptyState = $('#emptyState');
            if (emptyState) {
                emptyState.classList.toggle('hidden', visibleCount > 0);
            }
        },

        reset() {
            if ($('#searchInput')) $('#searchInput').value = '';
            if ($('#filterRole')) $('#filterRole').value = '';
            if ($('#filterStatus')) $('#filterStatus').value = '';
            if ($('#sortBy')) $('#sortBy').value = 'name_asc';
            this.apply();
        },
    };

    // ══════════════════════════════════════════════════════════
    //  МАСКА ТЕЛЕФОНА: +7 (XXX) XXX-XX-XX
    // ══════════════════════════════════════════════════════════

    function initPhoneMask() {
        const phoneInput = $('#f_phone');
        if (!phoneInput) return;

        phoneInput.addEventListener('input', function () {
            let value = this.value.replace(/\D/g, '');

            if (value.startsWith('8')) value = '7' + value.slice(1);
            if (value.length > 0 && !value.startsWith('7')) value = '7' + value;

            let formatted = '';
            if (value.length > 0) formatted = '+' + value[0];
            if (value.length > 1) formatted += ' (' + value.substring(1, 4);
            if (value.length > 4) formatted += ') ' + value.substring(4, 7);
            if (value.length > 7) formatted += '-' + value.substring(7, 9);
            if (value.length > 9) formatted += '-' + value.substring(9, 11);

            this.value = formatted;
        });

        phoneInput.addEventListener('keydown', function (e) {
            const cursorPos = this.selectionStart;
            if ((e.key === 'Backspace' || e.key === 'Delete') && cursorPos <= 2) {
                e.preventDefault();
            }
        });
    }

    // ══════════════════════════════════════════════════════════
    //  ДИНАМИЧЕСКОЕ ПОЛЕ ПАРТНЁРА
    // ══════════════════════════════════════════════════════════

    function initPartnerToggle() {
        const checkbox = $('#f_is_partner');
        const group = $('#partnerNameGroup');
        const nameInput = $('#f_partner_name');
        if (!checkbox || !group) return;

        checkbox.addEventListener('change', function () {
            if (this.checked) {
                group.classList.remove('hidden');
                nameInput.setAttribute('required', 'required');
            } else {
                group.classList.add('hidden');
                nameInput.removeAttribute('required');
                nameInput.value = '';
            }
        });
    }

    // ══════════════════════════════════════════════════════════
    //  ГЛОБАЛЬНОЕ ДЕЛЕГИРОВАНИЕ СОБЫТИЙ
    // ══════════════════════════════════════════════════════════

    document.addEventListener('click', function (e) {
        const trigger = e.target.closest('[data-action]');
        if (!trigger) return;

        const action = trigger.dataset.action;

        switch (action) {
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

    document.addEventListener('change', function (e) {
        if (e.target.classList.contains('group-checkbox')) {
            UserModal.updateGroupLabels();
        }
    });

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
        TableFilter.init();
        initPhoneMask();
        initPartnerToggle();

        const userForm = $('#userForm');
        if (userForm) userForm.addEventListener('submit', (e) => UserModal.submit(e));

        const deleteForm = $('#deleteForm');
        if (deleteForm) deleteForm.addEventListener('submit', (e) => DeleteModal.submit(e));
    });

})();