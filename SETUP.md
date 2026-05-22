# Quick Setup Guide — Team & Projects

## 1. Run Migrations

```bash
cd kastra-backend
python3 -m alembic upgrade head
```

This creates:
- Team invite fields on users table
- Projects, project_updates, project_photos tables

## 2. Configure Cloudinary

Sign up at [cloudinary.com](https://cloudinary.com) (free tier is fine to start).

Add to `kastra-backend/.env`:
```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

## 3. Start Services

```bash
# Terminal 1 - Backend
cd kastra-backend
uvicorn app.main:app --reload --port 8080

# Terminal 2 - Frontend
cd kastra-frontend
npm run dev
```

## 4. Test Team Management

1. Log in as admin (the first user who registered)
2. Go to `/team` in sidebar
3. Click "Invite Member"
4. Enter email: `test@example.com`, name: `Test User`, role: `Field Agent`
5. Check terminal for invite email (in dev mode, it logs instead of sending)
6. Copy the invite link from logs
7. Open in browser → set password → log in as field agent

## 5. Test Projects

1. Log in as admin/manager
2. Create a quotation, send to client
3. Have client accept it (or manually change status to "accepted")
4. Go to `/projects` → click "New Project"
5. Select the accepted quotation
6. Fill in title, description, assign to field agent, set target date
7. Project appears on pipeline board

## 6. Test Field Agent View

1. Log in as field agent
2. Go to `/projects` → see only assigned projects
3. Click project → post update: "Started work today"
4. Upload a photo from your computer
5. Log back in as admin → see the update and photo

## 7. Test Pipeline Board

1. As admin/manager, go to `/projects`
2. Drag a project card from "Not Started" to "In Progress"
3. Drag another to "Completed"
4. Notice color indicators (green = recent, yellow = 3-7 days, red = 7+ days)

## 8. Check Dashboard

1. Go to `/dashboard`
2. Scroll to bottom → see "Team Overview" widget
3. Shows each team member's active/completed projects
4. Status indicator shows days since last update

---

## Roles Explained

| Role | Can Do |
|---|---|
| **Admin** | Everything — invite users, manage team, all projects, all data |
| **Manager** | Create/edit projects, quotations, invoices, clients, reports |
| **Field Agent** | View assigned projects only, post updates, upload photos |
| **Viewer** | Read-only — dashboard, reports, no create/edit/delete |

---

## Troubleshooting

**"Cannot import name 'send_email'"**
- Fixed — uses `_send` internally

**"Cloudinary upload failed"**
- Check credentials in `.env`
- Verify file is an image

**"Field agent can't see project"**
- Make sure project is assigned to that user
- Check user role is `field_agent` and `is_active = true`

**"Invite link doesn't work"**
- Tokens expire after 48 hours
- Admin can delete user and re-invite

---

## What's Next?

All core features are complete. Optional enhancements:

1. **Notifications** — In-app bell with unread count
2. **Scheduler** — Auto-flag stalled projects (7+ days no update)
3. **WhatsApp Notifications** — Alert admin when field agent posts update
4. **Client Portal** — Let clients view project progress (no login)

See `IMPLEMENTATION.md` for full details.

---

**Status:** ✅ Ready to use  
**Production:** Run migrations, add Cloudinary keys, deploy
