function reloadPeers() {
    var peersContent = $('#peers-content');
//    peersContent.empty(); // Clear previous content
    
    var loader = $('#peer-loader');
//    loader.show(); // Show loader
    
    var info = $('#peers-info');
    info.hide(); // Hide info text
    
    fetch('/get-active-peers/')
        .then(response => {
            console.log(response);
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to fetch active peers');
        })
        .then(data => {
            console.log(data);
            peersContent.html('');
        if (data.active_peers.length !== 0){
                data.active_peers.forEach(peer => {
                    console.log(peer)
                    // Create list item for each peer
                    var listItem = $('<li>', {
                        'class': 'list-group-item d-flex justify-content-between align-items-center',
                        'html': '<span class="file-name">' + peer.key + '</span>' +
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
//            info.show(); // Show info text
        })
        .finally(() => {
            loader.hide(); // Hide loader
        });
}

//$('#reload-peers-btn').on('click', function() {
//    reloadPeers();
//});

// Initial preload
reloadPeers();

setInterval(reloadPeers, 5000);