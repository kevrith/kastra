import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Kanban, Plus, User, Calendar, Clock } from 'lucide-react';
import { listProjects, updateProject } from '../../api/projects';
import { listClients } from '../../api/clients';
import { listTeamMembers } from '../../api/team';

const STAGES = [
  { key: 'not_started', label: 'Not Started', color: 'bg-gray-100 text-gray-700' },
  { key: 'in_progress', label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  { key: 'on_hold', label: 'On Hold', color: 'bg-yellow-100 text-yellow-700' },
  { key: 'completed', label: 'Completed', color: 'bg-green-100 text-green-700' },
  { key: 'invoiced', label: 'Invoiced', color: 'bg-purple-100 text-purple-700' },
];

export default function ProjectPipeline() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState({});
  const [teamMembers, setTeamMembers] = useState({});
  const [loading, setLoading] = useState(true);
  const [draggedProject, setDraggedProject] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [projectsRes, clientsRes, teamRes] = await Promise.all([
        listProjects(),
        listClients(),
        listTeamMembers().catch(() => ({ data: [] }))
      ]);
      
      setProjects(projectsRes.data);
      
      const clientsMap = {};
      clientsRes.data.forEach(c => clientsMap[c.id] = c);
      setClients(clientsMap);
      
      const teamMap = {};
      teamRes.data.forEach(m => teamMap[m.id] = m);
      setTeamMembers(teamMap);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = (e, project) => {
    setDraggedProject(project);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, newStage) => {
    e.preventDefault();
    if (!draggedProject || draggedProject.stage === newStage) {
      setDraggedProject(null);
      return;
    }

    try {
      await updateProject(draggedProject.id, { stage: newStage });
      loadData();
    } catch (err) {
      alert('Failed to update project stage');
    } finally {
      setDraggedProject(null);
    }
  };

  const getProjectsByStage = (stage) => {
    return projects.filter(p => p.stage === stage);
  };

  const getDaysSinceUpdate = (lastUpdate) => {
    if (!lastUpdate) return null;
    const days = Math.floor((Date.now() - new Date(lastUpdate)) / (1000 * 60 * 60 * 24));
    return days;
  };

  const getStalenessColor = (days) => {
    if (days === null) return '';
    if (days >= 7) return 'border-l-4 border-red-500';
    if (days >= 3) return 'border-l-4 border-yellow-500';
    return 'border-l-4 border-green-500';
  };

  if (loading) {
    return <div className="p-6">Loading pipeline...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Kanban className="w-7 h-7" />
            Project Pipeline
          </h1>
          <p className="text-gray-600 mt-1">Drag cards to update project stage</p>
        </div>
        <button
          onClick={() => navigate('/quotations')}
          className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
        >
          <Plus className="w-5 h-5" />
          New Project
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {STAGES.map(stage => {
          const stageProjects = getProjectsByStage(stage.key);
          return (
            <div
              key={stage.key}
              className="bg-gray-50 rounded-lg p-4 min-h-[500px]"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, stage.key)}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">{stage.label}</h3>
                <span className={`text-xs px-2 py-1 rounded-full ${stage.color}`}>
                  {stageProjects.length}
                </span>
              </div>

              <div className="space-y-3">
                {stageProjects.map(project => {
                  const client = clients[project.client_id];
                  const assignedUser = teamMembers[project.assigned_to];
                  const daysSinceUpdate = getDaysSinceUpdate(project.last_update_at || project.updated_at);
                  
                  return (
                    <div
                      key={project.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, project)}
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className={`bg-white p-3 rounded-lg shadow-sm cursor-move hover:shadow-md transition-shadow ${getStalenessColor(daysSinceUpdate)}`}
                    >
                      <div className="font-medium text-sm text-gray-900 mb-1">
                        {project.title}
                      </div>
                      <div className="text-xs text-gray-500 mb-2">
                        {client?.name || 'Unknown Client'}
                      </div>
                      
                      {assignedUser && (
                        <div className="flex items-center gap-1 text-xs text-gray-600 mb-1">
                          <User className="w-3 h-3" />
                          {assignedUser.display_name}
                        </div>
                      )}
                      
                      {project.target_date && (
                        <div className="flex items-center gap-1 text-xs text-gray-600 mb-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(project.target_date).toLocaleDateString()}
                        </div>
                      )}
                      
                      {daysSinceUpdate !== null && (
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
                          <Clock className="w-3 h-3" />
                          {daysSinceUpdate === 0 ? 'Updated today' : `${daysSinceUpdate}d ago`}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
