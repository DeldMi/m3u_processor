let loadedChannels = [];
let currentChannelPage = 1;

function toggleSidebar() {
    document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem("sidebar-collapsed", document.body.classList.contains("sidebar-collapsed"));
}

document.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem("sidebar-collapsed") === "true") document.body.classList.add("sidebar-collapsed");
});

function loadChannels() {
    const country = document.getElementById("filter-country").value;
    const category = document.getElementById("filter-category").value;
    const status = document.getElementById("filter-status").value;

    const search = encodeURIComponent(document.getElementById("channel-search").value);
    const sort = document.getElementById("sort-channels").value;
    const direction = document.getElementById("sort-direction").value;
    fetch(`/api/v1/channels?country=${country}&category=${category}&status=${status}&search=${search}&sort=${sort}&direction=${direction}`)
        .then(r => r.json())
        .then(channels => {
            loadedChannels = channels;
            currentChannelPage = 1;
            renderChannelPage();
        });
}

function renderChannelPage() {
    const tbody = document.getElementById("channels-table-body");
    const pageSizeValue = document.getElementById("channel-page-size").value.trim();
    const requestedPageSize = Number(pageSizeValue);
    const pageSize = !pageSizeValue || requestedPageSize < 1 ? loadedChannels.length || 1 : requestedPageSize;
    const totalPages = Math.max(1, Math.ceil(loadedChannels.length / pageSize));
    currentChannelPage = Math.min(currentChannelPage, totalPages);
    const start = (currentChannelPage - 1) * pageSize;
    const visibleChannels = loadedChannels.slice(start, start + pageSize);
    document.getElementById("channel-count").innerText = `${visibleChannels.length} de ${loadedChannels.length} canal(is) neste grupo`;
    document.getElementById("channel-page-indicator").innerText = `Página ${currentChannelPage} de ${totalPages}`;
    document.getElementById("previous-channel-page").disabled = currentChannelPage === 1;
    document.getElementById("next-channel-page").disabled = currentChannelPage === totalPages;
    document.getElementById("select-all-channels").checked = false;
    tbody.innerHTML = visibleChannels.map(ch => `
                <tr>
                    <td><input type="checkbox" class="channel-select" value="${ch.id}"></td>
                    <td>
                        <span class="status-dot ${ch.status}" 
                              title="Clique para alternar forçado (Online/Offline)" 
                              onclick="toggleStatus(${ch.id}, '${ch.status}')"></span>
                    </td>
                    <td class="channel-name-cell">
                        <img class="channel-logo" src="${escapeHtml(ch.logo || extractLogo(ch.metadata))}" alt="" onerror="this.classList.add('logo-fallback'); this.removeAttribute('src');">
                        <b>${escapeHtml(ch.name)}</b><button class="icon-btn" title="Editar canal" onclick='editChannel(${JSON.stringify(ch)})'>Editar</button>
                    </td>
                    <td data-column="location">${escapeHtml(ch.country)} / ${escapeHtml(ch.state)} / ${escapeHtml(ch.city)}</td>
                    <td><span style="text-transform:uppercase; font-size:10px;">${ch.category}</span></td>
                    <td data-column="group">${escapeHtml(ch.group_title || "-")}</td>
                    <td data-column="epg">${escapeHtml(ch.tvg_id || "-")}</td>
                    <td data-column="latency">${ch.latency_ms || 0} ms</td>
                    <td data-column="url" class="is-hidden"><small>${escapeHtml(ch.url)}</small></td>
                    <td>
                        <input type="checkbox" ${ch.auto_remove_if_offline ? "checked" : ""} 
                               onchange="toggleAutoRemove(${ch.id}, this.checked)">
                    </td>
                    <td>
                        <button class="btn" onclick="playStream('${ch.url}', '${ch.name}')">Assistir</button>
                    </td>
                </tr>
            `).join('');
}

function changeChannelPage(step) {
    currentChannelPage += step;
    renderChannelPage();
}

let channelLoadTimer;
function scheduleChannelLoad() {
    clearTimeout(channelLoadTimer);
    channelLoadTimer = setTimeout(loadChannels, 250);
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}

