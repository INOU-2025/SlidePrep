import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Project } from '../../core/services/project.service';

export const ZOOMS = [1, 2, 4, 10, 20, 40];

@Component({
    selector: 'app-top-bar',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './top-bar.component.html',
    styleUrls: ['./top-bar.component.scss']
})
export class TopBarComponent {
    @Input() mode: 'home' | 'workspace' = 'home';
    @Input() project?: Project;
    @Input() zoomIdx: number = 1;

    @Output() newSlide    = new EventEmitter<void>();
    @Output() zoomIn      = new EventEmitter<void>();
    @Output() zoomOut     = new EventEmitter<void>();
    @Output() resetZoom   = new EventEmitter<void>();
    @Output() export      = new EventEmitter<void>();

    readonly wordmarkCells = Array.from({ length: 9 }, (_, i) => i);
    readonly zooms = ZOOMS;

    constructor(private router: Router) {}

    goBack() { this.router.navigate(['/startup']); }

    get currentZoomLabel(): string { return ZOOMS[this.zoomIdx] + '×'; }

    get dims(): string {
        const w = this.project?.width;
        const h = this.project?.height;
        return w && h ? `${w.toLocaleString()} × ${h.toLocaleString()} px` : '—';
    }

    get canShowControls(): boolean {
        return this.project?.status === 'completed';
    }
}
