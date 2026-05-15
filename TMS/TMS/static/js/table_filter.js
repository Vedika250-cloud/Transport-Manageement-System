function filterTable(inputId, tableId) {
    let input, filter, table, tr, td, i, j, txtValue, rowVisible;
    input = document.getElementById(inputId);
    filter = input.value.toLowerCase();
    table = document.getElementById(tableId);
    
    // Fallback if tableId not found or not provided: try to find the first table on the page
    if (!table) {
        table = document.querySelector('table');
        if (!table) return;
    }

    tr = table.getElementsByTagName("tr");

    for (i = 1; i < tr.length; i++) {
        rowVisible = false;
        td = tr[i].getElementsByTagName("td");
        for (j = 0; j < td.length; j++) {
            if (td[j]) {
                txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    rowVisible = true;
                    break;
                }
            }
        }
        if (rowVisible) {
            tr[i].style.display = "";
        } else {
            tr[i].style.display = "none";
        }
    }
}
