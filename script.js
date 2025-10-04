document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileName = document.getElementById('fileName');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resetBtn = document.getElementById('resetBtn');
    const diagnosisResult = document.getElementById('diagnosisResult');
    const status = document.getElementById('status');
    const progress = document.getElementById('progress');
    const progressText = document.getElementById('progressText');

    let uploadedFile = null;

    // Upload area functionality
    uploadArea.addEventListener('click', function() {
        document.getElementById('fileInput').click();
    });

    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '#f0f9ff';
        uploadArea.style.borderColor = '#2dd4fd';
    });

    uploadArea.addEventListener('dragleave', function() {
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '#1a6c5c';
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '#1a6c5c';

        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // Hidden file input
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'fileInput';
    fileInput.accept = 'audio/*';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    fileInput.addEventListener('change', function() {
        if (fileInput.files.length) {
            handleFile(fileInput.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.type.startsWith('audio/')) {
            alert('Please upload an audio file (WAV, MP3, or FLAC)');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            alert('File size must be less than 10MB');
            return;
        }

        uploadedFile = file;
        fileName.textContent = file.name;
        analyzeBtn.disabled = false;
        status.querySelector('span').textContent = 'File ready for analysis';
    }

    // Analyze button
    analyzeBtn.addEventListener('click', async function() {
        if (!uploadedFile) return;

        analyzeBtn.disabled = true;
        status.classList.add('processing');
        status.querySelector('.status-indicator').style.background = '#FF9800';
        status.querySelector('span').textContent = 'Uploading audio to AI model...';

        let progressValue = 0;
        const progressInterval = setInterval(() => {
            if (progressValue < 90) {
                progressValue += 1;
                progress.style.width = progressValue + '%';
                progressText.textContent = progressValue + '%';
            }
        }, 100);

        const formData = new FormData();
        formData.append('file', uploadedFile);

        try {
            


             const response = await fetch('http://192.168.100.15:5000/predict', {
               method: 'POST',
                body: formData




            });

            clearInterval(progressInterval);

            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }

            const result = await response.json();

            progress.style.width = '100%';
            progressText.textContent = '100%';

            const prediction = result.prediction;

            const resultIcon = diagnosisResult.querySelector('.result-icon');
            const resultText = diagnosisResult.querySelector('.result-text');

            let iconClass = '';
            if (prediction === 'Healthy') {
                iconClass = 'healthy';
                resultIcon.innerHTML = '<i class="fas fa-heartbeat"></i>';
            } else if (prediction === 'COPD') {
                iconClass = 'copd';
                resultIcon.innerHTML = '<i class="fas fa-lungs-virus"></i>';
            } else {
                iconClass = 'pneumonia';
                resultIcon.innerHTML = '<i class="fas fa-virus"></i>';
            }

            resultIcon.className = 'result-icon ' + iconClass;
            resultText.textContent = `Diagnosis: ${prediction}`;
            resultText.className = 'result-text ' + iconClass;

            status.classList.remove('processing');
            status.querySelector('.status-indicator').style.background = '#4CAF50';
            status.querySelector('span').textContent = 'Analysis complete';

        } catch (error) {
            clearInterval(progressInterval);
            alert('Error: ' + error.message);
            analyzeBtn.disabled = false;
            status.classList.remove('processing');
            status.querySelector('.status-indicator').style.background = '#F44336';
            status.querySelector('span').textContent = 'Error during analysis';
        }
    });

    // Reset button
    resetBtn.addEventListener('click', function() {
        uploadedFile = null;
        fileName.textContent = '';
        analyzeBtn.disabled = true;

        const resultIcon = diagnosisResult.querySelector('.result-icon');
        const resultText = diagnosisResult.querySelector('.result-text');

        resultIcon.innerHTML = '<i class="fas fa-lungs"></i>';
        resultIcon.className = 'result-icon';
        resultText.textContent = 'Upload audio to begin analysis';
        resultText.className = 'result-text';

        progress.style.width = '0%';
        progressText.textContent = '0%';

        status.classList.remove('processing');
        status.querySelector('.status-indicator').style.background = '#4CAF50';
        status.querySelector('span').textContent = 'Ready for upload';
    });
});
