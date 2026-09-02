// static/js/q_detail.js

document.addEventListener('DOMContentLoaded', function() {
    // Универсальное модальное окно
    const actionModal = document.getElementById('actionModal');
    if (actionModal) {
        actionModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const url = button.getAttribute('data-action-url');
            const title = button.getAttribute('data-action-title');
            const text = button.getAttribute('data-action-text');
            const btnClass = button.getAttribute('data-btn-class') || 'btn-primary';
            const btnText = button.getAttribute('data-btn-text') || 'Подтвердить';
            const commentText = button.getAttribute('data-comment-text') || '';

            const form = document.getElementById('actionForm');
            if (form) form.action = url;

            const redirectTo = button.getAttribute('data-redirect-to') || '';
            const redirectInput = document.getElementById('redirectToInput');
            if (redirectInput) redirectInput.value = redirectTo;

            document.getElementById('actionModalLabel').textContent = title;
            document.getElementById('actionModalText').textContent = text;

            const submitBtn = document.getElementById('actionSubmitBtn');
            submitBtn.textContent = btnText;
            submitBtn.className = 'btn ' + btnClass;

            const commentField = document.getElementById('actionComment');
            if (commentField) {
                commentField.value = commentText;
                commentField.placeholder = commentText ? 'Измените текст комментария...' : 'Опишите причину действия...';
            }

            const questionText = button.getAttribute('data-question-text') || '';
            const questionInfo = document.getElementById('actionModalQuestion');
            if (questionInfo) questionInfo.textContent = questionText;
        });
    }

    // Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Подтверждение действий
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) e.preventDefault();
        });
    });

    // Читать далее для комментариев
    document.querySelectorAll('.comment-textarea').forEach(function(textarea) {
        const commentItem = textarea.closest('.comment-item');
        if (!commentItem) return;
        const toggleBtn = commentItem.querySelector('.comment-toggle-btn');
        if (!toggleBtn) return;

        const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 21;
        const threeLinesHeight = lineHeight * 3;
        const originalRows = textarea.rows;
        textarea.rows = 0;
        textarea.style.height = 'auto';
        const fullHeight = textarea.scrollHeight;
        textarea.rows = originalRows;
        textarea.style.height = '';

        if (fullHeight > threeLinesHeight + 5) toggleBtn.style.display = 'inline-block';

        let isExpanded = false;
        toggleBtn.addEventListener('click', function() {
            isExpanded = !isExpanded;
            if (isExpanded) {
                textarea.style.height = fullHeight + 'px';
                this.textContent = 'Свернуть';
            } else {
                textarea.style.height = threeLinesHeight + 'px';
                this.textContent = 'Читать далее';
            }
        });
    });

    // Прокрутка к истории
    function scrollToHistory() {
        const historyBlock = document.getElementById('history');
        if (historyBlock) {
            const offset = 100;
            const elementPosition = historyBlock.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - offset;
            window.scrollTo({top: offsetPosition, behavior: 'smooth'});
        }
    }
    if (window.location.hash === '#history') setTimeout(scrollToHistory, 200);

    // Активация вкладки по параметру
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('tab') === 'draft') {
        const draftTab = document.getElementById('draft-tab');
        if (draftTab) new bootstrap.Tab(draftTab).show();
    }
    if (urlParams.get('tab') === 'paraphrase') {
        const paraphraseTab = document.getElementById('paraphrase-tab');
        if (paraphraseTab) new bootstrap.Tab(paraphraseTab).show();
    }

    // Переключение вкладок и отметка просмотра
    document.querySelectorAll('#questionTabs button[data-bs-toggle="tab"]').forEach(function(tab) {
        tab.addEventListener('shown.bs.tab', function() {
            const tabType = this.dataset.tabType;
            const pk = this.dataset.questionPk;

            // Скрываем бейдж на текущей вкладке сразу
            const badge = this.querySelector('.new-badge');
            if (badge) {
                badge.style.display = 'none';
            }

            if (tabType && pk) {
                fetch(`/questions/question/${pk}/mark-viewed/${tabType}/`, {
                    method: 'POST',
                    headers: {'X-CSRFToken': getCookie('csrftoken')}
                }).then(response => response.json())
                  .then(data => {
                      if (data.status === 'ok') {
                          fetch('/ajax/notifications/')
                              .then(res => res.json())
                              .then(flags => {
                                  updateNavBarBadges(flags);
                              });
                      }
                  });
            }
        });
    });

    function updateNavBarBadges(flags) {
        const questionsLink = document.querySelector('a[href*="/questions/"]');
        if (questionsLink) {
            const existingBadge = questionsLink.querySelector('.badge');
            if (flags.new_questions_count) {
                if (!existingBadge) {
                    const span = document.createElement('span');
                    span.className = 'badge bg-warning text-dark ms-1';
                    span.textContent = 'new';
                    questionsLink.appendChild(span);
                }
            } else {
                if (existingBadge) existingBadge.remove();
            }
        }

        const usersLink = document.querySelector('a[href*="/users/"]');
        if (usersLink) {
            const existingBadge = usersLink.querySelector('.badge');
            if (flags.new_users_count > 0) {
                if (!existingBadge) {
                    const span = document.createElement('span');
                    span.className = 'badge bg-warning text-dark ms-1';
                    span.textContent = 'new';
                    usersLink.appendChild(span);
                }
            } else {
                if (existingBadge) existingBadge.remove();
            }
        }
    }
});

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