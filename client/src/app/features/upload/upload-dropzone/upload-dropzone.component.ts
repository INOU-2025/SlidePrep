import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';

@Component({
    selector: 'app-upload-dropzone',
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatIconModule,
        MatProgressBarModule,
        MatListModule,
        MatCheckboxModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        FormsModule,
    ],
    templateUrl: './upload-dropzone.component.html',
    styleUrls: ['./upload-dropzone.component.scss']
})
export class UploadDropzoneComponent {
    files: File[] = [];
    isUploading = false;
    uploadProgress = 0;
    statusMessage = 'Initializing...';

    projectName: string = '';

    // Processing options
    cleanGrid = true;

    // Scan parameters
    gridWidth: number | null = null;
    gridHeight: number | null = null;
    overlap: number | null = null;
    pixelSize: number | null = null;
    direction: string = '';
    suffixFilter: string = '';

    // Grid detection parameters
    gridAngle: number | null = null;
    detectionThreshold: number | null = null;

    get canUpload(): boolean {
        return this.files.length > 0 && !this.isUploading &&
               this.projectName.trim().length > 0 &&
               this.gridWidth != null && this.gridWidth > 0 &&
               this.gridHeight != null && this.gridHeight > 0;
    }

    constructor(
        private apiService: ApiService,
        private projectService: ProjectService,
        private router: Router
    ) { }

    onFileSelected(event: any) {
        const files = event.target.files;
        if (files) {
            for (let i = 0; i < files.length; i++) {
                this.files.push(files[i]);
            }
        }
    }

    onDragOver(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
    }

    onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        const files = event.dataTransfer?.files;
        if (files) {
            for (let i = 0; i < files.length; i++) {
                this.files.push(files[i]);
            }
        }
    }

    removeFile(index: number) {
        this.files.splice(index, 1);
    }

    getFileIcon(file: File): string {
        return file.name.toLowerCase().endsWith('.zip') ? 'folder_zip' : 'image';
    }

    upload() {
        if (!this.canUpload) return;

        this.isUploading = true;
        this.statusMessage = 'Uploading...';

        this.apiService.uploadImages(this.files, {
            cleanGrid: this.cleanGrid,
            gridWidth: this.gridWidth,
            gridHeight: this.gridHeight,
            overlap: this.overlap,
            pixelSize: this.pixelSize,
            direction: this.direction,
            suffixFilter: this.suffixFilter,
            gridAngle: this.gridAngle,
            detectionThreshold: this.detectionThreshold,
        }).subscribe({
            next: (response) => {
                this.projectService.addProject({
                    id: response.job_id,
                    name: this.projectName.trim(),
                    date: new Date(),
                    jobId: response.job_id,
                    status: 'processing',
                    tileCount: (this.gridWidth ?? 0) * (this.gridHeight ?? 0) || undefined,
                });
                this.pollStatus(response.job_id);
            },
            error: (err) => {
                console.error('Upload failed', err);
                this.isUploading = false;
            }
        });
    }

    pollStatus(jobId: string) {
        const pollInterval = setInterval(() => {
            this.apiService.getJobStatus(jobId).subscribe({
                next: (status) => {
                    if (status.message) {
                        this.statusMessage = status.message;
                    }
                    if (status.progress != null) {
                        this.uploadProgress = status.progress;
                    }

                    if (status.status === 'COMPLETED' || status.status === 'SUCCESS') {
                        clearInterval(pollInterval);
                        this.isUploading = false;
                        this.projectService.updateProject(jobId, {
                            status: 'completed',
                            thumbnail: status.thumbnail_url,
                            width: status.width,
                            height: status.height,
                        });
                        this.router.navigate(['/workspace', jobId]);
                    } else if (status.status === 'FAILURE') {
                        clearInterval(pollInterval);
                        this.isUploading = false;
                        this.projectService.updateProject(jobId, { status: 'failed' });
                        console.error('Processing failed', status.error);
                    } else {
                        console.log('Processing status:', status.status);
                    }
                },
                error: (err) => {
                    console.error('Polling error', err);
                    clearInterval(pollInterval);
                    this.isUploading = false;
                }
            });
        }, 2000);
    }
}
