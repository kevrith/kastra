# Migration Guide — Existing Kastra Users

If you already have Kastra running in production with existing users and data, follow this guide to safely add the new team and project features.

---

## Pre-Migration Checklist

- [ ] Backup your production database
- [ ] Test migrations on a staging environment first
- [ ] Notify users of planned maintenance window (5-10 minutes)
- [ ] Have rollback plan ready

---

## Step 1: Backup Database

```bash
# On Render or your hosting platform
pg_dump $DATABASE_URL > kastra_backup_$(date +%Y%m%d).sql
```

Or use Render's built-in backup feature.

---

## Step 2: Run Migrations

```bash
cd kastra-backend
alembic upgrade head
```

This will apply:
1. `w9x0y1z2a3b4` — Adds invite fields to users table
2. `x0y1z2a3b4c5` — Creates projects, project_updates, project_photos tables

**What happens to existing users:**
- All existing users keep their current `role` (admin or manager)
- New fields (`invite_token`, `invited_by`, etc.) are set to NULL
- No data is lost or modified
- Users can continue logging in normally

---

## Step 3: Update Environment Variables

Add to your production `.env`:

```bash
# Cloudinary (photo storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

Get these from [cloudinary.com](https://cloudinary.com) (free tier is fine).

---

## Step 4: Deploy Backend

```bash
git add .
git commit -m "Add team management and project pipeline"
git push origin main
```

Render will auto-deploy. Wait for build to complete.

---

## Step 5: Deploy Frontend

```bash
cd kastra-frontend
npm run build
# Deploy to Vercel or your hosting platform
```

---

## Step 6: Verify Deployment

1. Log in as an existing admin user
2. Check that `/team` link appears in sidebar
3. Go to `/team` → should see existing users listed
4. Go to `/projects` → should see empty pipeline board
5. Try inviting a new user → verify email is sent (or logged in dev)

---

## Step 7: Upgrade Existing Users

**Option A: Automatic (Recommended)**
- All existing users keep their current roles
- First user who registered is already admin
- Other users are managers by default
- Admin can change roles via `/team` page

**Option B: Manual SQL (if needed)**

If you need to promote specific users to admin:

```sql
UPDATE users 
SET role = 'admin' 
WHERE email IN ('owner@company.com', 'manager@company.com');
```

---

## Step 8: Communicate Changes to Users

Send an email to all users:

```
Subject: New Features — Team Management & Project Tracking

Hi [User],

We've added powerful new features to Kastra:

1. Team Management
   - Invite team members with different roles
   - Assign projects to field agents
   - Track who's working on what

2. Project Pipeline
   - Visual Kanban board for all projects
   - Drag & drop to update status
   - Post updates and upload photos from mobile

3. Enhanced Dashboard
   - See team activity at a glance
   - Track project progress in real time

What you need to do:
- Nothing! Your account works exactly as before
- Explore the new "Team" and "Projects" links in the sidebar
- Invite your team members to collaborate

Questions? Reply to this email.

Best,
Kastra Team
```

---

## Rollback Plan (If Needed)

If something goes wrong:

### 1. Restore Database Backup

```bash
psql $DATABASE_URL < kastra_backup_YYYYMMDD.sql
```

### 2. Revert Code

```bash
git revert HEAD
git push origin main
```

### 3. Downgrade Migrations

```bash
alembic downgrade -1  # Undo last migration
alembic downgrade -1  # Undo second-to-last migration
```

---

## Common Issues

### "Migration failed: column already exists"

**Cause:** Migration was partially applied  
**Fix:**
```bash
alembic stamp head  # Mark as applied
# Or manually check which columns exist and adjust migration
```

### "Users can't log in after migration"

**Cause:** Token version mismatch  
**Fix:**
```sql
UPDATE users SET token_version = 0 WHERE token_version IS NULL;
```

### "Cloudinary upload fails"

**Cause:** Missing or incorrect credentials  
**Fix:**
- Verify `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` in `.env`
- Check Cloudinary dashboard for correct values
- Restart backend after adding credentials

### "Field agent can't see projects"

**Cause:** No projects assigned to them  
**Fix:**
- Admin/manager must create project and assign to field agent
- Verify user role is `field_agent` (not `viewer`)

---

## Data Migration (Optional)

If you want to convert existing quotations to projects:

```sql
-- Create projects from all accepted quotations
INSERT INTO projects (id, organization_id, quotation_id, client_id, stage, title, created_at, updated_at)
SELECT 
  gen_random_uuid(),
  q.organization_id,
  q.id,
  q.client_id,
  'completed',  -- Mark as completed since they're old
  CONCAT('Project for ', c.name),
  q.created_at,
  NOW()
FROM quotations q
JOIN clients c ON c.id = q.client_id
WHERE q.status = 'accepted'
  AND q.converted_to_invoice = true
  AND NOT EXISTS (SELECT 1 FROM projects p WHERE p.quotation_id = q.id);
```

This is optional — new projects will be created going forward.

---

## Testing Checklist

After migration, test these flows:

- [ ] Existing admin can log in
- [ ] Existing manager can log in
- [ ] Admin can access `/team` page
- [ ] Admin can invite new user
- [ ] Invited user receives email (or see log in dev)
- [ ] Invited user can accept invite and set password
- [ ] New user can log in
- [ ] Admin can create project from accepted quotation
- [ ] Project appears on pipeline board
- [ ] Field agent can post update
- [ ] Field agent can upload photo
- [ ] Photo appears in project detail
- [ ] Dashboard shows team overview widget

---

## Performance Impact

**Database:**
- 3 new tables (projects, project_updates, project_photos)
- 4 new columns on users table
- Minimal impact — all tables have proper indexes

**Storage:**
- Photos stored on Cloudinary (not in database)
- Database size increase: negligible

**API:**
- 8 new endpoints (team + projects)
- No impact on existing endpoints
- All queries scoped to `organization_id` (same as before)

---

## Monitoring

After migration, monitor:

1. **Error logs** — Check for any new errors in Sentry/logs
2. **Database size** — Should not increase significantly
3. **Cloudinary usage** — Check dashboard for storage/bandwidth
4. **User feedback** — Ask users if they encounter issues

---

## Support

If you encounter issues:

1. Check `IMPLEMENTATION.md` for technical details
2. Check `SETUP.md` for configuration steps
3. Review error logs in Render/Vercel dashboard
4. Test on local environment first

---

**Migration Time:** 5-10 minutes  
**Downtime:** None (if using Render's zero-downtime deploys)  
**Risk Level:** Low (migrations are additive, no data deletion)  
**Rollback:** Easy (restore backup + revert code)

---

*Safe migrations! 🚀*
