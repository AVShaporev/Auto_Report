document.addEventListener('DOMContentLoaded', function() {
    // Обработчики для поиска в dropdown
    const setupDropdownSearch = (searchId, listId) => {
        const searchInput = document.getElementById(searchId);
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                const filter = this.value.toLowerCase();
                const items = document.querySelectorAll(`#${listId} .dropdown-item`);
                
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(filter) ? 'block' : 'none';
                });
            });
        }
    };

    // Инициализация поиска для всех dropdown
    setupDropdownSearch('specJobTitleSearch', 'job-titles-list');
    setupDropdownSearch('BankSearch', 'banks-list');

    // Обработчики для кнопок "Создать новую должность" и "Создать новый банк"
    document.querySelectorAll('#job-titles-list button[value="create"], #banks-list button[value="create"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const modalId = this.closest('#job-titles-list') ? 'spec_job_title_Modal' : 'bank_Modal';
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
        });
    });
});