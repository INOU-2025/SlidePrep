import { Routes } from '@angular/router';
import { ProjectListComponent } from './features/startup/project-list/project-list.component';

export const routes: Routes = [
    { path: '', redirectTo: 'startup', pathMatch: 'full' },
    { path: 'startup', component: ProjectListComponent },
    {
        path: 'workspace/:id',
        loadComponent: () => import('./features/workspace/workspace.component').then(m => m.WorkspaceComponent)
    }
];
