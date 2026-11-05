// map.js
document.addEventListener('DOMContentLoaded', function () {
    var map = L.map("map", {
        zoomControl: true,
        crs: L.CRS.Simple, // Utilizza CRS Simple per mappare i tiles statici
        zoom: 13 // Imposta lo zoom iniziale su 13
    });

    const tileUrl = "{% static 'qwen_map/tiles/{z}/{x}/{y}.png' %}";
    L.tileLayer(tileUrl, {
        tms: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    // Vista approssimativa di fallback su Carrara
    const fallbackBounds = L.latLngBounds([
        [44.02, 10.02],
        [44.13, 10.18]
    ]);
    map.fitBounds(fallbackBounds, {
        padding: [20, 20]
    });

    // Aggiungi evento per caricare il file GeoJSON locale
    document.getElementById('loadGeoJSON').addEventListener('click', function () {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.geojson';

        input.onchange = function (event) {
            console.log("File selezionato:", event.target.files[0]);
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    console.log("Contenuto del file GeoJSON:", e.target.result);
                    try {
                        const geojsonData = JSON.parse(e.target.result);
                        L.geoJSON(geojsonData, {
                            style: {
                                color: "#ff0000",
                                weight: 2,
                                fillColor: "#ff0000",
                                fillOpacity: 0.3
                            }
                        }).addTo(map);
                    } catch (error) {
                        console.error("Errore durante il parsing del GeoJSON:", error);
                    }
                };
                reader.readAsText(file);
            }
        };

        input.click();
    });
});