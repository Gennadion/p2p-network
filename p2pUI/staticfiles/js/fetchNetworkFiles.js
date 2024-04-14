function fetchNetworkFiles() {
 // Reload network files
    const loader = $('#netfiles-loader');
    const info = $('#netfiles-info');
    $('#net-content').html('');
    info.hide();
//    loader.show();
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
}

// Initial preload
fetchNetworkFiles();

// Fetch network files every 5 seconds
setInterval(fetchNetworkFiles, 5000);