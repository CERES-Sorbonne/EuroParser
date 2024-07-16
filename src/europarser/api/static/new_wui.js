import {spawn_dropzone} from './dropzone_handler.js'

function createUrl(files, dataBlock) {
    // let url = "{{host + '/upload?'}}"
    let url = "/upload?"
    // + "filter_keywords=" + document.getElementById('filter_keywords').checked.toString()
    // + "&minimal_support=" + (document.getElementById('minimal_support').value || 1)
    // + "&minimal_support_kw=" + (document.getElementById('minimal_support_kw').value || 1)
    // + "&minimal_support_journals=" + (document.getElementById('minimal_support_journals').value || 1)
    // + "&minimal_support_authors=" + (document.getElementById('minimal_support_authors').value || 1)
    // + "&minimal_support_dates=" + (document.getElementById('minimal_support_dates').value || 1)

    console.log(url)
    return (url)
}

async function createFileUploadUrl() {
    let url = null;
    let uuid_ = null;
    let url_promise = fetch("/create_file_upload_url")
        .then(response => response.json())
        .then(data => {
            console.log(data);
            url = data.upload_url;
            uuid_ = data.uuid;
        })
        .catch(error => {
            if (error === "UUID collision") {
                return createFileUploadUrl();
            }
        });

    await url_promise;
    return [url, uuid_];
}

export function submitForm() {
    //send all the form data along with the files:
    var xhr = new XMLHttpRequest();
    var formData = new FormData();

    formData.append("uuid", uuid_);

    let checkboxes = document.getElementsByTagName('input');

    for (let checkbox of checkboxes) {
        if (checkbox.type === 'checkbox' && checkbox.checked) {
            formData.append("output", checkbox.id.toString().toLowerCase());
        }
    }


    console.log(formData.get("output"))
    console.log(formData.get("uuid"))

    xhr.open("POST", createUrl());

    let len_ = checkboxes.length
    for (let i = 0; i < len_; i++) {
        checkboxes[i].disabled = true;
        checkboxes[i].cursor = "not-allowed";
        checkboxes[i].style.opacity = "0.5";
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
    xhr.send(formData);
}



const uploadUrl = await createFileUploadUrl()
const url = uploadUrl[0]
const uuid_ = uploadUrl[1]

const myDropzone = spawn_dropzone("files-dropzone", url)
