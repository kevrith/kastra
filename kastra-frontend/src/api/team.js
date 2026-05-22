import api from './axios';

export const listTeamMembers = () => api.get('/team');

export const inviteUser = (data) => api.post('/team/invite', data);

export const acceptInvite = (data) => api.post('/team/accept-invite', data);

export const updateTeamMember = (userId, data) => api.patch(`/team/${userId}`, data);

export const removeTeamMember = (userId) => api.delete(`/team/${userId}`);

export const resetTeamMemberPassword = (userId) => api.post(`/team/${userId}/reset-password`);
