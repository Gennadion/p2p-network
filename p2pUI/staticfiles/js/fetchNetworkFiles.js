function fetchNetworkFiles() {

    const loader = $('#netfiles-loader');
    const info = $('#netfiles-info');
    info.hide();
    fetch('/get-network-files/')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to fetch network files');
        })
        .then(data => {
             console.log(data);
            const netContent = document.getElementById('net-content');
            netContent.innerHTML = ''; // Clear previous content
           $.each(data.net_files, function(index, file) {
                // Create list item for each file
                var listItem = $('<li>', {
                    'class': 'list-group-item d-flex justify-content-between align-items-center'
                });


                var fileNameSpan = $('<span>', {
                    'class': 'file-name',
                    'text': file
                });


                var downloadButton = $('<button>', {
                    'type': 'button',
                    'class': 'btn btn-outline-primary btn-sm share-btn',
                    'html': '<i class="bi bi-download"></i> Get'
                });


                listItem.append(fileNameSpan).append(downloadButton);


                $('#net-content').append(listItem);
            });

            searchListItems();
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

// Initial preload
fetchNetworkFiles();

// Fetch network files every 5 seconds
setInterval(fetchNetworkFiles, 5000);