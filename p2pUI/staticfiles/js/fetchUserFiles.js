/* fetches users files from localhost
   potential use: check localhost directory with saved content, that user want to share over p2p
*/

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function fetchUserFiles() {
        const my_loader = $('#myfiles-loader');
    const my_info = $('#myfiles-info');
    $('#my-content').html('');
    my_info.hide();
    my_loader.show();
fetch('/get-local-files/')
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
        data.local_files.forEach(file => {
        const fileSize = formatFileSize(file.size);
            // Create list item for each file
            var listItem = $('<li>', {
                'class': 'list-group-item d-flex justify-content-between align-items-center',
                'html': '<span class="file-name col-6">' + file.name + '</span>' +
                        '<span class="label col-2">' + 'size: '  + '</span>' +
                        '<span class="size col-2">' + fileSize + '</span>'
//                        +
//                        '<button type="button" class="btn btn-outline-danger btn-sm share-btn">' +
//                            '<i class="bi "></i> Delete' +
//                        '</button>'
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
