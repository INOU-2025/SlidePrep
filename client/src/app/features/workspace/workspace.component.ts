import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ViewerComponent } from './viewer/viewer.component';
import { ActivatedRoute } from '@angular/router';
import { ApiService, JobStatus } from '../../core/services/api.service';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [CommonModule, ViewerComponent],
  template: `
    <div class="workspace-container">
      <app-viewer class="viewer" [imageUrl]="imageUrl"></app-viewer>
    </div>
  `,
  styles: [`
    .workspace-container {
      display: flex;
      height: 100vh;
      width: 100vw;
    }
    .viewer {
      flex: 1;
      background: #000;
    }
  `]
})
export class WorkspaceComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private apiService = inject(ApiService);

  imageUrl: string = '';

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (jobId) {
      this.pollJobStatus(jobId);
    }
  }

  pollJobStatus(jobId: string) {
    // Simple polling for MVP
    const interval = setInterval(() => {
      this.apiService.getJobStatus(jobId).subscribe({
        next: (status: JobStatus) => {
          if (status.status === 'SUCCESS' && status.result_url) {
            // Construct full URL. Assuming backend is on localhost:8000
            this.imageUrl = `http://localhost:8000${status.result_url}`;
            clearInterval(interval);
          } else if (status.status === 'FAILURE') {
            console.error('Job failed:', status.error);
            clearInterval(interval);
          }
        },
        error: (err) => {
          console.error('Error polling job status:', err);
          clearInterval(interval);
        }
      });
    }, 2000);
  }
}
