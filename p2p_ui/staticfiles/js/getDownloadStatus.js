function checkDownloadStatus() {
    // Make a GET request to the backend endpoint
    fetch('/get-download-status/')
        .then(response => {
            if (response.ok) {
                // If the response is successful, parse the JSON data
                return response.json();
            } else {
                // If the response is not successful, throw an error
                throw new Error('Failed to fetch download status');
            }
        })
        .then(data => {
            // Handle the JSON data returned from the backend
            console.log('Download status:', data);
            // You can update the UI or perform further actions based on the download status
        })
        .catch(error => {
            // Handle errors
            console.error('Error checking download status:', error);
        });
}

// Call the function every 500 milliseconds
//setInterval(checkDownloadStatus, 500);