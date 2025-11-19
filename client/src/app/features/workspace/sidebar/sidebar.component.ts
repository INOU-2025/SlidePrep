import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';

@Component({
    selector: 'app-sidebar',
    standalone: true,
    imports: [CommonModule, MatListModule],
    template: `
    <div class="sidebar-content">
      <h3>Images</h3>
      <mat-list>
        <mat-list-item *ngFor="let i of [1,2,3,4,5]">
          <img matListItemAvatar src="https://via.placeholder.com/50" alt="Thumbnail">
          <div matListItemTitle>Image {{i}}</div>
        </mat-list-item>
      </mat-list>
    </div>
  `,
    styles: [`
    .sidebar-content {
      padding: 10px;
    }
    h3 {
      padding-left: 16px;
      margin-bottom: 10px;
    }
  `]
})
export class SidebarComponent { }
