import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ProjectService, Project } from '../../../core/services/project.service';
import { TopBarComponent } from '../../../shared/top-bar/top-bar.component';
import { CreateModalComponent } from '../create-modal/create-modal.component';

const NAV_ITEMS = [
    { id: 'all',        icon: 'folder',        label: 'All slides' },
    { id: 'processing', icon: 'hourglass_top', label: 'Processing' },
    { id: 'completed',  icon: 'cloud_done',    label: 'Completed'  },
    { id: 'failed',     icon: 'error_outline', label: 'Failed'     },
];

const FILTER_TITLES: Record<string, string> = {
    all: 'Slides', processing: 'Processing', completed: 'Completed', failed: 'Failed',
};

@Component({
    selector: 'app-project-list',
    standalone: true,
    imports: [CommonModule, TopBarComponent, CreateModalComponent],
    templateUrl: './project-list.component.html',
    styleUrls: ['./project-list.component.scss']
})
export class ProjectListComponent {
    private projectService = inject(ProjectService);
    private router = inject(Router);

    projects$ = this.projectService.projects$;

    navItems = NAV_ITEMS;
    filter = 'all';
    showModal = false;
    hoveredId: string | null = null;
    confirmId: string | null = null;

    get filterTitle(): string { return FILTER_TITLES[this.filter]; }

    filterProjects(projects: Project[]): Project[] {
        if (this.filter === 'all') return projects;
        return projects.filter(p => p.status === this.filter);
    }

    countFor(projects: Project[], filterId: string): number {
        if (filterId === 'all') return projects.length;
        return projects.filter(p => p.status === filterId).length;
    }

    openProject(project: Project) {
        this.router.navigate(['/workspace', project.id]);
    }

    confirmDelete(event: MouseEvent, projectId: string) {
        event.stopPropagation();
        this.confirmId = projectId;
    }

    cancelDelete(event: MouseEvent) {
        event.stopPropagation();
        this.confirmId = null;
    }

    deleteProject(event: MouseEvent, projectId: string) {
        event.stopPropagation();
        this.projectService.deleteProject(projectId);
        this.confirmId = null;
        this.hoveredId = null;
    }

    formatDate(d: Date | string | null): string {
        if (!d) return '—';
        const date = new Date(d);
        const diff = (Date.now() - date.getTime()) / 1000;
        if (diff < 60)     return 'just now';
        if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
        if (diff < 172800) return 'yesterday';
        if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    formatDims(p: Project): string | null {
        return p.width && p.height
            ? `${p.width.toLocaleString()} × ${p.height.toLocaleString()} px`
            : null;
    }
}
