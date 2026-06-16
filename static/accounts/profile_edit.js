// JS для превью аватарки перед сохранением
document.getElementById('avatar_input').addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
        const img = document.querySelector('.w-20.h-20');
        if (img.tagName === 'IMG') {
            img.src = URL.createObjectURL(file);
        } else {
            // Если стояла иконка, заменяем её на картинку
            const newImg = document.createElement('img');
            newImg.src = URL.createObjectURL(file);
            newImg.className = 'w-20 h-20 rounded-full object-cover mr-5 shadow';
            img.replaceWith(newImg);
        }
    }
});