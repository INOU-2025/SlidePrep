import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { ProjectService, Project } from '../../../core/services/project.service';

@Component({
    selector: 'app-project-list',
    standalone: true,
    imports: [CommonModule, MatCardModule, MatButtonModule, MatListModule, MatIconModule],
    templateUrl: './project-list.component.html',
    styleUrls: ['./project-list.component.scss']
})
export class ProjectListComponent {
    private projectService = inject(ProjectService);
    private router = inject(Router);

    projects$ = this.projectService.projects$;

    createNewProject() {
        this.router.navigate(['/upload']);
    }

    openProject(project: Project) {
        this.router.navigate(['/workspace', project.id]);
    }

    deleteProject(event: Event, projectId: string) {
        event.stopPropagation();
        this.projectService.deleteProject(projectId);
    }
}
