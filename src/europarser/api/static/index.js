import {spawn_dropzone} from './dropzone_handler.js'

const debug = getDebugFromParam();
if (debug) {
    console.log("Debug mode activated, will see the console logs");
}

function getBaseURL() {
    let base_url = window.location.href;
    if (base_url.includes("?")) {
        base_url = base_url.split("?")[0];
    }

    if (base_url.includes("#")) {
        base_url = base_url.split("#")[0] + base_url.split("#")[1];
    }

    if (base_url.endsWith("/")) {
        return base_url;
    }

    return base_url + "/";
}

function parseURLParams() {
    const urlParams = Object.fromEntries(new URLSearchParams(window.location.search).entries());
    return urlParams;
}

function getURLParam() {
    const urlParams = parseURLParams();

    // If both ceres and pedro are present, return null to indicate an error else return the present key
    if ("ceres" in urlParams && "pedro" in urlParams) {
        return null;
    }
    if ("ceres" in urlParams) {
        return "ceres";
    }
    if ("pedro" in urlParams) {
        return "pedro";
    }
}

function getDebugFromParam() {
    const urlParams = parseURLParams();
    return "debug" in urlParams;
}


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
    if ("#".includes(path)) {
        path = path.split("#")[0] + path.split("#")[1]; // remove the hash
    }
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
            if (debug) {
                console.log(data);
            }
            url = addBaseURL(data.upload_url);
            uuid_ = data.uuid;
        })
        .catch(error => {
            if (error === "UUID collision") {
                return createFileUploadUrl();
            }
        });

    await url_promise;
    if (debug) {
        console.log("upload url : " + url);
    }
    if (debug) {
        console.log("upload uuid : " + uuid_);
    }
    return [url, uuid_];
}

function submitForm() {
    // Ensure that all files have been uploaded
    if (myDropzone.files.length === 0) {
        alert("Veuillez d'abord déposer vos fichiers à convertir");
        return;
    }
    if (myDropzone.getUploadingFiles().length > 0 || myDropzone.getQueuedFiles().length > 0) {
        alert("Merci d'attendre que tous les fichiers soient téléchargés");
        return;
    }
    if (myDropzone.getRejectedFiles().length > 0) {
        alert("Veillez à ce que tous les fichiers soient acceptés (uniquement les fichiers .html issus de Europresse)");
        return;
    }
    if (myDropzone.getAcceptedFiles().length !== myDropzone.files.length) {
        alert("Merci de patienter jusqu'à ce que tous les fichiers soient acceptés");
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
        const value = param.type === 'checkbox' ? param.checked : param.value
        formData.append(param.id, value);
    }
    // for (let key in base_params) {
    //     formData.append(key, base_params[key]);
    // }

    if (debug) {
        console.log(formData.get("output"));
    }
    if (debug) {
        console.log(formData.get("uuid"));
    }

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
            mutePedro();
            document.getElementById('loader-container').style.display = "none";
            document.getElementById('error').innerHTML = e.currentTarget.statusText;
            document.getElementById('error').style.display = "block";
            document.getElementById('redo-container').style.display = "block";
        }
        let blob = e.currentTarget.response;
        let contentDispo = e.currentTarget.getResponseHeader('Content-Disposition');
        // https://stackoverflow.com/a/23054920/
        let fileName = contentDispo.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
        mutePedro();
        document.getElementById('loader-container').style.display = "none";
        saveBlob(blob, fileName);
    }

    xhr.upload.onprogress = function (e) {
        let percentComplete = (e.loaded / e.total) * 100;
        hearPedro();
        document.getElementById('loader-container').style.display = "block";
        document.getElementById('loader-container').value = percentComplete
    }

    xhr.send(formData);
}

