import { Component, AfterViewInit, OnChanges, SimpleChanges, Input, Output, EventEmitter, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import OpenSeadragon from 'openseadragon';

@Component({
    selector: 'app-viewer',
    standalone: true,
    imports: [CommonModule],
    template: `
        <div class="viewer-host">
            <div id="openseadragon-viewer" style="width: 100%; height: 100%;"></div>
            <div class="cursor-info" *ngIf="mouseInViewport">
                <span class="coords">X: {{ mouseX }}&nbsp;&nbsp;Y: {{ mouseY }}</span>
                <span class="resolution" *ngIf="resolution != null">{{ resolution | number:'1.3-3' }} µm/px</span>
            </div>
        </div>
    `,
    styles: [`
        :host { display: block; height: 100%; }
        .viewer-host { position: relative; width: 100%; height: 100%; }
        .cursor-info {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.65);
            color: #e0e0e0;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            gap: 1px;
            backdrop-filter: blur(2px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .resolution { color: #90caf9; }
    `]
})
export class ViewerComponent implements AfterViewInit, OnChanges {
    private viewer: any;
    private homeZoom: number = 1;

    @Input() imageUrl: string = '';
    @Input() resolution: number | null = null;
    @Output() zoomChange = new EventEmitter<number>();

    mouseX: number = 0;
    mouseY: number = 0;
    mouseInViewport: boolean = false;

    constructor(private ngZone: NgZone) {}

    ngAfterViewInit() {
        this.initViewer();
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['imageUrl'] && !changes['imageUrl'].firstChange) {
            if (this.viewer) {
                const url = this.imageUrl;
                const isDzi = url.endsWith('.dzi');
                this.viewer.open(isDzi ? url : { type: 'image', url });
            }
        }
    }

    zoomIn()    { this.viewer?.viewport.zoomBy(2, null, true); }
    zoomOut()   { this.viewer?.viewport.zoomBy(0.5, null, true); }
    resetZoom() { this.viewer?.viewport.goHome(true); }

    private initViewer() {
        if (this.viewer) return;

        const url = this.imageUrl || 'https://libimages1.princeton.edu/loris/pudl0001%2F4609321%2Fs42%2F00000001.jp2/full/full/0/default.jpg';
        const isDzi = url.endsWith('.dzi');

        this.viewer = OpenSeadragon({
            id: 'openseadragon-viewer',
            prefixUrl: 'https://openseadragon.github.io/openseadragon/images/',
            tileSources: isDzi ? url : { type: 'image', url },
            showNavigationControl: false,
            showNavigator:    true,
            navigatorPosition: 'BOTTOM_RIGHT',
            navigatorHeight:  '100px',
            navigatorWidth:   '150px',
        });

        this.viewer.addHandler('open', () => {
            this.homeZoom = this.viewer.viewport.getHomeZoom();
            this.zoomChange.emit(1.0);
        });

        this.viewer.addHandler('zoom', (event: any) => {
            this.zoomChange.emit(event.zoom / this.homeZoom);
        });

        this.viewer.addHandler('canvas-mousemove', (event: any) => {
            const imageCoords = this.viewer.viewport.viewerElementToImageCoordinates(event.position);
            this.ngZone.run(() => {
                this.mouseX = Math.round(imageCoords.x);
                this.mouseY = Math.round(imageCoords.y);
                this.mouseInViewport = true;
            });
        });

        this.viewer.addHandler('canvas-exit', () => {
            this.ngZone.run(() => {
                this.mouseInViewport = false;
            });
        });
    }
}
