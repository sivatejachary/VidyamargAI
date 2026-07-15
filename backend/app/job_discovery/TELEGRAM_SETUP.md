# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM JOB DISCOVERY — SETUP GUIDE
# ══════════════════════════════════════════════════════════════════════════════
#
# VidyaMarg AI can automatically discover jobs from Telegram channels including
# private channels that your account has joined.
#
# ── STEP 1: Get your Telegram API credentials ─────────────────────────────────
#
#   1. Go to https://my.telegram.org/apps
#   2. Log in with your phone number
#   3. Create a new application (any name, e.g. "VidyaMarg Bot")
#   4. Copy the api_id and api_hash values
#   5. Add them to your .env file:
#
#       TG_API_ID=12345678
#       TG_API_HASH=abcdef1234567890abcdef1234567890
#
# ── STEP 2: Authenticate (one-time only) ──────────────────────────────────────
#
#   cd backend
#   python -m app.agents.telegram_login
#
#   This will ask for your phone number and a code sent to your Telegram app.
#   The session is saved to: backend/app/agents/telegram_session.session
#   You will NOT need to do this again unless the session expires or you
#   log in from too many devices.
#
# ── STEP 3: Configure channels ────────────────────────────────────────────────
#
#   Edit: backend/app/job_discovery/telegram_channels.txt
#
#   Add one channel per line (without @):
#       JobsForTechies
#       TechJobsIndia
#       MyPrivateJobChannel
#
#   For private channels: join them in your Telegram app first, then add
#   the username here. Invite links (t.me/+xxxx) are also supported.
#
# ── STEP 4: Verify channels ───────────────────────────────────────────────────
#
#   cd backend
#
#   # List all configured channels:
#   python -m app.job_discovery.verify_telegram_channels --list
#
#   # Test a specific channel:
#   python -m app.job_discovery.verify_telegram_channels --channel JobsForTechies
#
#   # Run full verification (all channels):
#   python -m app.job_discovery.verify_telegram_channels
#
#   # Add a channel from CLI:
#   python -m app.job_discovery.verify_telegram_channels --add MyChannel
#
#   # Remove a channel:
#   python -m app.job_discovery.verify_telegram_channels --remove OldChannel
#
# ── STEP 5: API endpoints (Admin/Recruiter Portal) ────────────────────────────
#
#   GET  /api/v1/telegram/channels          → List all channels
#   POST /api/v1/telegram/channels          → Add channels
#   DELETE /api/v1/telegram/channels/{name} → Remove a channel
#   GET  /api/v1/telegram/status            → Session health + stats
#   POST /api/v1/telegram/channels/test?channel_name=X → Live test a channel
#   POST /api/v1/telegram/trigger           → Trigger immediate discovery
#
# ── ENVIRONMENT VARIABLES ─────────────────────────────────────────────────────
#
#   TG_API_ID          (required) Your Telegram app API ID
#   TG_API_HASH        (required) Your Telegram app API hash
#   TG_CHANNELS_FILE   (optional) Custom path to the channels .txt file
#                                 Default: backend/app/job_discovery/telegram_channels.txt
#
# ── HOW IT WORKS ──────────────────────────────────────────────────────────────
#
#   Discovery Run:
#     1. Scheduler triggers every 30 minutes
#     2. TelegramJobsConnector reads all channels from telegram_channels.txt
#     3. All channels are fetched CONCURRENTLY (batches of 10)
#     4. Each message goes through a multi-strategy job parser:
#        A. Structured field extraction (Title:, Company:, Location:, ...)
#        B. Emoji + keyword heuristic (🚀 🔥 💼 detect job posts)
#        C. NLP fallback (first-line company, URL detection)
#     5. Parsed jobs → Normalize → Validate → Deduplicate → Persist
#     6. Redis event published → Embedding Worker → Matching Worker
#     7. Matched candidates get notified in real-time via WebSocket
#
#   Parsing limits per channel per run:
#     Default: 100 messages (configurable via _MESSAGES_PER_CHANNEL)
#     Minimum message length: 60 characters to be considered a job post
#
# ── TROUBLESHOOTING ───────────────────────────────────────────────────────────
#
#   "Session not available"
#     → Run: python -m app.agents.telegram_login
#
#   "User is not authorized"
#     → Session expired. Re-run: python -m app.agents.telegram_login
#
#   "Could not access @ChannelName"
#     → Your Telegram account has not joined this channel.
#       Join it in the Telegram app, then retry.
#
#   "No job messages found"
#     → The channel may not use standard job posting format.
#       Check with: python -m app.job_discovery.verify_telegram_channels --raw --channel NAME
#
# ══════════════════════════════════════════════════════════════════════════════
