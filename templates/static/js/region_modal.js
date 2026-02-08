document.getElementById('action-select-region').addEventListener('change', function() {
    const selectedValue = this.value;
    
    if (selectedValue === 'create') {
        const modal = new bootstrap.Modal(document.getElementById('region_Modal'));
        modal.show();
    }
});

// Отправка данных формы
async function submitRegion() {
    const name = document.getElementById('name').value;
    const symdol = document.getElementById('symdol').value;
    const spec_region_id = document.getElementById('spec_region_id').value;
    const description = document.getElementById('description').value;

    // Проверка на пустые поля

    // Проверка наличия наименования региона
    if (!name.trim()) {
        alert("Пожалуйста, введите наименование региона");
        return;
    }

    // Проверка наличия кода региона
    if (!symdol.trim()) {
        alert("Пожалуйста, введите код региона");
        return;
    }
    
    // Проверка выбора типа региона
    if (!spec_region_id.trim()) {
        alert("Пожалуйста, выберите тип региона");
        return;
    }

    const response = await fetch('/region/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            symdol: symdol,
            spec_region_id: spec_region_id,
            description: description
        })
    });

    if (response.ok) {
        const select_region = await response.json();

        // Добавить новое значение в select
        const dropdown = document.getElementById("action-select-region")
        const option = document.createElement("option");
        option.value = select_region.id;
        option.textContent = select_region.name;
        dropdown.appendChild(option);

        // Закрыть модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('region_Modal'));
        modal.hide();
        
        // Очистить форму
        document.getElementById('region_Form').reset();
    }
}