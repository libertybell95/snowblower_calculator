# Snowblower Discord Bot

A Discord bot that provides snowblowing advice based on weather conditions and forecasts. Deploy it as a Docker container in Portainer for 24/7 availability.

## Features

- **`/snowblower`** - Get current conditions and recommendations
- **`/snowblower-config`** - View bot configuration
- 24-hour snow accumulation monitoring
- 24-hour forecast analysis
- Wind safety recommendations
- Optimal snow blowing direction

## Quick Start

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" tab and click "Add Bot"
4. Enable these **Privileged Gateway Intents**:
   - Message Content Intent
5. Copy the bot token (keep it secret!)
6. Go to "OAuth2" > "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select permissions: `Send Messages`, `Embed Links`
9. Copy the generated URL and open it to invite bot to your server

### 2. Local Testing (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Discord token
notepad .env

# Run the bot
python discord_bot.py
```

### 3. Deploy to Portainer

#### Option A: Using Portainer Stacks

1. Open Portainer
2. Go to **Stacks** > **Add stack**
3. Name it: `snowblower-bot`
4. Upload `docker-compose.yml` or paste its contents
5. Add environment variables:
   ```
   DISCORD_TOKEN=your_actual_discord_token
   LATITUDE=46.780404848922245
   LONGITUDE=-96.89542777279159
   ACCUMULATION_THRESHOLD=2.0
   MAX_WIND_SPEED=25.0
   ```
6. Click **Deploy the stack**

#### Option B: Using Portainer Containers

1. Build the Docker image locally first:
   ```bash
   docker build -t snowblower-bot .
   ```

2. Save and transfer to your Portainer host:
   ```bash
   docker save snowblower-bot > snowblower-bot.tar
   ```

3. Load on Portainer host:
   ```bash
   docker load < snowblower-bot.tar
   ```

4. In Portainer:
   - Go to **Containers** > **Add container**
   - Name: `snowblower-discord-bot`
   - Image: `snowblower-bot:latest`
   - Add environment variables (same as above)
   - Restart policy: **Unless stopped**
   - Click **Deploy the container**

### 4. Using the Bot

In your Discord server, type:

- **`/snowblower`** - Get snowblowing advice
- **`/snowblower-config`** - View current settings

## Configuration

Configure via environment variables (in `.env` for local, or Portainer environment variables):

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | *Required* |
| `LATITUDE` | Your location latitude | `46.780404848922245` |
| `LONGITUDE` | Your location longitude | `-96.89542777279159` |
| `ACCUMULATION_THRESHOLD` | Minimum snow depth (inches) | `2.0` |
| `MAX_WIND_SPEED` | Maximum safe wind speed (mph) | `25.0` |

### Finding Your Coordinates

1. Open [Google Maps](https://maps.google.com)
2. Right-click your location
3. Click the coordinates to copy them
4. Format: `latitude, longitude`

## Bot Output

The bot provides color-coded recommendations:

- 🚨 **Red** - Time to snowblow now
- ⚠️ **Orange** - Wait for better wind conditions
- 🟡 **Yellow** - Forecast alert (may need to snowblow soon)
- ✅ **Green** - No action needed

### Example Output

```
🚨 TIME TO SNOW BLOW NOW!

📊 Current Conditions
Temperature: 27.2°F
Wind: 14.7 mph from SE
Wind Condition: Good - light winds
Snow (past 24hr): 3.50 inches

🔮 24-Hour Forecast
Expected Snowfall: 0.53 inches
Peak Wind Speed: 19.1 mph
Avg Wind Direction: NW
✓ Will stay below 2.0" threshold

💡 Recommendation
✓ Snow accumulation (3.50") exceeds threshold (2.0")
✓ Wind conditions are safe (14.7 mph)

📍 Blow snow toward the NW
   (Wind is blowing from SE to NW)
```

## Maintenance

### View Logs

**Portainer:**
1. Go to **Containers**
2. Click on `snowblower-discord-bot`
3. Click **Logs**

**Command line:**
```bash
docker logs snowblower-discord-bot
```

### Restart Bot

**Portainer:**
1. Go to **Containers**
2. Select `snowblower-discord-bot`
3. Click **Restart**

**Command line:**
```bash
docker restart snowblower-discord-bot
```

### Update Configuration

**Portainer:**
1. Go to **Containers** or **Stacks**
2. Select your container/stack
3. Click **Duplicate/Edit**
4. Update environment variables
5. Click **Deploy**

## Troubleshooting

### Bot not responding to slash commands

1. Make sure bot has proper permissions in Discord server
2. Wait 1 hour for Discord to sync commands globally (or restart bot)
3. Check bot is online in Discord
4. Verify `DISCORD_TOKEN` is correct

### "Import discord could not be resolved" error

This is expected during development if you haven't installed dependencies locally. The Docker container will have all dependencies.

To fix locally:
```bash
pip install -r requirements.txt
```

### Weather data not loading

- Check container has internet access
- Verify coordinates are correct (latitude/longitude)
- Check Portainer logs for API errors

### Container keeps restarting

```bash
# Check logs for errors
docker logs snowblower-discord-bot

# Common issues:
# - Missing DISCORD_TOKEN
# - Invalid DISCORD_TOKEN
# - Wrong latitude/longitude format
```

## Architecture

```
Discord Server
     ↓
  /snowblower command
     ↓
Discord Bot (Python)
     ↓
SnowblowerAdvisor class
     ↓
Open-Meteo API
     ↓
Weather data + forecast
     ↓
Formatted Discord Embed
     ↓
User sees advice
```

## Files

- `snowblower_advisor.py` - Core weather logic
- `discord_bot.py` - Discord bot wrapper
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build instructions
- `docker-compose.yml` - Portainer stack configuration
- `.env.example` - Environment variable template

## Security Notes

- **Never commit your `.env` file or Discord token to git**
- Add `.env` to `.gitignore`
- Rotate your Discord token if exposed
- Use Portainer's secrets management for production

## License

MIT License - Free to use and modify!
