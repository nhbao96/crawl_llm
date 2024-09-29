document.getElementById("start_crawl").onclick = function() {
    var website_url = document.getElementById("website_url").value;
    var chrome_driver_path = document.getElementById("chrome_driver_path").value;
    var output_file = document.getElementById("output_file").value;

    // Show the loading popup
    document.getElementById("loading-popup").style.display = "flex";

    fetch('/start_crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `website_url=${website_url}&chrome_driver_path=${chrome_driver_path}&output_file=${output_file}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            startRealTimeStream();
        } else {
            document.getElementById("loading-popup").style.display = "none";
            alert(data.message);
        }
    })
    .catch(error => {
        document.getElementById("loading-popup").style.display = "none";
        console.error('Error:', error);
    });
};

function startRealTimeStream() {
    var logPanel = document.getElementById("log-panel");
    var progressFill = document.getElementById("progress-bar-fill");

    const eventSource = new EventSource('/stream');
    eventSource.onmessage = function(event) {
        logPanel.innerHTML += `<div>${event.data}</div>`;
        logPanel.scrollTop = logPanel.scrollHeight;  // Auto scroll to bottom

        var progress = Math.min(parseFloat(progressFill.style.width) + 10, 100);
        progressFill.style.width = progress + '%';

        if (progress >= 100) {
            document.getElementById("loading-popup").style.display = "none";
            eventSource.close();
        }
    };
}
