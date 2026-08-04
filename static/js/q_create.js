console.log('Скрипт загружен');

// ========================================
// Глобальная функция удаления изображения
// ========================================
function removeImage(inputId, previewId, removeBtnId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const removeBtn = removeBtnId ? document.getElementById(removeBtnId) : null;

    if (input) input.value = '';
    if (preview) {
        preview.src = '#';
        preview.style.display = 'none';
    }
    if (removeBtn) removeBtn.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded сработал');

    // ========================================
    // Превью изображений
    // ========================================

    function setupImagePreview(inputId, previewId, removeBtnId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        const removeBtn = removeBtnId ? document.getElementById(removeBtnId) : null;

        if (!input || !preview) return;

        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                if (!file.type.startsWith('image/')) {
                    preview.src = '#';
                    preview.style.display = 'none';
                    if (removeBtn) removeBtn.style.display = 'none';
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    preview.classList.remove('zoomed');
                    if (removeBtn) removeBtn.style.display = 'inline-block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    setupImagePreview('id_question_img', 'question-img-preview', 'remove-question-img');
    setupImagePreview('id_comment_img', 'comment-img-preview', 'remove-comment-img');

    // ========================================
    // Модалка создания темы
    // ========================================

    const themeForm = document.getElementById('theme-create-form');
    const themeSelect = document.querySelector('[data-theme-select="true"]');
    const addThemeBtn = document.getElementById('add-theme-btn');
    const modalBody = document.getElementById('theme-modal-body');

    if (!themeForm || !themeSelect) {
        console.warn('Элементы темы не найдены — модалка не будет работать');
    } else {
        const createUrl = addThemeBtn ? addThemeBtn.dataset.createUrl : '/questions/themes/create/';
        const originalModalHtml = modalBody ? modalBody.innerHTML : '';

        themeForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(themeForm);
            const submitBtn = themeForm.querySelector('button[type="submit"]');

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Создание...';

            fetch(createUrl, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const option = new Option(data.name, data.id);
                    themeSelect.add(option);
                    themeSelect.value = data.id;

                    const modal = bootstrap.Modal.getInstance(document.getElementById('themeModal'));
                    modal.hide();

                    themeForm.reset();
                    if (modalBody) {
                        modalBody.innerHTML = originalModalHtml;
                    }
                } else {
                    if (modalBody && data.html) {
                        modalBody.innerHTML = data.html;
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Произошла ошибка при создании темы.');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> Создать';
            });
        });

        const themeModal = document.getElementById('themeModal');
        themeModal.addEventListener('hidden.bs.modal', function() {
            themeForm.reset();
            if (modalBody) {
                modalBody.innerHTML = originalModalHtml;
            }
        });
    }

    // ========================================
    // Динамическое управление ответами
    // ========================================

    const answersContainer = document.getElementById('answers-container');
    const addAnswerBtn = document.getElementById('add-answer-btn');
    const emptyTemplate = document.getElementById('empty-form-template');
    const totalFormsInput = document.getElementById('id_answers-TOTAL_FORMS');
    const qKindSelect = document.getElementById('id_q_kind');

    if (!answersContainer || !addAnswerBtn || !emptyTemplate || !totalFormsInput) {
        console.warn('Элементы для управления ответами не найдены');
    } else {

        const MAX_ANSWERS = 10;

        function updateAnswerNumbers() {
            const rows = answersContainer.querySelectorAll('.answer-form-row');
            let visibleIndex = 0;
            rows.forEach(row => {
                if (!row.classList.contains('d-none')) {
                    visibleIndex++;
                    const badge = row.querySelector('.answer-number');
                    if (badge) badge.textContent = visibleIndex;
                }
            });
        }

        function updateAnswerNameIndexes() {
            const rows = answersContainer.querySelectorAll('.answer-form-row');
            rows.forEach((row, i) => {
                row.querySelectorAll('[name]').forEach(input => {
                    const name = input.getAttribute('name');
                    if (name && name.includes('__prefix__')) return;
                    const newName = name.replace(/answers-\d+-/, `answers-${i}-`);
                    input.setAttribute('name', newName);
                });
                const idHidden = row.querySelector('input[id*="id_answers-"]');
                if (idHidden) {
                    idHidden.setAttribute('id', `id_answers-${i}-id`);
                }
            });
            totalFormsInput.value = rows.length;
        }

        function updateCorrectInputType(row) {
            const qKind = qKindSelect ? qKindSelect.value : 'SINGLE';
            const badge = row.querySelector('.correct-badge');
            if (badge) {
                badge.dataset.type = qKind === 'MULTY' ? 'checkbox' : 'radio';
            }
        }

        function updateAllCorrectInputTypes() {
            const qKind = qKindSelect ? qKindSelect.value : 'SINGLE';
            const rows = answersContainer.querySelectorAll('.answer-form-row');

            rows.forEach(row => {
                updateCorrectInputType(row);

                // При переключении на SINGLE сбрасываем все выборы
                if (qKind === 'SINGLE') {
                    row.classList.remove('list-group-item-success');
                    const badge = row.querySelector('.correct-badge');
                    const hidden = row.querySelector('.correct-input-hidden');
                    if (badge) {
                        badge.classList.remove('bg-success');
                        badge.classList.add('badge-outline');
                    }
                    if (hidden) hidden.value = '';
                }
            });
        }

        function updateRemoveButtons() {
            const visibleRows = Array.from(answersContainer.querySelectorAll('.answer-form-row'))
                .filter(r => !r.classList.contains('d-none'));

            visibleRows.forEach(row => {
                const removeBtn = row.querySelector('.remove-answer-btn');
                if (removeBtn) {
                    removeBtn.style.display = visibleRows.length <= 2 ? 'none' : '';
                }
            });
        }

        function addAnswerRow() {
            // Сначала ищем скрытую строку — переиспользуем
            const allRows = answersContainer.querySelectorAll('.answer-form-row');
            let reused = false;
            for (let row of allRows) {
                if (row.classList.contains('d-none')) {
                    row.classList.remove('d-none');
                    row.classList.remove('list-group-item-success');
                    row.querySelector('.delete-input').value = '';
                    row.querySelectorAll('input[type="text"]').forEach(input => input.value = '');
                    // Сбрасываем бейдж правильного ответа
                    const badge = row.querySelector('.correct-badge');
                    const hidden = row.querySelector('.correct-input-hidden');
                    if (badge) {
                        badge.classList.remove('bg-success');
                        badge.classList.add('badge-outline');
                    }
                    if (hidden) hidden.value = '';
                    updateCorrectInputType(row);
                    reused = true;
                    break;
                }
            }

            if (!reused) {
                if (allRows.length >= MAX_ANSWERS) {
                    alert(`Максимальное количество ответов: ${MAX_ANSWERS}`);
                    return;
                }

                const templateRow = emptyTemplate.querySelector('.answer-form-row');
                const newRow = templateRow.cloneNode(true);
                const newIndex = allRows.length;

                newRow.querySelectorAll('[name]').forEach(input => {
                    const name = input.getAttribute('name');
                    if (name) {
                        input.setAttribute('name', name.replace('__prefix__', newIndex));
                    }
                });
                const idHidden = newRow.querySelector('input[name*="-id"]');
                if (idHidden) {
                    idHidden.setAttribute('id', `id_answers-${newIndex}-id`);
                }
                newRow.querySelectorAll('input[type="text"]').forEach(input => input.value = '');
                newRow.querySelectorAll('[disabled]').forEach(input => input.removeAttribute('disabled'));
                newRow.querySelector('.correct-input-hidden').value = '';
                const badge = newRow.querySelector('.correct-badge');
                if (badge) {
                    badge.classList.add('badge-outline');
                }
                updateCorrectInputType(newRow);
                answersContainer.appendChild(newRow);
                totalFormsInput.value = allRows.length + 1;
            }

            updateAnswerNumbers();
            updateRemoveButtons();

            const visibleCount = Array.from(answersContainer.querySelectorAll('.answer-form-row'))
                .filter(r => !r.classList.contains('d-none')).length;
            addAnswerBtn.disabled = visibleCount >= MAX_ANSWERS;
        }

        function deleteAnswerRow(deleteBtn) {
            const row = deleteBtn.closest('.answer-form-row');
            const deleteInput = row.querySelector('.delete-input');
            if (deleteInput) {
                deleteInput.value = 'on';
            }
            row.classList.add('d-none');
            row.classList.remove('list-group-item-success');
            updateAnswerNumbers();
            updateRemoveButtons();
            addAnswerBtn.disabled = false;
        }

        // Кнопка "Добавить ответ"
        addAnswerBtn.addEventListener('click', addAnswerRow);

        // Клик по бейджу "правильный ответ" или кнопке удаления
        answersContainer.addEventListener('click', function(e) {
            // Сначала проверяем кнопку удаления
            const deleteBtn = e.target.closest('.remove-answer-btn');
            if (deleteBtn) {
                deleteAnswerRow(deleteBtn);
                return;
            }

            // Затем проверяем бейдж правильного ответа
            const badge = e.target.closest('.correct-badge');
            if (!badge) return;

            const row = badge.closest('.answer-form-row');
            const hiddenInput = row.querySelector('.correct-input-hidden');
            const qKind = qKindSelect ? qKindSelect.value : 'SINGLE';

            if (qKind === 'SINGLE') {
                // Сбрасываем все строки
                const allRows = answersContainer.querySelectorAll('.answer-form-row');
                allRows.forEach(r => r.classList.remove('list-group-item-success'));
                const allBadges = answersContainer.querySelectorAll('.correct-badge');
                const allHidden = answersContainer.querySelectorAll('.correct-input-hidden');
                allBadges.forEach(b => {
                    b.classList.remove('bg-success');
                    b.classList.add('badge-outline');
                });
                allHidden.forEach(h => h.value = '');

                // Включаем текущую
                row.classList.add('list-group-item-success');
                badge.classList.remove('badge-outline');
                badge.classList.add('bg-success');
                hiddenInput.value = 'true';
            } else {
                // MULTY: переключаем текущий
                if (badge.classList.contains('bg-success')) {
                    row.classList.remove('list-group-item-success');
                    badge.classList.remove('bg-success');
                    badge.classList.add('badge-outline');
                    hiddenInput.value = '';
                } else {
                    row.classList.add('list-group-item-success');
                    badge.classList.remove('badge-outline');
                    badge.classList.add('bg-success');
                    hiddenInput.value = 'true';
                }
            }
        });

        // Смена SINGLE/MULTY
        if (qKindSelect) {
            qKindSelect.addEventListener('change', updateAllCorrectInputTypes);
        }

        // Перед отправкой формы обновляем индексы
        const form = document.querySelector('form');
        form.addEventListener('submit', function() {
            updateAnswerNameIndexes();
        });

        // При загрузке
        updateRemoveButtons();

    }

});