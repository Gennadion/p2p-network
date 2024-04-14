function reloadPeers() {
    var peersContent = $('#peers-content');
    peersContent.empty(); // Clear previous content
    
    var loader = $('#peer-loader');
    loader.show(); // Show loader
    
    var info = $('#peers-info');
    info.hide(); // Hide info text
    
    fetch('/get-active-peers/')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to fetch active peers');
        })
        .then(data => {
            console.log(data);
            if (data.active_peers.length === 0) {
                console.log('empty');
                info.show(); // Show info text
            } else {
                data.active_peers.forEach(peer => {
                    // Create list item for each peer
                    var listItem = $('<li>', {
                        'class': 'list-group-item d-flex justify-content-between align-items-center',
                        'html': '<span class="file-name">' + peer + '</span>' +
                                '<button type="button" class="btn btn-outline-primary btn-sm share-btn">' +
                                    '<i class="bi bi-eye-fill"></i>' +
                                '</button>'
                    });
                    peersContent.append(listItem);
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            info.show(); // Show info text
        })
        .finally(() => {
            loader.hide(); // Hide loader
        });
}

$('#reload-peers-btn').on('click', function() {
    reloadPeers();
});

reloadPeers();