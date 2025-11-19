import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Viewer } from './viewer';

describe('Viewer', () => {
  let component: Viewer;
  let fixture: ComponentFixture<Viewer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Viewer]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Viewer);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
