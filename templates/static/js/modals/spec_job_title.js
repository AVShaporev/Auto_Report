// static/js/modals/spec_job_title.js
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация обработчиков
    initJobTitleDropdown();
    initSaveButton();
});

// Инициализация выпадающего списка
function initJobTitleDropdown() {
    const dropdownList = document.getElementById('job-titles-list');
    
    // Делегирование событий для всего списка
    dropdownList?.addEventListener('click', function(e) {
        if (e.target.classList.contains('dropdown-item')) {
            handleJobTitleSelection(e.target);
        }
    });
    
    // Инициализация поиска
    const searchInput = document.getElementById('specJobTitleSearch');
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

// Обработка выбора должности
function handleJobTitleSelection(selectedItem) {
    if (selectedItem.value === "create") {
        // Показываем модальное окно для создания новой должности
        new bootstrap.Modal(document.getElementById('spec_job_title_Modal')).show();
        return;
    }
    
    // Устанавливаем выбранное значение
    document.getElementById('specJobTitleBtn').textContent = selectedItem.textContent;
    document.getElementById('selectedSpecJobTitle').value = selectedItem.value;
}

// Инициализация кнопки сохранения
function initSaveButton() {
    document.getElementById('saveJobTitleBtn')?.addEventListener('click', submitJobTitle);
}

// Отправка формы
async function submitJobTitle() {
    const name = document.getElementById('name_of_job_title').value.trim();
    const description = document.getElementById('job_title_description').value.trim();
    
    if (!name) {
        alert('Пожалуйста, укажите наименование должности');
        return;
    }

    try {
        const response = await fetch('/api/spec_job_titles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });

        if (!response.ok) throw new Error('Ошибка сохранения');
        
        const newTitle = await response.json();
        addNewJobTitleToDropdown(newTitle);
        
        // Закрываем и очищаем модальное окно
        bootstrap.Modal.getInstance(document.getElementById('spec_job_title_Modal')).hide();
        document.getElementById('jobTitleForm').reset();
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Не удалось сохранить должность: ' + error.message);
    }
}

// Добавление новой должности в список
function addNewJobTitleToDropdown(newTitle) {
    const dropdownList = document.getElementById('job-titles-list');
    const dropdownButton = document.getElementById('specJobTitleBtn');
    const hiddenInput = document.getElementById('selectedSpecJobTitle');
    
    // Создаем новый элемент
    const newItem = document.createElement('button');
    newItem.className = 'dropdown-item';
    newItem.type = 'button';
    newItem.value = newTitle.id;
    newItem.textContent = newTitle.name;
    
    // Вставляем после кнопки "Создать"
    const createBtn = dropdownList.querySelector('button[value="create"]');
    createBtn.insertAdjacentElement('afterend', newItem);
    
    // Автоматически выбираем новую должность
    dropdownButton.textContent = newTitle.name;
    hiddenInput.value = newTitle.id;
}