function redoForm(keep_files = false, keep_params = false) {
    let conversion_container = document.getElementById('conversion-container');
    conversion_container.style.display = "block";

    let download_container = document.getElementById('download-container');
    download_container.style.display = "none";

    let redo_container = document.getElementById('redo-container');
    redo_container.style.display = "none";

    let labels = document.getElementsByTagName('label');
    for (let label of labels) {
        label.disabled = false;
        label.cursor = "pointer";
        label.style.opacity = "1";
    }
    let inputs = document.getElementsByTagName('input');
    for (let input of inputs) {
        input.disabled = false;
        input.cursor = "pointer";
        input.style.opacity = "1";
    }

    if (!keep_files) {
        myDropzone.removeAllFiles();
    }

    if (!keep_params) {
        let checkboxes = document.getElementsByTagName('input');
        for (let checkbox of checkboxes) {
            if (checkbox.type === 'checkbox') {
                checkbox.checked = false;
            }
        }
        let params = document.getElementsByClassName('params-input');
        for (let param of params) {
            param.value = 1;
        }
    }

    let loader_container = document.getElementById('loader-container');
    loader_container.style.display = "none";

}

function saveBlob(blob, fileName) {
    if (debug) {
        console.log("saveBlob");
    }

    let download_container = document.getElementById('download-container');
    let download = document.getElementById('download');

    download.href = window.URL.createObjectURL(blob);
    download.download = fileName;

    download_container.style.display = "block";

    let redo_container = document.getElementById('redo-container');
    redo_container.style.display = "block";

    download.click();
}

function addModalEvents() {
    let buttons = document.querySelectorAll('[ id$="params_button" ]');
    for (let button of buttons) {
        button.onclick = function () {
            let modal = document.getElementById(button.id.replace("button", "modal"));
            modal.showModal();
        }
    }
}

function closeThis(this_) {
    if (event.target !== this_) {
        return;
    }

    this_.close();
}

function closeParentModal(this_) {
    let a = this_;
    while (a) {
        if (a.tagName === "DIALOG") {
            a.close();
            return;
        }
        a = a.parentElement;
    }
    console.error("No parent modal found");
}

function seeHelp(id_) {
    let help_ = document.querySelectorAll('[ id$="help" ]');
    for (let help of help_) {
        if (help.id === id_) {
            help.style.display = "block";
        } else {
            help.style.display = "none";
        }
    }
}

function seePedro() {
    if (urlParam === 'pedro') {
        document.getElementById('loader').className = "spinner-border-pedro";
        document.getElementById('loader').style["background-image"] = "url('" + base_url + "static/pedro.png')";

    }
}

function seeCeres() {
    if (urlParam === 'ceres') {
        document.getElementById('loader').className = "spinner-border-ceres";
        document.getElementById('loader').style["background-image"] = "url('" + base_url + "static/logo_ceres.png')";
    }

}

function hearPedro() {
    if (urlParam === 'pedro') {
        window.audio = new Audio('static/pedro.mp3');
        audio.loop = true;

        let audio_promise = audio.play()

        if (debug) {
            audio_promise.then(
                console.log("Pedro is speaking")
            ).catch(
                console.error("Pedro is not speaking")
            )
        }
    }
}

function mutePedro() {
    if (window.audio) {
        audio.pause();
    }
}

const base_url = getBaseURL();
if (debug) {
    console.log("base url : " + base_url);
}

const urlParam = getURLParam();
if (debug) {
    console.log("url param : " + urlParam);
}


addModalEvents()

const uploadUrl = await createFileUploadUrl()
const url = uploadUrl[0]
const uuid_ = uploadUrl[1]

const myDropzone = spawn_dropzone("files-dropzone", url)
myDropzone.on("success", function (file) {
    let success_marks = document.getElementsByClassName('dz-success-mark');
    for (let success_mark of success_marks) {
        success_mark.style.background = "green";
        success_mark.style.borderRadius = "30px";
    }
    // let error_marks = document.getElementsByClassName('dz-error-mark');
    // for (let error_mark of error_marks) {
    //     error_mark.style.display = "none";
    // }
});
myDropzone.on("error", function (file) {
    let error_marks = document.getElementsByClassName('dz-error-mark');
    for (let error_mark of error_marks) {
        error_mark.style.background = "red";
        error_mark.style.borderRadius = "30px";
    }
    // let success_marks = document.getElementsByClassName('dz-success-mark');
    // for (let success_mark of success_marks) {
    //     success_mark.style.display = "none";
    // }
});

seePedro();
seeCeres();


window.submitForm = submitForm
window.closeThis = closeThis
window.closeParentModal = closeParentModal
window.seeHelp = seeHelp
window.redoForm = redoForm

window.hearPedro = hearPedro
window.mutePedro = mutePedro
