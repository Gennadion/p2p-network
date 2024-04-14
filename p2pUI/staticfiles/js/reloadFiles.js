function reloadFiles() {
    // Reload network files
    const loader = $('#netfiles-loader');
    const info = $('#netfiles-info');
    $('#net-content').html('');
    info.hide();
    loader.show();
    fetch('/get-network-files/')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            info.show();
            throw new Error('Failed to fetch network files');
        })
        .then(data => {
            loader.hide();
             console.log(data);
            const netContent = document.getElementById('net-content');
            netContent.innerHTML = ''; // Clear previous content
           $.each(data.net_files, function(index, file) {
                // Create list item for each file
                var listItem = $('<li>', {
                    'class': 'list-group-item d-flex justify-content-between align-items-center'
                });

                // Create span element for file name
                var fileNameSpan = $('<span>', {
                    'class': 'file-name',
                    'text': file
                });

                // Create button element for download
                var downloadButton = $('<button>', {
                    'type': 'button',
                    'class': 'btn btn-outline-primary btn-sm share-btn',
                    'html': '<i class="bi bi-download"></i> Get'
                });

                // Append file name span and download button to list item
                listItem.append(fileNameSpan).append(downloadButton);

                // Append list item to netContent
                $('#net-content').append(listItem);
            });
        })
        .catch(error => {
            console.error('Error:', error);
        });


 const my_loader = $('#myfiles-loader');
    const my_info = $('#myfiles-info');
    $('#my-content').html('');
    my_info.hide();
    my_loader.show();
fetch('/get-my-files/')
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        my_info.show();
        throw new Error('Failed to fetch my files');
    })
    .then(data => {
        my_loader.hide();
        console.log(data);
        var myContent = $('#my-content');
        myContent.empty(); // Clear previous content
        data.my_files.forEach(file => {
            // Create list item for each file
            var listItem = $('<li>', {
                'class': 'list-group-item d-flex justify-content-between align-items-center',
                'html': '<span class="file-name">' + file + '</span>' +
                        '<button type="button" class="btn btn-outline-primary btn-sm share-btn">' +
                            '<i class="bi bi-share-fill"></i> Share' +
                        '</button>'
            });
            myContent.append(listItem);
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Event listener for reload files button
document.getElementById('reload-files-btn').addEventListener('click', reloadFiles);
reloadFiles();