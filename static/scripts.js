document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const website_url = document.getElementById('website_url');
    const output_file_base = document.getElementById('output_file');
    const file_format = document.getElementById('file_format');
    const logPanel = document.getElementById('logContent');

    let eventSource = null;

    startBtn.addEventListener('click', function () {
        if (website_url.value === '' || output_file_base.value === '') {
            alert('Vui lòng nhập đầy đủ thông tin URL và tên file output.');
            return;
        }

        const output_file = `${output_file_base.value}.${file_format.value}`;

        fetch('/start_crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                website_url: website_url.value,
                output_file: output_file,
                format_type: file_format.value
            }),
        })
            .then(response => response.json())
            .then(data => {
                logPanel.innerHTML += `<p><b>${getCurrentTime()} [INFO]:</b> ${data.message}</p>`;
                startBtn.disabled = true;
                stopBtn.disabled = false;
                downloadBtn.disabled = true;

                eventSource = new EventSource('/crawl_log');
                eventSource.onmessage = function (event) {
                    logPanel.innerHTML += `<p>${event.data}</p>`;
                    logPanel.scrollTop = logPanel.scrollHeight; 
                };
            })
            .catch(error => {
                console.error('Error:', error);
                logPanel.innerHTML += `<p style="color: red;">Có lỗi xảy ra: ${error.message}</p>`;
            });
    });

    stopBtn.addEventListener('click', function () {
        fetch('/stop_crawl', {
            method: 'POST',
        })
            .then(response => response.json())
            .then(data => {
                logPanel.innerHTML += `<p><b>${getCurrentTime()} [INFO]:</b> ${data.message}</p>`;
                startBtn.disabled = false;
                stopBtn.disabled = true;
                downloadBtn.disabled = false;

                if (eventSource) {
                    eventSource.close();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                logPanel.innerHTML += `<p style="color: red;">Có lỗi xảy ra: ${error.message}</p>`;
            });
    });

    downloadBtn.addEventListener('click', function () {
        window.location.href = '/download_log'; 
    });

    function getCurrentTime() {
        const now = new Date();
        return now.toISOString().replace('T', ' ').substring(0, 19);
    }
});
