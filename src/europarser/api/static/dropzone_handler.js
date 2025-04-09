import 'https://unpkg.com/dropzone@5/dist/min/dropzone.min.js'
// import 'https://unpkg.com/dropzone@5/dist/dropzone.js'
Dropzone.autoDiscover = false;

function updateState(elem, number) {
    let state = document.getElementById('state');
    state.innerHTML = parseInt(state.innerHTML) + number;
    // elem.hasFiles = parseInt(state.innerHTML) !== 0;
}


export function spawn_dropzone(id_, url) {
    const dropzone = document.getElementById(id_); //  'files-dropzone'

    return new Dropzone(dropzone, {
        url: url,
        paramName: "file",
        maxFiles: 1_000,
        acceptedFiles: "text/html, application/json", // "text/html, application/zip",
        autoProcessQueue: true,
        parallelUploads: 10,
        uploadMultiple: false,
        // chunking: true,
        // chunkSize: 1024 * 1024 * 5,
        // parallelChunkUploads: true,
        // retryChunks: true,
        // retryChunksLimit: 3,
        maxFilesize: 1024,
        createImageThumbnails: false,

        init: function () {
            this.on("addedfile", function (file) {
                updateState(this, 1)
                console.log('addedfile')
            });
            this.on("removedfile", function (file) {
                updateState(this, -1)
                console.log('removedfile')
            });

            this.on("success", function (file, response) {
                console.log('success')
            });
            this.on("error", function (file, errorMessage) {
                console.log('error')
            });
        }
    });
}


// const createUrl = "/upload?"
// myDropzone = spawn_dropzone("files-dropzone", createUrl)
