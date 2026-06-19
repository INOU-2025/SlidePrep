import { Component, AfterViewInit, OnChanges, SimpleChanges, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import OpenSeadragon from 'openseadragon';

@Component({
    selector: 'app-viewer',
    standalone: true,
    imports: [CommonModule],
    template: '<div id="openseadragon-viewer" style="width: 100%; height: 100%;"></div>',
    styles: [':host { display: block; height: 100%; }']
})
export class ViewerComponent implements AfterViewInit, OnChanges {
    private viewer: any;
    private homeZoom: number = 1;

    @Input() imageUrl: string = '';
    @Output() zoomChange = new EventEmitter<number>();

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
            showNavigator: true
        });

        this.viewer.addHandler('open', () => {
            this.homeZoom = this.viewer.viewport.getHomeZoom();
            this.zoomChange.emit(1.0);
        });

        this.viewer.addHandler('zoom', (event: any) => {
            this.zoomChange.emit(event.zoom / this.homeZoom);
        });
    }
}