function toggleAllChannels(checked) {
    document.querySelectorAll(".channel-select").forEach(input => input.checked = checked);
}

function toggleColumn(column, visible) {
    document.querySelectorAll(`[data-column="${column}"]`).forEach(element => element.classList.toggle("is-hidden", !visible));
}

function extractLogo(metadata) {
    const match = String(metadata || "").match(/tvg-logo="([^"]*)"/i);
    return match ? match[1] : "";
}

function editChannel(channel) {
    document.getElementById("edit-channel-id").value = channel.id;
    document.getElementById("edit-name").value = channel.name || "";
    document.getElementById("edit-url").value = channel.url || "";
    document.getElementById("edit-logo").value = channel.logo || extractLogo(channel.metadata);
    document.getElementById("edit-tvg-id").value = channel.tvg_id || "";
    document.getElementById("edit-group").value = channel.group_title || "";
    document.getElementById("edit-country").value = channel.country || "";
    document.getElementById("edit-state").value = channel.state || "";
    document.getElementById("edit-city").value = channel.city || "";
    document.getElementById("edit-category").value = channel.category || "tv";
    document.getElementById("edit-status").value = channel.status || "desconhecido";
    document.getElementById("edit-metadata").value = channel.metadata || "";
    document.getElementById("edit-auto-remove").checked = Boolean(channel.auto_remove_if_offline);
    document.getElementById("channel-editor").style.display = "flex";
}

function closeChannelEditor() {
    document.getElementById("channel-editor").style.display = "none";
}

function saveChannel(event) {
    event.preventDefault();
    const id = document.getElementById("edit-channel-id").value;
    const logo = document.getElementById("edit-logo").value;
    const metadata = document.getElementById("edit-metadata").value;
    fetch(`/api/v1/channels/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: document.getElementById("edit-name").value,
            url: document.getElementById("edit-url").value,
            logo,
            tvg_id: document.getElementById("edit-tvg-id").value,
            group_title: document.getElementById("edit-group").value,
            country: document.getElementById("edit-country").value,
            state: document.getElementById("edit-state").value,
            city: document.getElementById("edit-city").value,
            category: document.getElementById("edit-category").value,
            status: document.getElementById("edit-status").value,
            metadata,
            auto_remove_if_offline: document.getElementById("edit-auto-remove").checked ? 1 : 0
        })
    }).then(response => {
        if (!response.ok) throw new Error("save failed");
        closeChannelEditor();
        loadChannels();
    }).catch(() => alert("Não foi possível salvar o canal."));
}

function selectedChannelIds() {
    return [...document.querySelectorAll(".channel-select:checked")].map(input => Number(input.value));
}

function openPlaylistBuilder() {
    const ids = selectedChannelIds();
    if (!ids.length) {
        alert("Selecione pelo menos um canal.");
        return;
    }
    document.getElementById("selection-summary").innerText = `${ids.length} canal(is) selecionado(s).`;
    document.getElementById("playlist-builder").style.display = "flex";
}

function closePlaylistBuilder() {
    document.getElementById("playlist-builder").style.display = "none";
}

function generatePlaylist() {
    const ids = selectedChannelIds();
    const payload = {
        ids,
        sort: document.getElementById("playlist-sort").value,
        direction: document.getElementById("playlist-direction").value,
        limit: document.getElementById("playlist-limit").value || undefined,
        status: document.getElementById("playlist-online-only").checked ? "online" : "todos"
    };
    fetch("/api/v1/playlists/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then(response => response.json())
        .then(data => document.getElementById("playlist-result").innerText = data.manifestos?.length ? `${data.manifestos.length} arquivo(s) gerado(s). Veja os links no painel.` : "Nenhum canal corresponde ao perfil.");
}

function toggleStatus(id, currentStatus) {
    const nextStatus = currentStatus === 'online' ? 'offline' : 'online';
    fetch(`/api/v1/channels/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
    }).then(() => loadChannels());
}

function toggleAutoRemove(id, isChecked) {
    fetch(`/api/v1/channels/${id}/autoremove`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_remove_if_offline: isChecked ? 1 : 0 })
    });
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("channels-table-body")) loadChannels();
});