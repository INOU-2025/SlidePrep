import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';

@Component({
    selector: 'app-upload-dropzone',
    standalone: true,
    imports: [CommonModule, MatButtonModule, MatIconModule, MatProgressBarModule, MatListModule],
    templateUrl: './upload-dropzone.component.html',
    styleUrls: ['./upload-dropzone.component.scss']
})
export class UploadDropzoneComponent {
    files: File[] = [];
    isUploading = false;
    uploadProgress = 0;

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
        if (this.files.length === 0) return;

        this.isUploading = true;
        this.apiService.uploadImages(this.files).subscribe({
            next: (response) => {
                // Create a new project entry
                this.projectService.addProject({
                    id: response.job_id,
                    name: `Project ${new Date().toLocaleString()}`,
                    date: new Date(),
                    jobId: response.job_id
                });

                this.isUploading = false;
                this.router.navigate(['/workspace', response.job_id]);
            },
            error: (err) => {
                console.error('Upload failed', err);
                this.isUploading = false;
                // Handle error (show snackbar)
            }
        });
    }
}
