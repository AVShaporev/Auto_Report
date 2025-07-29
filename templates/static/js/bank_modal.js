document.addEventListener('DOMContentLoaded', function() {
        // Элементы для банков
        const dropdownBtn = document.getElementById('BankBtn');
        const searchInput = document.getElementById('BankSearch');
        const hiddenInput = document.getElementById('selectedBank');
        const dropdownItems = document.querySelectorAll('#BankBtn + .dropdown-menu .dropdown-item');
        
        // Поиск в dropdown
        searchInput.addEventListener('input', function() {
            const searchText = this.value.toLowerCase();
            
            dropdownItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchText) ? 'block' : 'none';
            });
        });
        
        // Обработка выбора
        document.querySelectorAll('#BankBtn + .dropdown-menu .dropdown-item').forEach(item => {
            item.addEventListener('click', function() {
            // Обновляем текст кнопки
            dropdownBtn.textContent = this.textContent;
            
            // Записываем значение в hidden input
            hiddenInput.value = this.getAttribute('value');
            
            // Если выбрано "Создать новый банк"
            if (this.getAttribute('value') === 'create') {
                const modal = new bootstrap.Modal(document.getElementById('bank_Modal'));
                modal.show();
            }
            });
        });
        });