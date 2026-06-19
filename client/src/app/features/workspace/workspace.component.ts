import { Component, OnInit, OnDestroy, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

import { ViewerComponent } from './viewer/viewer.component';
import { TopBarComponent, ZOOMS } from '../../shared/top-bar/top-bar.component';
import { ApiService, JobStatus } from '../../core/services/api.service';
import { ProjectService, Project } from '../../core/services/project.service';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [CommonModule, ViewerComponent, TopBarComponent],
  template: `
    <div class="workspace-container">
      <app-top-bar
        mode="workspace"
        [project]="project"
        [zoomIdx]="zoomIdx"
        (zoomIn)="stepZoom(1)"
        (zoomOut)="stepZoom(-1)"
        (resetZoom)="zoomIdx = 1; viewerRef?.resetZoom()"
        (export)="doExport()">
      </app-top-bar>

      <!-- Processing state -->
      <div class="state-overlay" *ngIf="project?.status === 'processing' && !imageUrl">
        <span class="material-symbols-rounded state-icon processing">hourglass_top</span>
        <div class="state-text">
          <div class="state-heading">Processing</div>
          <div class="state-sub">Slide will appear when complete</div>
        </div>
      </div>

      <!-- Failed state -->
      <div class="state-overlay" *ngIf="project?.status === 'failed'">
        <span class="material-symbols-rounded state-icon failed">error_outline</span>
        <div class="state-text">
          <div class="state-heading">Processing failed</div>
          <div class="state-sub">Check the file format and parameters, then try again.</div>
        </div>
        <button class="btn-secondary" type="button" (click)="router.navigate(['/startup'])">
          <span class="material-symbols-rounded">arrow_back</span>
          Back to slides
        </button>
      </div>

      <!-- Viewer -->
      <app-viewer
        *ngIf="imageUrl"
        #viewerRef
        class="viewer"
        [imageUrl]="imageUrl"
        [resolution]="project?.pixelSize ?? null">
      </app-viewer>
    </div>
  `,
  styles: [`
    .workspace-container {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
      background: var(--surface-void);
    }
    .viewer {
      flex: 1;
      min-height: 0;
      background: var(--surface-void);
    }
    .state-overlay {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 14px;
    }
    .state-icon {
      font-size: 36px;
      opacity: 0.7;
      &.processing { color: var(--accent); }
      &.failed     { color: var(--danger); }
    }
    .state-text {
      text-align: center;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .state-heading {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      font-family: var(--font-sans);
    }
    .state-sub {
      font-size: 12px;
      color: var(--text-muted);
      font-family: var(--font-sans);
    }
    .btn-secondary {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 0 14px;
      height: 32px;
      border: 1px solid var(--border-default);
      border-radius: 4px;
      background: var(--surface-card);
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 100ms, color 100ms;
      .material-symbols-rounded { font-size: 16px; }
      &:hover { background: var(--surface-hover); color: var(--text-primary); }
    }
  `]
})
export class WorkspaceComponent implements OnInit, OnDestroy {
  @ViewChild('viewerRef') viewerRef?: ViewerComponent;

  private route         = inject(ActivatedRoute);
  readonly router       = inject(Router);
  private apiService    = inject(ApiService);
  private projectService = inject(ProjectService);

  imageUrl = '';
  project: Project | undefined;
  zoomIdx  = 1;

  private pollInterval: any;
  private sub?: Subscription;

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (!jobId) return;

    // Reactively track project changes (modal updates status in real-time)
    this.sub = this.projectService.projects$.subscribe(projects => {
      this.project = projects.find(p => p.id === jobId);
    });

    this.startPolling(jobId);
  }

  ngOnDestroy() {
    clearInterval(this.pollInterval);
    this.sub?.unsubscribe();
  }

  stepZoom(dir: 1 | -1) {
    const next = this.zoomIdx + dir;
    if (next < 0 || next >= ZOOMS.length) return;
    this.zoomIdx = next;
    if (dir === 1)  this.viewerRef?.zoomIn();
    else            this.viewerRef?.zoomOut();
  }

  doExport() {
    if (!this.project?.jobId) return;
    const link = document.createElement('a');
    link.href     = `/api/jobs/${this.project.jobId}/export`;
    link.download = `${this.project.name}.ome.tif`;
    link.click();
  }

  private startPolling(jobId: string) {
    this.pollInterval = setInterval(() => {
      this.apiService.getJobStatus(jobId).subscribe({
        next: (status: JobStatus) => {
          if (status.status === 'SUCCESS' || status.status === 'COMPLETED') {
            this.imageUrl = status.result_url ? `/api${status.result_url}` : this.imageUrl;
            this.projectService.updateProject(jobId, {
              status:    'completed',
              thumbnail: status.thumbnail_url,
              width:     status.width,
              height:    status.height,
            });
            clearInterval(this.pollInterval);
          } else if (status.status === 'FAILURE') {
            this.projectService.updateProject(jobId, { status: 'failed' });
            clearInterval(this.pollInterval);
          }
        },
        error: () => clearInterval(this.pollInterval),
      });
    }, 2000);
  }
}
