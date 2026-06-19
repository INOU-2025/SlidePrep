import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';

const PROCESSING_PHASES = [
    { until: 22,  message: 'Detecting grid' },
    { until: 52,  message: 'Aligning tiles' },
    { until: 82,  message: 'Stitching'      },
    { until: 97,  message: 'Finalising'     },
    { until: 100, message: 'Completing'     },
];

function getPhaseMessage(progress: number): string {
    return (PROCESSING_PHASES.find(ph => progress < ph.until) ?? PROCESSING_PHASES[PROCESSING_PHASES.length - 1]).message;
}

@Component({
    selector: 'app-create-modal',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './create-modal.component.html',
    styleUrls: ['./create-modal.component.scss']
})
export class CreateModalComponent {
    @Output() closed = new EventEmitter<void>();

    step: 1 | 2 = 1;
    phase: 'idle' | 'uploading' | 'processing' = 'idle';

    uploadProgress  = 0;
    processingProgress = 0;
    processingMessage  = '';

    files: File[] = [];
    drag = false;

    // Step 1 form fields
    name       = '';
    cols       = '';
    rows       = '';
    dir        = '';
    overlap    = '';
    pixelSize  = '';
    suffix     = '';
    angle      = '';
    thresh     = '';
    cleanGrid  = true;

    private pollInterval: any;

    constructor(
        private apiService: ApiService,
        private projectService: ProjectService,
    ) {}

    get tileCount(): number { return (parseInt(this.cols) || 0) * (parseInt(this.rows) || 0); }
    get step1Valid(): boolean { return !!this.name.trim() && !!this.cols && !!this.rows; }
    get step2Valid(): boolean { return this.files.length > 0 && this.phase === 'idle'; }
    get isRunning():  boolean { return this.phase === 'uploading' || this.phase === 'processing'; }

    tryClose() {
        if (!this.isRunning) this.closed.emit();
    }

    onDragOver(e: DragEvent) {
        e.preventDefault();
        if (this.phase === 'idle') this.drag = true;
    }

    onDragLeave() { this.drag = false; }

    onDrop(e: DragEvent) {
        e.preventDefault();
        this.drag = false;
        const dropped = Array.from(e.dataTransfer?.files ?? []);
        if (dropped.length) this.files = [...this.files, ...dropped];
    }

    onFileSelected(e: Event) {
        const input = e.target as HTMLInputElement;
        if (input.files) this.files = [...this.files, ...Array.from(input.files)];
    }

    removeFile(index: number) { this.files.splice(index, 1); }
    clearFiles() { this.files = []; }

    fileIcon(f: File): string { return f.name.toLowerCase().endsWith('.zip') ? 'folder_zip' : 'image'; }

    formatSize(f: File): string {
        return f.size ? (f.size / 1024 / 1024).toFixed(1) + ' MB' : '';
    }

    upload() {
        if (!this.step2Valid) return;

        this.uploadProgress = 0;
        this.phase = 'uploading';

        this.apiService.uploadImages(this.files, {
            cleanGrid:          this.cleanGrid,
            gridWidth:          this.cols   ? +this.cols   : null,
            gridHeight:         this.rows   ? +this.rows   : null,
            overlap:            this.overlap   ? +this.overlap   : null,
            pixelSize:          this.pixelSize ? +this.pixelSize : null,
            direction:          this.dir    || undefined,
            suffixFilter:       this.suffix || '',
            gridAngle:          this.angle  ? +this.angle  : null,
            detectionThreshold: this.thresh ? +this.thresh : null,
        }).subscribe({
            next: (response) => {
                this.projectService.addProject({
                    id:        response.job_id,
                    name:      this.name.trim(),
                    date:      new Date(),
                    jobId:     response.job_id,
                    status:    'processing',
                    tileCount: this.tileCount || undefined,
                    pixelSize: this.pixelSize ? +this.pixelSize : undefined,
                });
                this.beginPolling(response.job_id);
            },
            error: () => { this.phase = 'idle'; },
        });
    }

    private beginPolling(jobId: string) {
        this.phase = 'processing';
        this.processingProgress = 0;
        this.processingMessage  = 'Detecting grid';

        this.pollInterval = setInterval(() => {
            this.apiService.getJobStatus(jobId).subscribe({
                next: (status) => {
                    if (status.progress != null) {
                        this.processingProgress = status.progress;
                        this.processingMessage  = getPhaseMessage(status.progress);
                    }
                    if (status.message) this.processingMessage = status.message;

                    if (status.status === 'COMPLETED' || status.status === 'SUCCESS') {
                        clearInterval(this.pollInterval);
                        this.projectService.updateProject(jobId, {
                            status:    'completed',
                            thumbnail: status.thumbnail_url ? `/api${status.thumbnail_url}` : undefined,
                            width:     status.width,
                            height:    status.height,
                        });
                        this.closed.emit();
                    } else if (status.status === 'FAILURE') {
                        clearInterval(this.pollInterval);
                        this.projectService.updateProject(jobId, { status: 'failed' });
                        this.closed.emit();
                    }
                },
                error: () => clearInterval(this.pollInterval),
            });
        }, 2000);
    }
}
