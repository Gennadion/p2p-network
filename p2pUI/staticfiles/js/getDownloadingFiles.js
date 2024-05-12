function getDownloadingFiles(){
    fetch('/get-downloading-files/')
    .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to fetch network files');
        })
        .then(data => {
            console.log(data);
            var container = $('<div>');
            data.downloading.forEach(file => {
                 var listItem = $('<li>', {
                    'class': 'list-group-item d-flex justify-content-between align-items-center ',
                    'html': '<span class="file-name">' + file + '</span>'
                });
                container.append(listItem);

            })
                $('#download-content').html(container);

        })
        .catch(error => {
            console.error('Error:', error);
        });
}

setInterval(getDownloadingFiles, 500);