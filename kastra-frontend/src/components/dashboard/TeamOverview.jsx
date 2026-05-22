import { useEffect, useState } from 'react';
import { Users, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { listProjects } from '../../api/projects';
import { listTeamMembers } from '../../api/team';

export default function TeamOverview() {
  const [teamStats, setTeamStats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTeamStats();
  }, []);

  const loadTeamStats = async () => {
    try {
      const [projectsRes, teamRes] = await Promise.all([
        listProjects(),
        listTeamMembers().catch(() => ({ data: [] }))
      ]);

      const projects = projectsRes.data || [];
      const members = teamRes.data || [];

      const stats = members.map(member => {
        const assigned = projects.filter(p => p.assigned_to === member.id);
        const active = assigned.filter(p => p.stage === 'in_progress');
        const completed = assigned.filter(p => p.stage === 'completed');
        
        const lastUpdate = assigned.reduce((latest, proj) => {
          const updateTime = proj.last_update_at || proj.updated_at;
          return !latest || new Date(updateTime) > new Date(latest) ? updateTime : latest;
        }, null);

        return {
          member,
          totalProjects: assigned.length,
          activeProjects: active.length,
          completedProjects: completed.length,
          lastUpdate
        };
      });

      setTeamStats(stats);
    } catch (err) {
      console.error('Failed to load team stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (lastUpdate) => {
    if (!lastUpdate) return <AlertCircle className="w-4 h-4 text-gray-400" />;
    const daysSince = Math.floor((Date.now() - new Date(lastUpdate)) / (1000 * 60 * 60 * 24));
    if (daysSince >= 7) return <AlertCircle className="w-4 h-4 text-red-500" />;
    if (daysSince >= 3) return <Clock className="w-4 h-4 text-yellow-500" />;
    return <CheckCircle className="w-4 h-4 text-green-500" />;
  };

  if (loading) {
    return <div className="bg-white rounded-lg shadow p-6">Loading team overview...</div>;
  }

  if (teamStats.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Users className="w-5 h-5" />
        Team Overview
      </h2>

      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 text-sm font-medium text-gray-600">Member</th>
              <th className="text-center py-2 text-sm font-medium text-gray-600">Active</th>
              <th className="text-center py-2 text-sm font-medium text-gray-600">Completed</th>
              <th className="text-center py-2 text-sm font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {teamStats.map(({ member, activeProjects, completedProjects, lastUpdate }) => (
              <tr key={member.id} className="border-b last:border-0">
                <td className="py-3">
                  <div className="font-medium text-gray-900">{member.display_name}</div>
                  <div className="text-xs text-gray-500">{member.role}</div>
                </td>
                <td className="text-center py-3 text-sm">{activeProjects}</td>
                <td className="text-center py-3 text-sm">{completedProjects}</td>
                <td className="text-center py-3">
                  <div className="flex items-center justify-center gap-1">
                    {getStatusIcon(lastUpdate)}
                    {lastUpdate && (
                      <span className="text-xs text-gray-500">
                        {Math.floor((Date.now() - new Date(lastUpdate)) / (1000 * 60 * 60 * 24))}d
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
