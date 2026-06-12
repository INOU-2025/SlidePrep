import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';

@Component({
  selector: 'app-upload-dropzone',
  imports: [CommonModule, MatButtonModule, MatIconModule, MatProgressBarModule, MatListModule, MatCheckboxModule, FormsModule],
  templateUrl: './upload-dropzone.component.html',
  styleUrl: './upload-dropzone.component.scss',
})
export class UploadDropzone {
  files: File[] = [];
  isUploading = false;
  uploadProgress = 0;
  statusMessage = 'Initializing...';
  cleanGrid = true;

  constructor(
    private apiService: ApiService,
    private projectService: ProjectService,
    private router: Router
  ) {}

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
    this.statusMessage = 'Uploading...';

    this.apiService.uploadImages(this.files, this.cleanGrid).subscribe({
      next: (response) => {
        this.projectService.addProject({
          id: response.job_id,
          name: `Project ${new Date().toLocaleString()}`,
          date: new Date(),
          jobId: response.job_id
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
          if (status.message) this.statusMessage = status.message;
          if (status.progress != null) this.uploadProgress = status.progress;

          if (status.status === 'COMPLETED' || status.status === 'SUCCESS') {
            clearInterval(pollInterval);
            this.isUploading = false;
            this.router.navigate(['/workspace', jobId]);
          } else if (status.status === 'FAILURE') {
            clearInterval(pollInterval);
            this.isUploading = false;
            console.error('Processing failed', status.error);
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
