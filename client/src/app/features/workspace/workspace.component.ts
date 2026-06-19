import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';

import { ViewerComponent } from './viewer/viewer.component';
import { TopBarComponent } from '../../shared/top-bar/top-bar.component';
import { ApiService, JobStatus } from '../../core/services/api.service';
import { ProjectService, Project } from '../../core/services/project.service';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [CommonModule, ViewerComponent, TopBarComponent],
  template: `
    <div class="workspace-container">
      <app-top-bar mode="workspace" [project]="project"></app-top-bar>
      <app-viewer class="viewer" [imageUrl]="imageUrl"></app-viewer>
    </div>
  `,
  styles: [`
    .workspace-container {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
    }
    .viewer {
      flex: 1;
      min-height: 0;
      background: #000;
    }
  `]
})
export class WorkspaceComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);

  imageUrl: string = '';
  project: Project | undefined;

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (jobId) {
      this.project = this.projectService.getProject(jobId);
      this.pollJobStatus(jobId);
    }
  }

  pollJobStatus(jobId: string) {
    const interval = setInterval(() => {
      this.apiService.getJobStatus(jobId).subscribe({
        next: (status: JobStatus) => {
          if (status.status === 'SUCCESS' && status.result_url) {
            this.imageUrl = `/api${status.result_url}`;
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
