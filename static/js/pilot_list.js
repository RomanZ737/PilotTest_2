// static/js/pilot_list.js

document.addEventListener('DOMContentLoaded', function() {

    // ============================================
    // 1. Инициализация
    // ============================================
    const STORAGE_KEY = 'pilotTest_selectedPilots';
    const table = document.getElementById('pilots-table');
    const selectionPanel = document.getElementById('selection-panel');
    const selectionCount = document.getElementById('selection-count');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const selectAllBadge = document.querySelector('.select-all-badge');

    // Получаем сохранённые ID из localStorage
    let selectedIds = getStoredIds();

    // ============================================
    // 2. Функции для localStorage
    // ============================================
    function getStoredIds() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            return [];
        }
    }

    function saveStoredIds(ids) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    }

    // ============================================
    // 3. Обновление UI
    // ============================================
    function updateUI() {
        const rows = table.querySelectorAll('.pilot-row');

        rows.forEach(function(row) {
            const pilotId = parseInt(row.dataset.pilotId);
            const badge = row.querySelector('.select-badge');

            if (selectedIds.includes(pilotId)) {
                row.classList.add('table-active', 'selected');
                badge.classList.remove('badge-outline');
                badge.classList.add('bg-success');
            } else {
                row.classList.remove('table-active', 'selected');
                badge.classList.add('badge-outline');
                badge.classList.remove('bg-success');
            }
        });

        updateSelectAllBadge();
        updateSelectionPanel();
    }

    function updateSelectAllBadge() {
        if (!selectAllBadge) return;

        const rows = table.querySelectorAll('.pilot-row');
        const visibleIds = Array.from(rows).map(r => parseInt(r.dataset.pilotId));

        if (visibleIds.length === 0) {
            selectAllBadge.classList.add('badge-outline');
            selectAllBadge.classList.remove('bg-success');
            return;
        }

        const allSelected = visibleIds.every(id => selectedIds.includes(id));

        if (allSelected) {
            selectAllBadge.classList.remove('badge-outline');
            selectAllBadge.classList.add('bg-success');
        } else {
            selectAllBadge.classList.add('badge-outline');
            selectAllBadge.classList.remove('bg-success');
        }
    }

    function updateSelectionPanel() {
        const count = selectedIds.length;

        if (count > 0) {
            selectionPanel.classList.remove('d-none');
            selectionCount.textContent = count;
        } else {
            selectionPanel.classList.add('d-none');
            selectionCount.textContent = '0';
        }
    }

    // ============================================
    // 4. Обработчики выбора
    // ============================================
    if (table) {
        // Клик по бейджу выбора в строке
        table.addEventListener('click', function(e) {
            const badge = e.target.closest('.select-badge');
            if (!badge) return;

            const pilotId = parseInt(badge.dataset.pilotId);
            if (!pilotId) return;

            togglePilot(pilotId);
        });

        // Клик по бейджу "Выбрать всех"
        if (selectAllBadge) {
            selectAllBadge.addEventListener('click', function(e) {
                e.stopPropagation();

                const rows = table.querySelectorAll('.pilot-row');
                const visibleIds = Array.from(rows).map(r => parseInt(r.dataset.pilotId));

                const allSelected = visibleIds.every(id => selectedIds.includes(id));

                if (allSelected) {
                    // Снять выделение со всех видимых
                    selectedIds = selectedIds.filter(id => !visibleIds.includes(id));
                } else {
                    // Добавить всех видимых
                    visibleIds.forEach(function(id) {
                        if (!selectedIds.includes(id)) {
                            selectedIds.push(id);
                        }
                    });
                }

                saveStoredIds(selectedIds);
                updateUI();
            });
        }
    }

    function togglePilot(pilotId) {
        const index = selectedIds.indexOf(pilotId);

        if (index > -1) {
            selectedIds.splice(index, 1);
        } else {
            selectedIds.push(pilotId);
        }

        saveStoredIds(selectedIds);
        updateUI();
    }

    // ============================================
    // 5. Кнопка "Снять выделение"
    // ============================================
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', function() {
            selectedIds = [];
            saveStoredIds(selectedIds);
            updateUI();
        });
    }

    // ============================================
    // 6. Первоначальная отрисовка
    // ============================================
    updateUI();

});