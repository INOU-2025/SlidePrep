import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Project } from '../../core/services/project.service';

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
    /** Actual OpenSeadragon zoom, relative to the home/fit level (1 = fit to viewport). */
    @Input() zoom: number = 1;

    @Output() newSlide    = new EventEmitter<void>();
    @Output() zoomIn      = new EventEmitter<void>();
    @Output() zoomOut     = new EventEmitter<void>();
    @Output() resetZoom   = new EventEmitter<void>();
    @Output() export      = new EventEmitter<void>();

    readonly wordmarkCells = Array.from({ length: 9 }, (_, i) => i);

    constructor(private router: Router) {}

    goBack() { this.router.navigate(['/startup']); }

    get currentZoomLabel(): string {
        const rounded = Math.round(this.zoom * 10) / 10;
        const text = Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1);
        return text + '×';
    }

    get dims(): string {
        const w = this.project?.width;
        const h = this.project?.height;
        return w && h ? `${w.toLocaleString()} × ${h.toLocaleString()} px` : '—';
    }

    get canShowControls(): boolean {
        return this.project?.status === 'completed';
    }
}
