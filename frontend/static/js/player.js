let hlsInstance = null;

function playStream(url, channelName) {
    const modal = document.getElementById("player-modal");
    const video = document.getElementById("video-player");
    document.getElementById("player-title").innerText = "Visualizando: " + channelName;
    modal.style.display = "flex";

    if (hlsInstance) {
        hlsInstance.destroy();
    }

    if (Hls.isSupported() && url.includes(".m3u8")) {
        hlsInstance = new Hls({ enableWorker: true, lowLatencyMode: true });
        hlsInstance.loadSource(url);
        hlsInstance.attachMedia(video);
        hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => video.play());
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = url;
        video.play();
    } else {
        video.src = url;
        video.play();
    }
}

function closePlayer() {
    const modal = document.getElementById("player-modal");
    const video = document.getElementById("video-player");
    modal.style.display = "none";
    video.pause();
    video.src = "";
    if (hlsInstance) {
        hlsInstance.destroy();
        hlsInstance = null;
    }
}