const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const uploadInput = document.getElementById('imageInput');

navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => video.srcObject = stream)
.catch(err => console.error(err));

captureBtn.addEventListener('click', () => {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(blob => {
        const file = new File([blob], "snapshot.png", { type: "image/png" });
        const dt = new DataTransfer();
        dt.items.add(file);
        uploadInput.files = dt.files;
        alert("Snapshot captured! Click 'Upload Image' to predict.");
    });
});