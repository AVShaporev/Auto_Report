document.getElementById('action-select-spec_contract').addEventListener('change', function() {
    const selectedValue = this.value;
    
    if (selectedValue === 'create') {
        const modal = new bootstrap.Modal(document.getElementById('spec_contract_Modal'));
        modal.show();
    }
});

// Отправка данных формы
async function submitSpec_Contract() {
    const name = document.getElementById('name').value;
    const description = document.getElementById('description').value;

    // Проверка на пустые поля
    if (!name.trim()) {
        alert("Пожалуйста, введите наименование контракта");
        return;
    }

    const response = await fetch('/spec_contract/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            description: description
        })
    });

    if (response.ok) {
        const select_spec_contract = await response.json();

        // Добавить новое значение в select
        const dropdown = document.getElementById("action-select-spec_contract")
        const option = document.createElement("option");
        option.value = select_spec_contract.id;
        option.textContent = select_spec_contract.name;
        dropdown.appendChild(option);

        // Закрыть модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('spec_contract_Modal'));
        modal.hide();
        
        // Очистить форму
        document.getElementById('spec_contract_Form').reset();
    }
}