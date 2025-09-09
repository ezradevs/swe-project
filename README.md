<div class="rendered-markdown"><h1>Sydney Chess Club Admin Portal</h1>
<p>This is a modern, secure, and maintainable web application for managing the Sydney Chess Club (a hypothetical entity). The portal is designed for administrators to manage club members, tournaments, and analytics, with robust authentication and a clean, responsive UI.</p>
<h2>Features</h2>
<ul>
<li>Admin-only login (members do not log in)</li>
<li>Manage members and tournaments</li>
<li>Generate and manage fixtures (Swiss, Knockout, Round Robin)</li>
<li>Dashboard with analytics and reports</li>
<li>Admin management (add, edit, delete, change password)</li>
<li>Utility scripts for database initialization and viewing</li>
</ul>

<h2>Documentation</h2>
<p>For full documentation, see: <a href="https://ezradevs.notion.site/Software-Engineering-Project-Documentation-Ezra-Glover-Sanders-21e69a69f1df802e9a11cc93ccadc53e?source=copy_link">Ezra Glover-Sanders Software Engineering Project Documentation on Notion</a></p>

<h2>Security & Configuration</h2>
<ul>
<li><code>APP_ENV</code>: set to <code>production</code> for hardened behavior.</li>
<li><code>FLASK_SECRET_KEY</code> (required in production): secret for session signing.</li>
<li><code>ADMIN_DELETE_CODE</code> (required to delete other admins): one-time code admins must enter.</li>
<li><code>ADMIN_SIGNUP_SECRET</code> (optional): enables invite-only admin signup; otherwise signup is disabled.</li>
<li><code>FLASK_DEBUG</code>: set to <code>1</code> to enable debug (development only).</li>
</ul>

All POST routes are CSRF protected. Templates include a hidden <code>csrf_token</code> field.
