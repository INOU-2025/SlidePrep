import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { Project } from '../../core/services/project.service';

@Component({
    selector: 'app-top-bar',
    standalone: true,
    imports: [CommonModule, MatToolbarModule, MatButtonModule, MatIconModule, MatDividerModule],
    templateUrl: './top-bar.component.html',
    styleUrls: ['./top-bar.component.scss']
})
export class TopBarComponent {
    @Input() mode: 'home' | 'workspace' = 'home';
    @Input() project?: Project;

    constructor(private router: Router) {}

    goBack() {
        this.router.navigate(['/startup']);
    }

    newProject() {
        this.router.navigate(['/upload']);
    }

    get hasResolution(): boolean {
        return !!this.project?.width && !!this.project?.height;
    }
}
