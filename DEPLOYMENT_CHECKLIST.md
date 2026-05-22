# Deployment Checklist — Team & Projects

Use this checklist to deploy the new features to production.

---

## Pre-Deployment

- [ ] Read `IMPLEMENTATION.md` for full technical details
- [ ] Read `SETUP.md` for quick setup guide
- [ ] Read `MIGRATION.md` if you have existing users
- [ ] Backup production database
- [ ] Test on local environment first

---

## Local Testing

- [ ] Run migrations: `alembic upgrade head`
- [ ] Start backend: `uvicorn app.main:app --reload --port 8080`
- [ ] Start frontend: `npm run dev`
- [ ] Sign up for Cloudinary account (free tier)
- [ ] Add Cloudinary credentials to `.env`
- [ ] Test team invite flow
- [ ] Test project creation
- [ ] Test photo upload
- [ ] Test drag & drop on pipeline board
- [ ] Test field agent view (only assigned projects)
- [ ] Test dashboard team overview widget

---

## Cloudinary Setup

- [ ] Sign up at [cloudinary.com](https://cloudinary.com)
- [ ] Get credentials from dashboard
- [ ] Add to `kastra-backend/.env`:
  ```bash
  CLOUDINARY_CLOUD_NAME=your-cloud-name
  CLOUDINARY_API_KEY=your-api-key
  CLOUDINARY_API_SECRET=your-api-secret
  ```
- [ ] Test upload from project detail page
- [ ] Verify photo appears in Cloudinary dashboard

---

## Production Deployment

### Backend (Render)

- [ ] Push code to GitHub: `git push origin main`
- [ ] Go to Render dashboard
- [ ] Add environment variables:
  - `CLOUDINARY_CLOUD_NAME`
  - `CLOUDINARY_API_KEY`
  - `CLOUDINARY_API_SECRET`
- [ ] Wait for auto-deploy to complete
- [ ] Run migrations via Render shell:
  ```bash
  alembic upgrade head
  ```
- [ ] Check logs for errors

### Frontend (Vercel)

- [ ] Push code to GitHub: `git push origin main`
- [ ] Vercel auto-deploys
- [ ] Wait for build to complete
- [ ] Check deployment logs

---

## Post-Deployment Verification

- [ ] Visit production URL
- [ ] Log in as existing admin
- [ ] Check `/team` link appears in sidebar
- [ ] Go to `/team` → see existing users
- [ ] Invite a test user
- [ ] Check email (or SendGrid logs)
- [ ] Accept invite in new browser/incognito
- [ ] Log in as new user
- [ ] Create a project
- [ ] Assign to field agent
- [ ] Log in as field agent
- [ ] Post update
- [ ] Upload photo
- [ ] Verify photo appears
- [ ] Check dashboard team overview

---

## User Communication

- [ ] Send email to existing users about new features
- [ ] Update help documentation
- [ ] Create video tutorial (optional)
- [ ] Post announcement on social media (optional)

---

## Monitoring

### Week 1
- [ ] Check error logs daily
- [ ] Monitor Cloudinary usage
- [ ] Track user adoption (% who invite team members)
- [ ] Collect user feedback

### Week 2-4
- [ ] Check error logs weekly
- [ ] Monitor Cloudinary usage (upgrade if needed)
- [ ] Track project activity (updates per project)
- [ ] Identify stalled projects

---

## Rollback Plan (If Needed)

If something goes wrong:

1. [ ] Restore database backup
2. [ ] Revert code: `git revert HEAD && git push`
3. [ ] Downgrade migrations: `alembic downgrade -2`
4. [ ] Notify users of temporary rollback

---

## Success Metrics

Track these after launch:

- [ ] **Team adoption:** % of users who invite team members
- [ ] **Project creation:** # of projects created per week
- [ ] **Photo uploads:** # of photos uploaded per project
- [ ] **Update frequency:** Average updates per project per week
- [ ] **Staleness:** % of projects with no update in 7+ days
- [ ] **User satisfaction:** NPS score or feedback survey

---

## Pricing Update (Optional)

If you want to charge more for team features:

**Current:**
- Starter: KSh 1,500/month (1 user)
- Business: KSh 3,000/month (3 users)
- Premium: KSh 5,500/month (unlimited users)

**Suggested:**
- Starter: KSh 1,500/month (1 user, no team features)
- Business: KSh 3,500/month (5 users, team + projects)
- Premium: KSh 6,500/month (unlimited users, priority support)

---

## Support Resources

- **Technical:** `IMPLEMENTATION.md`
- **Setup:** `SETUP.md`
- **Migration:** `MIGRATION.md`
- **Summary:** `SUMMARY.md`
- **Main README:** `README.md`

---

## Next Steps (Optional Enhancements)

After successful deployment, consider:

1. **Notifications System**
   - In-app bell with unread count
   - Email alerts on project updates
   - WhatsApp notifications

2. **Scheduler Jobs**
   - Auto-flag stalled projects
   - Email digest of stalled projects
   - Auto-move to "invoiced" when invoice paid

3. **Client Portal**
   - Let clients view project progress
   - Photo gallery for clients
   - Approval workflow

4. **Advanced Features**
   - Time tracking per project
   - Budget vs actual cost
   - Project templates
   - Bulk operations

---

## Final Checks

- [ ] All tests passing locally
- [ ] Migrations run successfully
- [ ] Cloudinary credentials configured
- [ ] Backend deployed and running
- [ ] Frontend deployed and running
- [ ] Test user can invite and accept
- [ ] Test project creation and updates
- [ ] Test photo upload
- [ ] Dashboard shows team overview
- [ ] No errors in production logs

---

**Status:** Ready to deploy ✅  
**Estimated Time:** 30-60 minutes  
**Risk Level:** Low (migrations are additive)  
**Rollback:** Easy (backup + revert)

---

*Good luck with the deployment! 🚀*
