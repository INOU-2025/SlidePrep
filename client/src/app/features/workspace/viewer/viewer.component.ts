import { Component, OnInit, AfterViewInit, ElementRef, ViewChild, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import OpenSeadragon from 'openseadragon';

@Component({
    selector: 'app-viewer',
    standalone: true,
    imports: [CommonModule],
    template: '<div id="openseadragon-viewer" style="width: 100%; height: 100%;"></div>',
    styles: [':host { display: block; height: 100%; }']
})
export class ViewerComponent implements AfterViewInit {
    private viewer: any;
    @Input() imageUrl: string = ''; // Input for the image to load

    ngAfterViewInit() {
        this.viewer = OpenSeadragon({
            id: 'openseadragon-viewer',
            prefixUrl: 'https://openseadragon.github.io/openseadragon/images/', // Use CDN images for icons
            tileSources: {
                type: 'image',
                url: this.imageUrl || 'https://libimages1.princeton.edu/loris/pudl0001%2F4609321%2Fs42%2F00000001.jp2/full/full/0/default.jpg' // Placeholder
            },
            showNavigator: true
        });
    }
}
