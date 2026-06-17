import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface JobResponse {
    job_id: string;
    status: string;
    message: string;
}

export interface JobStatus {
    job_id: string;
    status: string;
    result_url?: string;
    error?: string;
    message?: string;
    progress?: number;
}

export interface UploadOptions {
    cleanGrid?: boolean;
    gridWidth?: number | null;
    gridHeight?: number | null;
    overlap?: number | null;
    pixelSize?: number | null;
    direction?: string;
    suffixFilter?: string;
}

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    private apiUrl = '/api';

    constructor(private http: HttpClient) { }

    uploadImages(files: File[], options: UploadOptions = {}): Observable<JobResponse> {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        formData.append('clean_grid', (options.cleanGrid ?? true).toString());
        if (options.gridWidth != null)       formData.append('grid_width',    String(options.gridWidth));
        if (options.gridHeight != null)      formData.append('grid_height',   String(options.gridHeight));
        if (options.overlap != null)         formData.append('overlap',       String(options.overlap));
        if (options.pixelSize != null)       formData.append('pixel_size',    String(options.pixelSize));
        if (options.direction)               formData.append('direction',     options.direction);
        if (options.suffixFilter !== undefined) formData.append('suffix_filter', options.suffixFilter);
        return this.http.post<JobResponse>(`${this.apiUrl}/jobs`, formData);
    }

    getJobStatus(jobId: string): Observable<JobStatus> {
        return this.http.get<JobStatus>(`${this.apiUrl}/jobs/${jobId}`);
    }

    deleteJob(jobId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/jobs/${jobId}`);
    }
}
