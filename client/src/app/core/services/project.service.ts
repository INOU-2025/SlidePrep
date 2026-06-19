import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Project {
    id: string;
    name: string;
    date: Date;
    thumbnail?: string;
    jobId?: string;
    status: 'processing' | 'completed' | 'failed';
    tileCount?: number;
    width?: number;
    height?: number;
    pixelSize?: number;
}

@Injectable({
    providedIn: 'root'
})
export class ProjectService {
    private projectsSubject = new BehaviorSubject<Project[]>([]);
    projects$ = this.projectsSubject.asObservable();

    constructor(private apiService: ApiService) {
        this.loadProjects();
    }

    private loadProjects() {
        const stored = localStorage.getItem('projects');
        if (stored) {
            this.projectsSubject.next(JSON.parse(stored));
        }
    }

    addProject(project: Project) {
        const current = this.projectsSubject.value;
        const updated = [project, ...current];
        this.projectsSubject.next(updated);
        localStorage.setItem('projects', JSON.stringify(updated));
    }

    getProject(id: string): Project | undefined {
        return this.projectsSubject.value.find(p => p.id === id);
    }

    updateProject(id: string, changes: Partial<Project>) {
        const current = this.projectsSubject.value;
        const updated = current.map(p => p.id === id ? { ...p, ...changes } : p);
        this.projectsSubject.next(updated);
        localStorage.setItem('projects', JSON.stringify(updated));
    }

    deleteProject(id: string) {
        const current = this.projectsSubject.value;
        const project = current.find(p => p.id === id);

        if (project && project.jobId) {
            this.apiService.deleteJob(project.jobId).subscribe({
                error: (err) => console.error('Failed to delete job on server', err)
            });
        }

        const updated = current.filter(p => p.id !== id);
        this.projectsSubject.next(updated);
        localStorage.setItem('projects', JSON.stringify(updated));
    }
}
