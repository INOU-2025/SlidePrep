import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Project {
    id: string;
    name: string;
    date: Date;
    thumbnail?: string;
    jobId?: string; // Linked job
}

@Injectable({
    providedIn: 'root'
})
export class ProjectService {
    private projectsSubject = new BehaviorSubject<Project[]>([]);
    projects$ = this.projectsSubject.asObservable();

    constructor() {
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
}
