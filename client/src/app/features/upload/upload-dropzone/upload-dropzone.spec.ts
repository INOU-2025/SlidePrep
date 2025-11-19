import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadDropzone } from './upload-dropzone';

describe('UploadDropzone', () => {
  let component: UploadDropzone;
  let fixture: ComponentFixture<UploadDropzone>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadDropzone]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UploadDropzone);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
