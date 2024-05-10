$('body').on('click', '.downloadButton', async function() {
    try {
        // Get the file hash from the data attribute of the clicked button
        const fileHash = $(this).data("file-hash");
        const fileName = $(this).data("file-name");
        // Send an asynchronous request to the backend
        const response = await fetch(`/get-file/${fileHash}/${fileName}/`);
        if (response.ok) {
            const result = await response.text();
            // Handle the result if needed
            console.log(result);
            alert(result);
        } else {
            console.error('Failed to initiate file download:', response.statusText);
            alert('Failed to initiate file download: ' + response.statusText);
        }
    } catch (error) {
        console.error('Error occurred while initiating file download:', error);
         alert('Error occurred while initiating file download: ' + error);
    }
});
