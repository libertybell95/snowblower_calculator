# Snowblower Discord Bot

A Discord bot that provides intelligent snowblowing advice based on real-time weather conditions and forecasts. Get instant recommendations on when to snow blow and which direction to blow for optimal results.

## Features

🤖 **Discord Integration**
- Slash commands (`/snowblower`, `/snowblower-config`)
- Beautiful embedded responses with color-coded alerts
- Real-time weather data and 24-hour forecasts

❄️ **Smart Recommendations**
- 24-hour snow accumulation monitoring
- Wind speed safety analysis
- Optimal snow blowing direction based on wind
- Forecast alerts for upcoming snow events

🌐 **Easy Deployment**
- Docker containerized for easy deployment
- Works with Portainer
- No API keys required (uses free Open-Meteo API)

## Quick Start

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create "New Application"
3. Go to "Bot" tab → "Add Bot"
4. Copy the bot token
5. Go to "OAuth2" → "URL Generator"
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Embed Links`
6. Use generated URL to invite bot to your server

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required: DISCORD_TOKEN
# Optional: Customize LOCATION_NAME, LATITUDE, LONGITUDE, thresholds
```

### 3. Deploy with Docker

**Local Testing:**
```bash
docker compose up -d
docker compose logs -f
```

**Portainer Deployment:**
1. Upload `docker-compose.yml` as a Stack
2. Set environment variables (especially `DISCORD_TOKEN`)
3. Deploy

See [DISCORD_BOT_README.md](DISCORD_BOT_README.md) for detailed deployment instructions.

## Usage

**In Discord:**
- `/snowblower` - Get current conditions and snowblowing advice
- `/snowblower-config` - View bot configuration

**Example Response:**

```
🚨 TIME TO SNOW BLOW NOW!

📍 Horace, ND
46.7804°N, -96.89543°W

📊 Current Conditions
🌡️ 27.2°F
💨 14.7 mph from SE
📊 Good - light winds
❄️ 2.50" accumulated (24hr)

🔮 24-Hour Forecast
❄️ 0.53" expected
💨 Peak winds: 19.1 mph from NW
✅ Stays below 2.0" threshold

💡 Recommendation
✅ Snow: 2.50" (threshold: 2.0")
✅ Wind: 14.7 mph (safe)

📍 Blow Direction: NW
Wind flowing SE → NW
```

## Configuration

All settings via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | *Required* |
| `LOCATION_NAME` | Display name for location | `Horace, ND` |
| `LATITUDE` | Location latitude | `46.780404848922245` |
| `LONGITUDE` | Location longitude | `-96.89542777279159` |
| `ACCUMULATION_THRESHOLD` | Min snow depth (inches) to trigger | `2.0` |
| `MAX_WIND_SPEED` | Max safe wind speed (mph) | `25.0` |

## Project Structure

```
snowblower_calculator/
├── discord_bot.py           # Discord bot main application
├── snowblower_advisor.py    # Core weather logic
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container build instructions
├── docker-compose.yml      # Docker Compose configuration
├── .env.example           # Environment template
├── README.md              # This file
└── DISCORD_BOT_README.md  # Detailed deployment guide
```

## Development

**Local Testing (without Docker):**

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run bot
python discord_bot.py
```

**Standalone Script:**

The core weather logic (`snowblower_advisor.py`) can be run standalone:

```bash
python snowblower_advisor.py
```

## How It Works

### Snow Accumulation Detection
- Monitors past 24 hours of snowfall
- Compares against configurable threshold
- Provides remaining inches needed

### Wind Analysis
- Checks current wind speed for safety
- Wind >25 mph = recommend waiting
- Calculates optimal blow direction (downwind)

### Forecast Intelligence
- Predicts next 24 hours of snowfall
- Warns if threshold will be exceeded
- Suggests preemptive action if winds will worsen

### API
Uses [Open-Meteo API](https://open-meteo.com/) - free, no key required, worldwide coverage

## Logging

Container logs show:
- Bot startup and configuration
- Command invocations with user info
- Weather data retrieval
- Errors with stack traces

```bash
# View logs
docker compose logs -f

# Or in Portainer: Containers → snowblower-discord-bot → Logs
```

## Troubleshooting

**Bot not responding:**
- Check bot is online in Discord
- Verify `DISCORD_TOKEN` is correct
- Wait 1 hour for slash commands to sync globally

**Weather data errors:**
- Verify `LATITUDE`/`LONGITUDE` are valid
- Check container has internet access
- Review logs for API errors

**Container won't start:**
```bash
docker compose logs
# Look for missing environment variables
```

## License

MIT License - Free to use and modify!

## Credits

- Weather data: [Open-Meteo API](https://open-meteo.com/)
- Built with [discord.py](https://discordpy.readthedocs.io/)

