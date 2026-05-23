import api from './axios';

export const listTeamMembers = () => api.get('/api/team');

export const inviteUser = (data) => api.post('/api/team/invite', data);

export const acceptInvite = (data) => api.post('/api/team/accept-invite', data);

export const updateTeamMember = (userId, data) => api.patch(`/api/team/${userId}`, data);

export const removeTeamMember = (userId) => api.delete(`/api/team/${userId}`);

export const resetTeamMemberPassword = (userId) => api.post(`/api/team/${userId}/reset-password`);

export const getMemberPermissions = (userId) => api.get(`/api/team/${userId}/permissions`);
export const setMemberPermissions = (userId, data) => api.put(`/api/team/${userId}/permissions`, data);
