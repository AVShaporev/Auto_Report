// static/js/modals/spec_job_title.js
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация обработчиков
    initRoleDropdown();
    initSaveButton();
});

// Инициализация выпадающего списка
function initRoleDropdown() {
    const dropdownList = document.getElementById('roles-list');
    
    // Делегирование событий для всего списка
    dropdownList?.addEventListener('click', function(e) {
        if (e.target.classList.contains('dropdown-item')) {
            handleRoleSelection(e.target);
        }
    });
    
    // Инициализация поиска
    const searchInput = document.getElementById('specRoleSearch');
    searchInput?.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        const items = dropdownList.querySelectorAll('.dropdown-item');
        
        items.forEach(item => {
            item.style.display = item.textContent.toLowerCase().includes(filter) 
                ? 'block' 
                : 'none';
        });
    });
}

// Обработка выбора роли
function handleJobTitleSelection(selectedItem) {
    if (selectedItem.value === "create") {
        // Показываем модальное окно для создания новой роли
        new bootstrap.Modal(document.getElementById('role_Modal')).show();
        return;
    }
    
    // Устанавливаем выбранное значение
    document.getElementById('RoleBtn').textContent = selectedItem.textContent;
    document.getElementById('selectedRole').value = selectedItem.value;
}

// Инициализация кнопки сохранения
function initSaveButton() {
    document.getElementById('saveRoleBtn')?.addEventListener('click', submitRole);
}

// Отправка формы
async function submitRole() {
    const name = document.getElementById('name_of_role').value.trim();
    const description = document.getElementById('role_description').value.trim();
    
    if (!name) {
        alert('Пожалуйста, укажите наименование роли');
        return;
    }

    try {
        const response = await fetch('/api/roles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });

        if (!response.ok) throw new Error('Ошибка сохранения');
        
        const newRole = await response.json();
        addNewRoleToDropdown(newRole);
        
        // Закрываем и очищаем модальное окно
        bootstrap.Modal.getInstance(document.getElementById('role_Modal')).hide();
        document.getElementById('roleForm').reset();
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Не удалось сохранить роль: ' + error.message);
    }
}

// Добавление новой роли в список
function addNewRoleToDropdown(newRole) {
    const dropdownList = document.getElementById('roles-list');
    const dropdownButton = document.getElementById('roleBtn');
    const hiddenInput = document.getElementById('selectedRole');
    
    // Создаем новый элемент
    const newItem = document.createElement('button');
    newItem.className = 'dropdown-item';
    newItem.type = 'button';
    newItem.value = newRole.id;
    newItem.textContent = newRole.name;
    
    // Вставляем после кнопки "Создать"
    const createBtn = dropdownList.querySelector('button[value="create"]');
    createBtn.insertAdjacentElement('afterend', newItem);
    
    // Автоматически выбираем новую роль
    dropdownButton.textContent = newRole.name;
    hiddenInput.value = newRole.id;
}