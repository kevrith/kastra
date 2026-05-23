import { useState, useEffect } from 'react';
import { Users, UserPlus, Shield, Eye, Briefcase, HardHat, Trash2, Power, KeyRound } from 'lucide-react';
import { listTeamMembers, inviteUser, updateTeamMember, removeTeamMember, resetTeamMemberPassword } from '../api/team';
import Modal from '../components/ui/Modal';
import ConfirmDialog from '../components/ui/ConfirmDialog';

const ROLE_ICONS = {
  admin: Shield,
  manager: Briefcase,
  field_agent: HardHat,
  viewer: Eye,
};

const ROLE_LABELS = {
  admin: 'Admin',
  manager: 'Manager',
  field_agent: 'Field Agent',
  viewer: 'Viewer',
};

const ROLE_DESCRIPTIONS = {
  admin: 'Full access — manage team, settings, all data',
  manager: 'Create/edit quotations, invoices, clients, reports',
  field_agent: 'View assigned projects, post updates & photos',
  viewer: 'Read-only access to dashboard and reports',
};

export default function TeamManagement() {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', display_name: '', role: 'manager' });
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState('');
  const [confirmDialog, setConfirmDialog] = useState(null);

  useEffect(() => {
    loadMembers();
  }, []);

  const loadMembers = async () => {
    try {
      const res = await listTeamMembers();
      setMembers(res.data);
    } catch (err) {
      console.error('Failed to load team members:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    setError('');
    setInviting(true);

    try {
      await inviteUser(inviteForm);
      setShowInviteModal(false);
      setInviteForm({ email: '', display_name: '', role: 'manager' });
      loadMembers();
      alert('Invitation sent successfully!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send invitation');
    } finally {
      setInviting(false);
    }
  };

  const handleToggleActive = async (member) => {
    try {
      await updateTeamMember(member.id, { is_active: !member.is_active });
      loadMembers();
    } catch (err) {
      alert('Failed to update member status');
    }
  };

  const handleChangeRole = async (member, newRole) => {
    try {
      await updateTeamMember(member.id, { role: newRole });
      loadMembers();
    } catch (err) {
      alert('Failed to update member role');
    }
  };

  const handleRemove = async (member) => {
    setConfirmDialog({
      title: 'Remove Team Member',
      message: `Are you sure you want to remove ${member.display_name}? This action cannot be undone.`,
      onConfirm: async () => {
        try {
          await removeTeamMember(member.id);
          loadMembers();
          setConfirmDialog(null);
        } catch (err) {
          alert('Failed to remove member');
        }
      },
      onCancel: () => setConfirmDialog(null),
    });
  };

  const handleResetPassword = async (member) => {
    setConfirmDialog({
      title: 'Reset Password',
      message: `Send a password reset link to ${member.email}?`,
      onConfirm: async () => {
        try {
          await resetTeamMemberPassword(member.id);
          alert('Password reset link sent!');
          setConfirmDialog(null);
        } catch (err) {
          alert('Failed to send reset link');
        }
      },
      onCancel: () => setConfirmDialog(null),
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return <div className="p-6">Loading team members...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="w-7 h-7" />
            Team Management
          </h1>
          <p className="text-gray-600 mt-1">Invite and manage your team members</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
        >
          <UserPlus className="w-5 h-5" />
          Invite Member
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Login</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {members.map((member) => {
              const RoleIcon = ROLE_ICONS[member.role];
              return (
                <tr key={member.id}>
                  <td className="px-6 py-4">
                    <div>
                      <div className="font-medium text-gray-900">{member.display_name}</div>
                      <div className="text-sm text-gray-500">{member.email}</div>
                      {member.invited_at && !member.last_login_at && (
                        <div className="text-xs text-amber-600 mt-1">Pending invite</div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <select
                      value={member.role}
                      onChange={(e) => handleChangeRole(member, e.target.value)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      {Object.entries(ROLE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                      <RoleIcon className="w-3 h-3" />
                      {ROLE_DESCRIPTIONS[member.role]}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        member.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {member.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(member.last_login_at)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleResetPassword(member)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Reset Password"
                      >
                        <KeyRound className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleToggleActive(member)}
                        className="text-gray-600 hover:text-gray-900"
                        title={member.is_active ? 'Deactivate' : 'Activate'}
                      >
                        <Power className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleRemove(member)}
                        className="text-red-600 hover:text-red-900"
                        title="Remove"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showInviteModal && (
        <Modal open={showInviteModal} onClose={() => setShowInviteModal(false)} title="Invite Team Member">
          <form onSubmit={handleInvite} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input
                type="text"
                value={inviteForm.display_name}
                onChange={(e) => setInviteForm({ ...inviteForm, display_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                {Object.entries(ROLE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {ROLE_DESCRIPTIONS[inviteForm.role]}
              </p>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => setShowInviteModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={inviting}
                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {inviting ? 'Sending...' : 'Send Invite'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {confirmDialog && (
        <ConfirmDialog
          title={confirmDialog.title}
          message={confirmDialog.message}
          onConfirm={confirmDialog.onConfirm}
          onCancel={confirmDialog.onCancel}
        />
      )}
    </div>
  );
}
