import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Calendar, MessageSquare, Image, Send, Upload, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { getProject, postUpdate, uploadPhoto, getProjectFinancials } from '../../api/projects';
import { getExpenses, createExpense } from '../../api/expenses';
import { listClients } from '../../api/clients';
import { listTeamMembers } from '../../api/team';
import Toast from '../../components/ui/Toast';
import Modal from '../../components/ui/Modal';
import { ksh } from '../../utils/formatters';

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
  const [toast, setToast] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [expenseForm, setExpenseForm] = useState({
    category: 'materials',
    description: '',
    vendor: '',
    amount: '',
    date: new Date().toISOString().split('T')[0]
  });
  const [savingExpense, setSavingExpense] = useState(false);

  useEffect(() => {
    loadProject();
    loadFinancials();
    loadExpenses();
  }, [id]);

  const loadProject = async () => {
    try {
      const [projectRes, clientsRes, teamRes] = await Promise.all([
        getProject(id),
        listClients(),
        listTeamMembers().catch(() => ({ data: [] }))
      ]);
      
      setProject(projectRes.data);
      
      // Handle clients response - backend returns { data: [...] }
      const clientsList = Array.isArray(clientsRes.data) ? clientsRes.data : (clientsRes.data?.data || []);
      const clientMatch = clientsList.find(c => c.id === projectRes.data.client_id);
      setClient(clientMatch);
      
      if (projectRes.data.assigned_to) {
        // Handle team response - backend returns array or { data: [...] }
        const teamList = Array.isArray(teamRes.data) ? teamRes.data : (teamRes.data?.data || []);
        const userMatch = teamList.find(m => m.id === projectRes.data.assigned_to);
        setAssignedUser(userMatch);
      }
    } catch (err) {
      console.error('Failed to load project:', err);
      setToast({ message: 'Failed to load project. Please try again.', type: 'error' });
      setTimeout(() => navigate('/projects'), 2000);
    } finally {
      setLoading(false);
    }
  };

  const loadFinancials = async () => {
    try {
      const { data } = await getProjectFinancials(id);
      setFinancials(data);
    } catch (err) {
      console.error('Failed to load financials:', err);
    }
  };

  const loadExpenses = async () => {
    try {
      const { data } = await getExpenses({ project_id: id, limit: 100 });
      setExpenses(data.data || []);
    } catch (err) {
      console.error('Failed to load expenses:', err);
    }
  };

  const handleSaveExpense = async () => {
    if (!expenseForm.description || !expenseForm.amount) {
      setToast({ message: 'Please fill in all required fields', type: 'error' });
      return;
    }

    setSavingExpense(true);
    try {
      await createExpense({
        ...expenseForm,
        amount: parseFloat(expenseForm.amount),
        project_id: id
      });
      setShowExpenseModal(false);
      setExpenseForm({
        category: 'materials',
        description: '',
        vendor: '',
        amount: '',
        date: new Date().toISOString().split('T')[0]
      });
      loadFinancials();
      loadExpenses();
      setToast({ message: 'Expense added successfully', type: 'success' });
    } catch (err) {
      console.error('Failed to save expense:', err);
      setToast({ message: 'Failed to save expense', type: 'error' });
    } finally {
      setSavingExpense(false);
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
      setToast({ message: 'Failed to post update. Please try again.', type: 'error' });
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
      setToast({ message: 'Failed to upload photo. Please try again.', type: 'error' });
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
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      
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

      {/* Financials Card */}
      {financials && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Project Financials
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-500">Revenue</div>
              <div className="text-xl font-bold text-gray-900">{ksh(financials.revenue)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Expenses</div>
              <div className="text-xl font-bold text-red-600">{ksh(financials.expenses)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Profit</div>
              <div className={`text-xl font-bold flex items-center gap-1 ${
                financials.profit >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {financials.profit >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                {ksh(financials.profit)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Margin</div>
              <div className={`text-xl font-bold ${
                financials.margin >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {financials.margin}%
              </div>
            </div>
          </div>

          {/* Expenses List */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">Project Expenses</h3>
              <button
                onClick={() => setShowExpenseModal(true)}
                className="text-sm text-green-600 hover:text-green-700 font-medium"
              >
                + Add Expense
              </button>
            </div>
            
            {expenses.length === 0 ? (
              <p className="text-sm text-gray-500">No expenses recorded yet</p>
            ) : (
              <div className="space-y-2">
                {expenses.map(exp => (
                  <div key={exp.id} className="flex items-center justify-between py-2 border-b border-gray-100">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{exp.description}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(exp.date).toLocaleDateString()} · {exp.category}
                        {exp.vendor && ` · ${exp.vendor}`}
                      </div>
                    </div>
                    <div className="text-sm font-semibold text-gray-900">{ksh(exp.amount)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

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

      {/* Add Expense Modal */}
      <Modal
        open={showExpenseModal}
        onClose={() => setShowExpenseModal(false)}
        title="Add Project Expense"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="label">Category</label>
            <select
              className="input"
              value={expenseForm.category}
              onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
            >
              <option value="materials">Materials</option>
              <option value="labor">Labor</option>
              <option value="transport">Transport</option>
              <option value="equipment">Equipment</option>
              <option value="supplies">Supplies</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="label">Description *</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Cement and sand"
              value={expenseForm.description}
              onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
            />
          </div>

          <div>
            <label className="label">Vendor</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. ABC Hardware"
              value={expenseForm.vendor}
              onChange={(e) => setExpenseForm({ ...expenseForm, vendor: e.target.value })}
            />
          </div>

          <div>
            <label className="label">Amount (KSh) *</label>
            <input
              type="number"
              className="input"
              placeholder="0.00"
              value={expenseForm.amount}
              onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
            />
          </div>

          <div>
            <label className="label">Date</label>
            <input
              type="date"
              className="input"
              value={expenseForm.date}
              onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setShowExpenseModal(false)}>Cancel</button>
          <button className="btn-primary" onClick={handleSaveExpense} disabled={savingExpense}>
            {savingExpense ? 'Saving...' : 'Save Expense'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
