import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Calendar, MessageSquare, Image, Send, Upload } from 'lucide-react';
import { getProject, postUpdate, uploadPhoto } from '../../api/projects';
import { listClients } from '../../api/clients';
import { listTeamMembers } from '../../api/team';

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [client, setClient] = useState(null);
  const [assignedUser, setAssignedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updateBody, setUpdateBody] = useState('');
  const [posting, setPosting] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadProject();
  }, [id]);

  const loadProject = async () => {
    try {
      const [projectRes, clientsRes, teamRes] = await Promise.all([
        getProject(id),
        listClients(),
        listTeamMembers().catch(() => ({ data: [] }))
      ]);
      
      setProject(projectRes.data);
      
      const clientMatch = clientsRes.data.find(c => c.id === projectRes.data.client_id);
      setClient(clientMatch);
      
      if (projectRes.data.assigned_to) {
        const userMatch = teamRes.data.find(m => m.id === projectRes.data.assigned_to);
        setAssignedUser(userMatch);
      }
    } catch (err) {
      console.error('Failed to load project:', err);
      navigate('/projects');
    } finally {
      setLoading(false);
    }
  };

  const handlePostUpdate = async (e) => {
    e.preventDefault();
    if (!updateBody.trim()) return;

    setPosting(true);
    try {
      await postUpdate(id, updateBody);
      setUpdateBody('');
      loadProject();
    } catch (err) {
      console.error('Failed to post update:', err);
    } finally {
      setPosting(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      await uploadPhoto(id, formData);
      loadProject();
    } catch (err) {
      console.error('Failed to upload photo:', err);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading project...</div>;
  }

  if (!project) {
    return <div className="p-6">Project not found</div>;
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <button
        onClick={() => navigate('/projects')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Pipeline
      </button>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">{project.title}</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-sm text-gray-500">Client</div>
            <div className="font-medium">{client?.name || 'Unknown'}</div>
          </div>
          
          {assignedUser && (
            <div>
              <div className="text-sm text-gray-500">Assigned To</div>
              <div className="font-medium flex items-center gap-2">
                <User className="w-4 h-4" />
                {assignedUser.display_name}
              </div>
            </div>
          )}
          
          {project.target_date && (
            <div>
              <div className="text-sm text-gray-500">Target Date</div>
              <div className="font-medium flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                {new Date(project.target_date).toLocaleDateString()}
              </div>
            </div>
          )}
        </div>

        {project.description && (
          <div className="mt-4">
            <div className="text-sm text-gray-500 mb-1">Description</div>
            <p className="text-gray-700">{project.description}</p>
          </div>
        )}

        <div className="mt-4">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            project.stage === 'completed' ? 'bg-green-100 text-green-800' :
            project.stage === 'in_progress' ? 'bg-blue-100 text-blue-800' :
            project.stage === 'on_hold' ? 'bg-yellow-100 text-yellow-800' :
            project.stage === 'invoiced' ? 'bg-purple-100 text-purple-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {project.stage.replace('_', ' ').toUpperCase()}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Progress Updates
          </h2>

          <form onSubmit={handlePostUpdate} className="mb-6">
            <textarea
              value={updateBody}
              onChange={(e) => setUpdateBody(e.target.value)}
              placeholder="Post a progress update..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md resize-none"
              rows={3}
            />
            <button
              type="submit"
              disabled={posting || !updateBody.trim()}
              className="mt-2 flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {posting ? 'Posting...' : 'Post Update'}
            </button>
          </form>

          <div className="space-y-4">
            {project.updates.length === 0 && (
              <p className="text-gray-500 text-sm">No updates yet</p>
            )}
            {project.updates.map(update => (
              <div key={update.id} className="border-l-4 border-green-500 pl-4 py-2">
                <p className="text-gray-700">{update.body}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(update.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Image className="w-5 h-5" />
            Photos
          </h2>

          <label className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 cursor-pointer mb-6 w-fit">
            <Upload className="w-4 h-4" />
            {uploading ? 'Uploading...' : 'Upload Photo'}
            <input
              type="file"
              accept="image/*"
              onChange={handlePhotoUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            {project.photos.length === 0 && (
              <p className="text-gray-500 text-sm col-span-2">No photos yet</p>
            )}
            {project.photos.map(photo => (
              <div key={photo.id} className="relative">
                <img
                  src={photo.cloudinary_url}
                  alt={photo.caption || 'Project photo'}
                  className="w-full h-40 object-cover rounded-lg"
                />
                {photo.caption && (
                  <p className="text-xs text-gray-600 mt-1">{photo.caption}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(photo.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
