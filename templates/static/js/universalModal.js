async function submitModalForm(modalId, fields, endpoint, listId, dropdownBtnId, hiddenFieldId) {
    const fieldValues = {};
    const errors = [];
    
    // Сборка значения полей и проверка обязательных
    fields.forEach(field => {
        const value = document.getElementById(field.id).value.trim();
        if (field.required && !value) {
            errors.push(`Поле "${field.label}" обязательно для заполнения`);
        }
        fieldValues[field.name] = value;
    });

    if (errors.length > 0) {
        alert(errors.join('\n'));
        return;
    }

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(fieldValues)
        });

        if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

        const data = await response.json();

        // Обновляем список
        const list = document.getElementById(listId);
        const newButton = document.createElement('button');
        newButton.className = 'dropdown-item';
        newButton.type = 'button';
        newButton.value = data.id;
        newButton.textContent = data.name;

        newButton.addEventListener('click', function() {
            document.getElementById(dropdownBtnId).textContent = this.textContent;
            if (hiddenFieldId) {
                document.getElementById(hiddenFieldId).value = this.value;
            }
        });

        const divider = list.querySelector('.dropdown-divider');
        if (divider) {
            divider.insertAdjacentElement('afterend', newButton);
        } else {
            list.appendChild(newButton);
        }

        // Обновление выбранного значения
        document.getElementById(dropdownBtnId).textContent = data.name;
        if (hiddenFieldId) {
            document.getElementById(hiddenFieldId).value = data.id;
        }

        // Закрывание и очистка модального окна
        bootstrap.Modal.getInstance(document.getElementById(modalId)).hide();
        fields.forEach(field => {
            document.getElementById(field.id).value = '';
        });

    } catch (error) {
        console.error("Ошибка:", error);
        alert("Не удалось сохранить: " + error.message);
    }
}
