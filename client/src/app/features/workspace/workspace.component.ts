import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SidebarComponent } from './sidebar/sidebar.component';
import { ViewerComponent } from './viewer/viewer.component';
import { ActivatedRoute } from '@angular/router';

@Component({
    selector: 'app-workspace',
    standalone: true,
    imports: [CommonModule, SidebarComponent, ViewerComponent],
    template: `
    <div class="workspace-container">
      <app-sidebar class="sidebar"></app-sidebar>
      <app-viewer class="viewer"></app-viewer>
    </div>
  `,
    styles: [`
    .workspace-container {
      display: flex;
      height: 100vh;
      width: 100vw;
    }
    .sidebar {
      width: 250px;
      border-right: 1px solid #ccc;
      overflow-y: auto;
    }
    .viewer {
      flex: 1;
      background: #000;
    }
  `]
})
export class WorkspaceComponent {
    constructor(private route: ActivatedRoute) { }
}
