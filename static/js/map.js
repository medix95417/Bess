document.getElementById('load-map')?.addEventListener('click', () => {
  const host = document.getElementById('incident-map');
  if (!window.L) { host.textContent = 'The map could not load. Use the complete incident list below.'; return; }
  const points = JSON.parse(document.getElementById('incident-points').textContent);
  host.replaceChildren();
  const map = L.map(host, {scrollWheelZoom: false}).setView([34, -98], 3);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 17
  }).addTo(map);
  const bounds = [];
  for (const point of points) {
    const box = document.createElement('div');
    const link = document.createElement('a'); link.href = point.url; link.textContent = point.title;
    const description = document.createElement('p'); description.textContent = `${point.date} · ${point.outcome}`;
    box.append(link, description);
    L.circleMarker([point.latitude, point.longitude], {radius: 9, color: '#123b3d', fillColor: '#208164', fillOpacity: 0.85, weight: 2}).addTo(map).bindPopup(box);
    bounds.push([point.latitude, point.longitude]);
  }
  if (bounds.length) map.fitBounds(bounds, {padding: [40, 40], maxZoom: 8});
});
