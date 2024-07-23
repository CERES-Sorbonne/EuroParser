import {spawn_dropzone} from './dropzone_handler.js'

const base_url = window.location.href
console.log("base url : " + base_url)

const base_params = {
    "filter_keywords": false,
    "filter_lang": false,
    "minimal_support": 1,
    "minimal_support_kw": 1,
    "minimal_support_journals": 1,
    "minimal_support_authors": 1,
    "minimal_support_dates": 1

}

function addBaseURL(path) {
    if (path.startsWith("/") && base_url.endsWith("/")) {
        return base_url + path.slice(1);
    }
    if (!path.startsWith("/") && !base_url.endsWith("/")) {
        return base_url + "/" + path;
    }
    return base_url + path;
}

async function createFileUploadUrl() {
    let url = null;
    let uuid_ = null;
    let url_promise = fetch(addBaseURL("/create_file_upload_url"))
        .then(response => response.json())
        .then(data => {
            console.log(data);
            url = addBaseURL(data.upload_url);
            uuid_ = data.uuid;
        })
        .catch(error => {
            if (error === "UUID collision") {
                return createFileUploadUrl();
            }
        });

    await url_promise;
    console.log("upload url : " + url);
    console.log("upload uuid : " + uuid_);
    return [url, uuid_];
}

function submitForm() {
    // Ensure that all files have been uploaded
    if (myDropzone.files.length === 0) {
        alert("Please upload files first");
        return;
    }
    if (myDropzone.getUploadingFiles().length > 0 || myDropzone.getQueuedFiles().length > 0) {
        alert("Please wait for all files to upload");
        return;
    }
    if (myDropzone.getRejectedFiles().length > 0) {
        alert("Please upload only valid files");
        return;
    }
    if (myDropzone.getAcceptedFiles().length !== myDropzone.files.length) {
        alert("Please wait for all files to be processed");
        return;
    }

    // Ensure that at least one output format is selected
    let checkboxes = document.getElementsByTagName('input');
    let checked = false;
    for (let checkbox of checkboxes) {
        if (checkbox.type === 'checkbox' && checkbox.checked) {
            checked = true;
            break;
        }
    }
    if (!checked) {
        alert("Please select at least one output format");
        return;
    }

    const conversion_container = document.getElementById('conversion-container');
    conversion_container.style.display = "none";

    //send all the form data along with the files:
    let xhr = new XMLHttpRequest();
    let formData = new FormData();

    // UUID (for the server to know which files to convert)
    formData.append("uuid", uuid_);

    // Output formats (for the server to know which formats to convert to)
    // let checkboxes = document.getElementsByTagName('input');
    for (let checkbox of checkboxes) {
        if (checkbox.type === 'checkbox' && checkbox.checked && !checkbox.className.includes("params-input")) {
            formData.append("output", checkbox.id);
        }
    }

    // Params (for the server to know which parameters to use)
    let params = document.getElementsByClassName('params-input');
    let params_dict = {};
    for (let param of params) {
        formData.append(param.id, param.value);
    }
    // for (let key in base_params) {
    //     formData.append(key, base_params[key]);
    // }

    console.log(formData.get("output"))
    console.log(formData.get("uuid"))

    xhr.open("POST", addBaseURL("convert"));

    let labels = document.getElementsByTagName('label');
    for (let label of labels) {
        label.disabled = true;
        label.cursor = "not-allowed";
        label.style.opacity = "0.5";
    }
    for (let checkbox of checkboxes) {
        checkbox.disabled = true;
        checkbox.cursor = "not-allowed";
        checkbox.style.opacity = "0.5";
    }

    xhr.responseType = 'blob';
    xhr.onload = function (e) {
        if (e.currentTarget.status > 300) {
            document.getElementById('loader-container').style.display = "none";
            document.getElementById('error').innerHTML = e.currentTarget.statusText;
            document.getElementById('error').style.display = "block";
        }
        let blob = e.currentTarget.response;
        let contentDispo = e.currentTarget.getResponseHeader('Content-Disposition');
        // https://stackoverflow.com/a/23054920/
        let fileName = contentDispo.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
        document.getElementById('loader-container').style.display = "none";
        saveBlob(blob, fileName);
    }

    xhr.upload.onprogress = function (e) {
        let percentComplete = (e.loaded / e.total) * 100;
        document.getElementById('loader-container').style.display = "block";
        document.getElementById('loader-container').value = percentComplete
    }

    xhr.send(formData);
}

function saveBlob(blob, fileName) {
    console.log("saveBlob")

    let download_container = document.getElementById('download-container');
    let download = document.getElementById('download');

    download.href = window.URL.createObjectURL(blob);
    download.download = fileName;

    download_container.style.display = "block";

    download.click();
}

const uploadUrl = await createFileUploadUrl()
const url = uploadUrl[0]
const uuid_ = uploadUrl[1]

const myDropzone = spawn_dropzone("files-dropzone", url)
myDropzone.on("success", function(file){
  $(".dz-success-mark svg").css("background", "green").css('border-radius', '30px');
  $(".dz-error-mark").css("display", "none");
});
myDropzone.on("error", function(file) {
  $(".dz-error-mark svg").css("background", "red").css('border-radius', '30px');
  $(".dz-success-mark").css("display", "none");
});
window.submitForm = submitForm
