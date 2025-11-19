import { Routes } from '@angular/router';
import { ProjectListComponent } from './features/startup/project-list/project-list.component';
import { UploadDropzoneComponent } from './features/upload/upload-dropzone/upload-dropzone.component';
import { ViewerComponent } from './features/workspace/viewer/viewer.component';
import { SidebarComponent } from './features/workspace/sidebar/sidebar.component'; // We might need a wrapper for workspace

export const routes: Routes = [
    { path: '', redirectTo: 'startup', pathMatch: 'full' },
    { path: 'startup', component: ProjectListComponent },
    { path: 'upload', component: UploadDropzoneComponent },
    {
        path: 'workspace/:id',
        loadComponent: () => import('./features/workspace/workspace.component').then(m => m.WorkspaceComponent)
    }
];
