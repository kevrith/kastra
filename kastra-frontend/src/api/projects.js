import api from './axios';

export const listProjects = (params) => api.get('/api/projects', { params });

export const createProject = (data) => api.post('/api/projects', data);

export const getProject = (id) => api.get(`/api/projects/${id}`);

export const updateProject = (id, data) => api.patch(`/api/projects/${id}`, data);

export const deleteProject = (id) => api.delete(`/api/projects/${id}`);

export const postUpdate = (projectId, body) => 
  api.post(`/api/projects/${projectId}/updates`, { body });

export const uploadPhoto = (projectId, formData) =>
  api.post(`/api/projects/${projectId}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

export const getProjectFinancials = (projectId) => api.get(`/api/projects/${projectId}/financials`);
