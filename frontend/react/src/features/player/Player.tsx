import React, { useEffect, useState } from "react";
import Hls from "hls.js";
import type { Channel } from "../../types";
import { Modal } from "../../components/Common";


export function Player() {
    const [channel, setChannel] = useState<Channel | null>(null);
    useEffect(() => {
        const f = (e: Event) => setChannel((e as CustomEvent<Channel>).detail);
        addEventListener("play-channel", f);
        return () => removeEventListener("play-channel", f);
    }, []);
    useEffect(() => {
        if (!channel) return;
        const video = document.getElementById("video") as HTMLVideoElement;
        let hls: Hls | null = null;
        if (channel.url.includes(".m3u8") && Hls.isSupported()) {
            hls = new Hls({ enableWorker: true, lowLatencyMode: true });
            hls.loadSource(channel.url);
            hls.attachMedia(video);
        } else video.src = channel.url;
        return () => {
            hls?.destroy();
            video.pause();
            video.src = "";
        };
    }, [channel]);
    return channel ? (
        <Modal
            title={`Visualizando: ${channel.name}`}
            close={() => setChannel(null)}
        >
            <video id="video" className="video" controls autoPlay />
        </Modal>
    ) : null;
}
