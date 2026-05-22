import api from './axios';

export const listProjects = (params) => api.get('/projects', { params });

export const createProject = (data) => api.post('/projects', data);

export const getProject = (id) => api.get(`/projects/${id}`);

export const updateProject = (id, data) => api.patch(`/projects/${id}`, data);

export const deleteProject = (id) => api.delete(`/projects/${id}`);

export const postUpdate = (projectId, body) => 
  api.post(`/projects/${projectId}/updates`, { body });

export const uploadPhoto = (projectId, formData) =>
  api.post(`/projects/${projectId}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
