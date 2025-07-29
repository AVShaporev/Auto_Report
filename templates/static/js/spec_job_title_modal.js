document.addEventListener('DOMContentLoaded', function() {

        // Элементы для должностей
        const dropdownBtn = document.getElementById('specJobTitleBtn');
        const searchInput = document.getElementById('specJobTitleSearch');
        const hiddenInput = document.getElementById('selectedSpecJobTitle');
        const dropdownItems = document.querySelectorAll('#specJobTitleBtn + .dropdown-menu .dropdown-item');
        
        // Поиск в dropdown
        searchInput.addEventListener('input', function() {
            const searchText = this.value.toLowerCase();
            
            dropdownItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchText) ? 'block' : 'none';
            });
        });
        
        // Обработка выбора
        document.querySelectorAll('#specJobTitleBtn + .dropdown-menu .dropdown-item').forEach(item => {
            item.addEventListener('click', function() {
            // Обновляем текст кнопки
            dropdownBtn.textContent = this.textContent;
            
            // Записываем значение в hidden input
            hiddenInput.value = this.getAttribute('value');
            
            // Если выбрано "Создать новую должность"
            if (this.getAttribute('value') === 'create') {
                const modal = new bootstrap.Modal(document.getElementById('spec_job_title_Modal'));
                modal.show();
            }
            });
        });
        });