document.addEventListener('DOMContentLoaded', () => {
    // Current date for default input
    const dateInput = document.getElementById('meetingDate');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }

    // Connect SocketIO
    let socket = null;
    try {
        if (typeof io !== 'undefined') {
            socket = io();
        } else {
            console.warn("Socket.io not loaded. Realtime updates disabled.");
        }
    } catch (e) {
        console.error("Socket.io error:", e);
    }

    // State
    let timerInterval;
    let secondsElapsed = 0;

    // Format timer
    const formatTime = (totalSeconds) => {
        const h = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
        const s = (totalSeconds % 60).toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    };

    const showToast = (message, type = 'info') => {
        const toastEl = document.getElementById('appToast');
        const msgEl = document.getElementById('toastMessage');
        let icon = '<i class="bi bi-info-circle text-primary me-2 fs-5"></i>';
        if (type === 'success') icon = '<i class="bi bi-check-circle text-success me-2 fs-5"></i>';
        if (type === 'error') icon = '<i class="bi bi-exclamation-circle text-danger me-2 fs-5"></i>';

        msgEl.innerHTML = `${icon} <span>${message}</span>`;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    };

    // --- Tab Event Listeners ---
    document.getElementById('library-tab').addEventListener('shown.bs.tab', () => {
        loadMeetings();
    });

    // --- Forms & Buttons ---
    const btnCreateMeeting = document.getElementById('btnCreateMeeting');
    const createForm = document.getElementById('createMeetingForm');
    const btnMic = document.getElementById('btnMic');
    const btnStopRecord = document.getElementById('btnStopRecord');

    // Create Meeting
    btnCreateMeeting.addEventListener('click', async (e) => {
        e.preventDefault();

        // Basic validation since we bypassed native form submit
        if (!document.getElementById('meetingName').value || !document.getElementById('meetingDate').value) {
            showToast('Veuillez remplir le nom et la date.', 'error');
            return;
        }

        const name = document.getElementById('meetingName').value;
        const date = document.getElementById('meetingDate').value;
        const lang = document.getElementById('meetingLang').value;

        try {
            const res = await fetch('/api/meetings/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, date, language: lang })
            });
            const data = await res.json();

            if (data.status === 'ok') {
                document.getElementById('activeMeetingName').textContent = name;
                document.getElementById('activeMeetingId').textContent = data.meeting_id;

                // Hide config, show recording UI
                document.getElementById('configCard').classList.add('d-none');
                document.getElementById('recordingCard').classList.remove('d-none');
                showToast('Réunion préparée. Prêt à enregistrer.', 'success');
            }
        } catch (err) {
            showToast('Erreur de création.', 'error');
            console.error(err);
        }
    });

    // Start UI
    const startRecordingUI = () => {
        btnMic.classList.remove('mic-idle');
        btnMic.classList.add('mic-recording');
        document.getElementById('micPulse').classList.remove('d-none');
        btnStopRecord.classList.remove('d-none');

        secondsElapsed = 0;
        document.getElementById('recordTimer').textContent = "00:00:00";
        timerInterval = setInterval(() => {
            secondsElapsed++;
            document.getElementById('recordTimer').textContent = formatTime(secondsElapsed);
        }, 1000);
    }

    const stopRecordingUI = () => {
        btnMic.classList.add('mic-idle');
        btnMic.classList.remove('mic-recording');
        document.getElementById('micPulse').classList.add('d-none');
        btnStopRecord.classList.add('d-none');
        clearInterval(timerInterval);

        document.getElementById('recordingCard').classList.add('d-none');
        document.getElementById('pipelineCard').classList.remove('d-none');
    }

    // Start Recording Action
    btnMic.addEventListener('click', async () => {
        if (btnMic.classList.contains('mic-recording')) return;
        try {
            await fetch('/api/recording/start', { method: 'POST' });
            startRecordingUI();
        } catch (err) {
            showToast('Erreur de démarrage micro.', 'error');
        }
    });

    // Stop Recording Action
    btnStopRecord.addEventListener('click', async () => {
        try {
            await fetch('/api/recording/stop', { method: 'POST' });
            stopRecordingUI();
        } catch (err) {
            showToast("Erreur d'arrêt.", 'error');
        }
    });

    // --- Socket Updates ---
    if (socket) {
        socket.on("status_update", (data) => {
            console.log("Status update:", data);

            const statusEl = document.getElementById('pipelineStatusText');
            const progressEl = document.getElementById('pipelineProgressText');
            const barEl = document.getElementById('pipelineProgressBar');

            if (data.status === 'saving') {
                updatePipelineStep('saving', 5, 'Sauvegarde Audio...');
            } else if (data.status === 'transcribing') {
                updatePipelineStep('transcribing', data.progress || 10, 'Transcription en cours...');
            } else if (data.status === 'summarizing') {
                updatePipelineStep('summarizing', data.progress || 60, 'Génération du résumé...');
            } else if (data.status === 'done') {
                updatePipelineStep('done', 100, 'Terminé !');
                setTimeout(() => {
                    document.getElementById('pipelineCard').classList.add('d-none');
                    document.getElementById('configCard').classList.remove('d-none');
                    createForm.reset();
                    showToast('Le compte-rendu est prêt ! Vous pouvez le consulter dans la bibliothèque.', 'success');
                }, 3000);
            } else if (data.status.startsWith('error')) {
                showToast('Erreur pipeline : ' + data.status, 'error');
                progressBarDanger(barEl, statusEl, 'Erreur de traitement');
            }
        });
    } else {
        // Fallback polling mechanism if socketio fails to load
        console.log("Socket disabled, using fallback polling for status updates.");
        setInterval(async () => {
            const pipCard = document.getElementById('pipelineCard');
            if (pipCard && !pipCard.classList.contains('d-none')) {
                try {
                    const res = await fetch('/api/recording/status');
                    const data = await res.json();

                    if (data.status === 'processing' || data.status === 'transcribing' || data.status === 'summarizing') {
                        updatePipelineStep(data.status, data.progress || 50, data.status + '...');
                    } else if (data.status === 'done') {
                        updatePipelineStep('done', 100, 'Terminé !');
                        setTimeout(() => {
                            document.getElementById('pipelineCard').classList.add('d-none');
                            document.getElementById('configCard').classList.remove('d-none');
                            createForm.reset();
                            showToast('Le compte-rendu est prêt ! Vous pouvez le consulter dans la bibliothèque.', 'success');
                        }, 3000);
                    }
                } catch (e) { }
            }
        }, 3000);
    }

    const updatePipelineStep = (step, progress, text) => {
        const statusEl = document.getElementById('pipelineStatusText');
        const progressEl = document.getElementById('pipelineProgressText');
        const barEl = document.getElementById('pipelineProgressBar');

        statusEl.textContent = text;
        progressEl.textContent = progress + '%';
        barEl.style.width = progress + '%';

        // Update icons
        const steps = ['saving', 'transcribing', 'summarizing'];
        let currentIndex = steps.indexOf(step);
        if (step === 'done') currentIndex = 3;

        steps.forEach((s, idx) => {
            const el = document.getElementById('step-' + s);
            if (!el) return;
            el.classList.remove('active', 'done');
            if (idx < currentIndex) el.classList.add('done');
            else if (idx === currentIndex) el.classList.add('active');
        });
    }

    const progressBarDanger = (bar, status, text) => {
        bar.classList.remove('bg-primary');
        bar.classList.add('bg-danger');
        status.textContent = text;
    };

    // --- Library Functions ---
    window.loadMeetings = async () => {
        const grid = document.getElementById('meetingsGrid');
        grid.innerHTML = '<div class="col-12 text-center text-muted py-5"><div class="spinner-border mb-3" role="status"></div><br>Chargement...</div>';
        try {
            const res = await fetch('/api/meetings');
            const data = await res.json();

            if (data.length === 0) {
                grid.innerHTML = '<div class="col-12 text-center text-muted py-5"><i class="bi bi-inbox fs-1 mb-2"></i><br>Aucune réunion trouvée.</div>';
                return;
            }

            grid.innerHTML = '';
            data.forEach(m => {
                // Parse meeting id (name_date)
                const parts = m.id.split('_');
                const name = parts[0].replace(/-/g, ' ');
                const date = parts.length > 1 ? parts[1] : '';

                const col = document.createElement('div');
                col.className = 'col-md-6 col-lg-4';
                col.innerHTML = `
                    <div class="card glass-card h-100 transition-all hover-transform">
                        <div class="card-body">
                            <h5 class="card-title text-truncate text-capitalize fw-semibold">${name}</h5>
                            <h6 class="card-subtitle mb-3 text-muted small"><i class="bi bi-calendar3 me-1"></i> ${date}</h6>
                            
                            <div class="d-flex flex-wrap gap-2 mb-4">
                                ${m.has_audio ? `<a href="/api/meetings/${m.id}/download/wav" class="badge rounded-pill bg-primary bg-opacity-25 text-primary text-decoration-none border border-primary border-opacity-25"><i class="bi bi-file-music me-1"></i> Audio (.wav)</a>` : ''}
                                ${m.has_txt ? `<a href="/api/meetings/${m.id}/download/txt" class="badge rounded-pill bg-light bg-opacity-10 text-light text-decoration-none border border-light border-opacity-25"><i class="bi bi-justify-left me-1"></i> Transcrit</a>` : ''}
                                ${m.has_md ? `<a href="/api/meetings/${m.id}/download/md" class="badge rounded-pill bg-success bg-opacity-25 text-success text-decoration-none border border-success border-opacity-25"><i class="bi bi-markdown me-1"></i> Compte-rendu</a>` : ''}
                            </div>
                            
                            ${m.has_md ? `
                                <button class="btn btn-sm btn-outline-light w-100" onclick="viewSummary('${m.id}')">
                                    <i class="bi bi-eye me-1"></i> Voir le compte-rendu
                                </button>
                            ` : `
                                <button class="btn btn-sm btn-outline-secondary w-100 disabled">
                                    En cours de traitement...
                                </button>
                            `}
                        </div>
                    </div>
                `;
                grid.appendChild(col);
            });

        } catch (err) {
            grid.innerHTML = '<div class="col-12 text-danger">Erreur de chargement.</div>';
            console.error(err);
        }
    };

    // Simple popup for summary preview
    window.viewSummary = async (meetingId) => {
        try {
            const res = await fetch(`/api/meetings/${meetingId}/download/md`);
            if (!res.ok) throw new Error("File not found");
            const mdText = await res.text();

            let htmlContent = "";
            if (typeof marked !== 'undefined') {
                htmlContent = marked.parse(mdText);
            } else {
                htmlContent = `<pre style="white-space: pre-wrap; font-family: inherit;">${mdText.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
                console.warn("Marked.js not loaded, showing raw text instead of Markdown format.");
            }

            // Reusing the configCard space for preview, or modal
            // Creating a simple modal on the fly
            let modalHtml = `
            <div class="modal fade" id="summaryModal" tabindex="-1">
            <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content glass-card">
                    <div class="modal-header border-0">
                        <h5 class="modal-title ms-2"><i class="bi bi-body-text me-2"></i>Compte-Rendu</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-4 md-content text-start">
                        ${htmlContent}
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-secondary rounded-pill px-4" data-bs-dismiss="modal">Fermer</button>
                        <a href="/api/meetings/${meetingId}/download/md" class="btn btn-primary rounded-pill px-4"><i class="bi bi-download me-2"></i>Télécharger (.md)</a>
                    </div>
                </div>
            </div>
            </div >
                `;

            // Remove existing modal if any
            const existing = document.getElementById('summaryModal');
            if (existing) existing.remove();

            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalEl = new bootstrap.Modal(document.getElementById('summaryModal'));
            modalEl.show();

        } catch (err) {
            showToast("Erreur lors du chargement de l'aperçu.", 'error');
        }
    };
});
