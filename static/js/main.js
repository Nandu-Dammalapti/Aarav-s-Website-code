// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const videoInput = document.getElementById('videoInput');
const selectedFile = document.getElementById('selectedFile');
const fileName = document.getElementById('fileName');
const removeFile = document.getElementById('removeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const uploadSection = document.getElementById('uploadSection');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const resetBtn = document.getElementById('resetBtn');

// Results elements
const formScore = document.getElementById('formScore');
const goodFrames = document.getElementById('goodFrames');
const badFrames = document.getElementById('badFrames');
const avgLeftAngle = document.getElementById('avgLeftAngle');
const avgRightAngle = document.getElementById('avgRightAngle');
const anglesTableBody = document.getElementById('anglesTableBody');
const framesGallery = document.getElementById('framesGallery');

let selectedVideoFile = null;

// Event Listeners
uploadArea.addEventListener('click', () => videoInput.click());
uploadArea.addEventListener('dragover', handleDragOver);
uploadArea.addEventListener('dragleave', handleDragLeave);
uploadArea.addEventListener('drop', handleDrop);
videoInput.addEventListener('change', handleFileSelect);
removeFile.addEventListener('click', handleRemoveFile);
analyzeBtn.addEventListener('click', handleAnalyze);
resetBtn.addEventListener('click', handleReset);

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// File Selection Handler
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    // Validate file type
    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm'];
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const validExtensions = ['mp4', 'avi', 'mov', 'mkv', 'webm'];

    if (!validTypes.includes(file.type) && !validExtensions.includes(fileExtension)) {
        alert('Please upload a valid video file (MP4, AVI, MOV, MKV, or WebM)');
        return;
    }

    // Check file size (100MB limit)
    if (file.size > 100 * 1024 * 1024) {
        alert('File size must be less than 100MB');
        return;
    }

    selectedVideoFile = file;
    fileName.textContent = file.name;
    selectedFile.style.display = 'flex';
    analyzeBtn.disabled = false;
}

function handleRemoveFile(e) {
    e.stopPropagation();
    selectedVideoFile = null;
    videoInput.value = '';
    fileName.textContent = '';
    selectedFile.style.display = 'none';
    analyzeBtn.disabled = true;
}

// Analyze Handler
async function handleAnalyze() {
    if (!selectedVideoFile) return;

    // Show loading
    uploadSection.style.display = 'none';
    loadingSection.style.display = 'block';
    resultsSection.style.display = 'none';

    // Create form data
    const formData = new FormData();
    formData.append('video', selectedVideoFile);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to process video');
        }

        // Display results
        displayResults(data);

    } catch (error) {
        alert('Error: ' + error.message);
        handleReset();
    }
}

// Display Results
function displayResults(data) {
    const { frames, summary } = data;

    // Update summary
    formScore.textContent = summary.form_score + '%';
    goodFrames.textContent = summary.good_form_frames;
    badFrames.textContent = summary.bad_form_frames;
    avgLeftAngle.textContent = summary.avg_left_angle;
    avgRightAngle.textContent = summary.avg_right_angle;

    // Update score color based on value
    const scoreItem = document.querySelector('.summary-item.score');
    if (summary.form_score >= 80) {
        scoreItem.style.borderColor = 'var(--success)';
    } else if (summary.form_score >= 50) {
        scoreItem.style.borderColor = 'var(--warning)';
    } else {
        scoreItem.style.borderColor = 'var(--danger)';
    }

    // Populate angles table
    anglesTableBody.innerHTML = '';
    frames.forEach((frame, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>Frame ${frame.frame_number}</td>
            <td>${frame.left_angle !== null ? frame.left_angle + '°' : 'N/A'}</td>
            <td>${frame.right_angle !== null ? frame.right_angle + '°' : 'N/A'}</td>
            <td>
                <span class="status-badge ${frame.bad_form ? 'bad' : 'good'}">
                    ${frame.bad_form ? 'Bad Form' : 'Good Form'}
                </span>
            </td>
        `;
        anglesTableBody.appendChild(row);
    });

    // Populate frames gallery
    framesGallery.innerHTML = '';
    frames.forEach((frame, index) => {
        const frameItem = document.createElement('div');
        frameItem.className = 'frame-item';
        frameItem.innerHTML = `
            <img src="${frame.image}" alt="Frame ${frame.frame_number}">
            <div class="frame-info">
                <div class="frame-number">Frame ${frame.frame_number}</div>
                <div class="frame-angles">
                    <div class="frame-angle">L: <span>${frame.left_angle !== null ? frame.left_angle + '°' : 'N/A'}</span></div>
                    <div class="frame-angle">R: <span>${frame.right_angle !== null ? frame.right_angle + '°' : 'N/A'}</span></div>
                </div>
                <div class="frame-status ${frame.bad_form ? 'bad' : 'good'}">
                    ${frame.bad_form ? '⚠ Bad Form' : '✓ Good Form'}
                </div>
            </div>
        `;
        framesGallery.appendChild(frameItem);
    });

    // Show results section
    loadingSection.style.display = 'none';
    resultsSection.style.display = 'block';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Reset Handler
function handleReset() {
    selectedVideoFile = null;
    videoInput.value = '';
    fileName.textContent = '';
    selectedFile.style.display = 'none';
    analyzeBtn.disabled = true;

    uploadSection.style.display = 'block';
    loadingSection.style.display = 'none';
    resultsSection.style.display = 'none';

    // Clear results
    anglesTableBody.innerHTML = '';
    framesGallery.innerHTML = '';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
