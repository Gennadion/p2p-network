/* fetches users files from localhost
   potential use: check localhost directory with saved content, that user want to share over p2p
*/

function fetchUserFiles() {
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
                        '<button type="button" class="btn btn-outline-danger btn-sm share-btn">' +
                            '<i class="bi "></i> Delete' +
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
document.getElementById('reload-files-btn').addEventListener('click', fetchUserFiles);
