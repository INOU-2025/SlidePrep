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

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    private apiUrl = '/api';

    constructor(private http: HttpClient) { }

    uploadImages(files: File[], cleanGrid: boolean = true): Observable<JobResponse> {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        formData.append('clean_grid', cleanGrid.toString());
        return this.http.post<JobResponse>(`${this.apiUrl}/jobs`, formData);
    }

    getJobStatus(jobId: string): Observable<JobStatus> {
        return this.http.get<JobStatus>(`${this.apiUrl}/jobs/${jobId}`);
    }

    deleteJob(jobId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/jobs/${jobId}`);
    }
}
