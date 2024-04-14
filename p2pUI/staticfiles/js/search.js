  function filterListItems() {
        var input, filter, ul, li, span, txtValue;
        input = document.getElementById('search-input');
        filter = input.value.toUpperCase();

        ul_network = document.getElementById('network-content');
        li = ul_network.getElementsByTagName('li');

        ul_my = document.getElementById('my-content');
        li_my = ul_my.getElementsByTagName('li');

        searchListItems(li, filter);
        searchListItems(li_my, filter);


    }

    function searchListItems(listOfItems, filter) {
        for (var i = 0; i < listOfItems.length; i++) {
            span = listOfItems[i].getElementsByClassName('file-name')[0];
            txtValue = span.textContent || span.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                showListItem(listOfItems[i]);
            } else {
                hideListItem(listOfItems[i]);
            }
        }
    }

    function showListItem(li) {
        // If the item matches the filter, show it and apply border
        li.style.height = 'auto'; // Reset height
        li.style.padding = '8px 16px'; // Reset padding
        li.style.margin = '0'; // Reset margin
        li.style.border = '1px solid #ddd'; // Add border
        li.style.overflow = 'visible'; // Reset overflow
    }

    function hideListItem(li) {
        // If the item doesn't match the filter, hide it and remove border
        li.style.height = '0'; // Set height to 0
        li.style.padding = '0'; // Set padding to 0
        li.style.margin = '0'; // Set margin to 0
        li.style.border = 'none'; // Remove border
        li.style.overflow = 'hidden'; // Hide overflow
    }

    // Add an event listener to trigger the filter function when the search input changes
    document.getElementById('search-input').addEventListener('input', filterListItems);