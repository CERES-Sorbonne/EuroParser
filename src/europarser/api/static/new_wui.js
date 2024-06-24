document.getElementsByClassName('myInput').forEach(function (item) {
    item.style.margin = 'auto 1vh 1vh' + document.getElementById('myDropzone').offsetHeight + 'px' + ' 50vh';
});


function saveBlob(blob, fileName) {
    var download = document.getElementById('download');
    download.href = window.URL.createObjectURL(blob);
    download.download = fileName;
}

function createUrl(files, dataBlock) {
    let url = "{{host + '/upload?'}}"
        + "filter_keywords=" + document.getElementById('filter_keywords').checked.toString()
        + "&minimal_support=" + (document.getElementById('minimal_support').value || 1)
        + "&minimal_support_kw=" + (document.getElementById('minimal_support_kw').value || 1)
        + "&minimal_support_journals=" + (document.getElementById('minimal_support_journals').value || 1)
        + "&minimal_support_authors=" + (document.getElementById('minimal_support_authors').value || 1)
        + "&minimal_support_dates=" + (document.getElementById('minimal_support_dates').value || 1)

    console.log(url)
    return (url)
}

Dropzone.options.myDropzone = {
    paramName: 'files',
    url: createUrl,
    autoProcessQueue: false,
    uploadMultiple: true,
    parallelUploads: 100,
    maxFiles: 100,
    acceptedFiles: '.html',
    // addRemoveLinks: true,
    // headers: { 'X-CSRF-TOKEN': $('meta[name="csrf-token"]').attr('content') },

    init: function () {
        let dzClosure = this; // Makes sure that 'this' is understood inside the functions below.

        // for Dropzone to process the queue (instead of default form behavior):
        document.getElementById("submit-all").addEventListener("click", function (e) {
            // Make sure that the form isn't actually being sent.
            e.preventDefault();
            e.stopPropagation();
            dzClosure.processQueue();

        })

        //send all the form data along with the files:
        this.on("sendingmultiple", function (data, xhr, formData) {
            if (document.getElementById('iramuteq').checked) {
                formData.append("output", "iramuteq");
            }
            if (document.getElementById('txm').checked) {
                formData.append("output", "txm");
            }
            if (document.getElementById('json').checked) {
                formData.append("output", "json");
            }
            if (document.getElementById('csv').checked) {
                formData.append("output", "csv");
            }
            if (document.getElementById('excel').checked) {
                formData.append("output", "excel");
            }
            if (document.getElementById('stats').checked) {
                formData.append("output", "stats");
            }
            var checked;
            if (document.getElementById('processed_stats').checked) {
                formData.append("output", "processed_stats");
                checked = true;
            }
            if (document.getElementById('plots').checked) {
                formData.append("output", "plots");
            }
            if (document.getElementById('markdown').checked) {
                formData.append("output", "markdown");
            }

            for (let file of data) {
                if (file.size === 0) { // Directory
                    // pass
                } else { // File
                    formData.append("files", file);
                }
            }

            document.getElementById('loader').style.display = "block";
            document.getElementById('submit-all').style.display = "none";


            len_ = document.getElementsByClassName("myInput").length
            for (let i = 0; i < len_; i++) {
                document.getElementsByClassName("myInput")[i].disabled = true;
                document.getElementsByClassName("myInput")[i].cursor = "not-allowed";
                document.getElementsByClassName("myDivInput")[i].style.opacity = "0.5";
            }

            xhr.responseType = 'blob';
            xhr.onload = function (e) {
                if (e.currentTarget.status > 300) {
                    document.getElementById('loader').style.display = "none";
                    document.getElementById('error').innerHTML = e.currentTarget.statusText;
                    document.getElementById('error').style.display = "block";
                }
                var blob = e.currentTarget.response;
                var contentDispo = e.currentTarget.getResponseHeader('Content-Disposition');
                // https://stackoverflow.com/a/23054920/
                var fileName = contentDispo.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
                document.getElementById('download').style.display = "block";
                document.getElementById('loader').style.display = "none";
                saveBlob(blob, fileName);
            }
            xhr.send(formData)
        });
    }
}

showtooltip = function (id) {
    document.getElementById(id).style.display = "block";
}
