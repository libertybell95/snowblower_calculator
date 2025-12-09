#!/usr/bin/env python3
"""
Discord Snowblower Bot
----------------------
Discord bot that provides snowblowing advice via slash commands.
Uses the SnowblowerAdvisor class to fetch weather data and provide recommendations.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from snowblower_advisor import SnowblowerAdvisor
from typing import Optional
import logging
from datetime import datetime
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
LOCATION_NAME = os.getenv('LOCATION_NAME', 'Unknown Location')
LATITUDE = float(os.getenv('LATITUDE', '46.780404848922245'))
LONGITUDE = float(os.getenv('LONGITUDE', '-96.89542777279159'))
ACCUMULATION_THRESHOLD = float(os.getenv('ACCUMULATION_THRESHOLD', '2.0'))
MAX_WIND_SPEED = float(os.getenv('MAX_WIND_SPEED', '25.0'))

# Alert storage file
ALERTS_FILE = Path('alerts.json')


def load_alerts():
    """Load alert subscriptions from file."""
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading alerts: {e}")
            return {}
    return {}


def save_alerts(alerts):
    """Save alert subscriptions to file."""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving alerts: {e}")


class SnowblowerBot(commands.Bot):
    """Discord bot for snowblowing advice."""
    
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix='/', intents=intents)
        self.alerts = load_alerts()
        self.last_alert_state = {}  # Track when we've already alerted
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info('Syncing slash commands with Discord...')
        await self.tree.sync()
        logger.info('Slash commands synced successfully')
        # Start the alert checking task
        self.check_alerts.start()
        logger.info('Alert checking task started')
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')
        for guild in self.guilds:
            logger.info(f'  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})')
        logger.info('Bot is ready to receive commands')
    
    @tasks.loop(minutes=15)  # Check every 15 minutes
    async def check_alerts(self):
        """Background task to check conditions and send alerts."""
        try:
            logger.info('Checking alert conditions...')
            advice_data = get_advisor_data()
            
            # Check if conditions warrant an alert (threshold reached and wind safe)
            should_alert = advice_data['should_blow'] and advice_data['wind_safe']
            
            for alert_key, alert_info in list(self.alerts.items()):
                channel_id = alert_info['channel_id']
                user_id = alert_info['user_id']
                
                # Create unique key for this alert state
                state_key = f"{channel_id}_{user_id}"
                
                # Only alert if conditions are met and we haven't alerted for this state
                if should_alert and not self.last_alert_state.get(state_key, False):
                    try:
                        channel = self.get_channel(channel_id)
                        if channel:
                            user = await self.fetch_user(user_id)
                            embed = format_snowblower_advice(advice_data)
                            embed.title = "🚨 SNOWBLOWER ALERT!"
                            embed.description = f"{user.mention} - Threshold reached!\n\n" + embed.description
                            
                            await channel.send(content=user.mention, embed=embed)
                            logger.info(f'Sent alert to user {user_id} in channel {channel_id}')
                            
                            # Mark that we've alerted for this state
                            self.last_alert_state[state_key] = True
                        else:
                            logger.warning(f'Channel {channel_id} not found, removing alert')
                            del self.alerts[alert_key]
                            save_alerts(self.alerts)
                    except Exception as e:
                        logger.error(f'Error sending alert to {user_id}: {e}')
                
                # Reset alert state when conditions no longer met
                elif not should_alert and self.last_alert_state.get(state_key, False):
                    self.last_alert_state[state_key] = False
                    logger.info(f'Alert state reset for {state_key}')
                    
        except Exception as e:
            logger.error(f'Error in alert check task: {e}', exc_info=True)
    
    @check_alerts.before_loop
    async def before_check_alerts(self):
        """Wait for the bot to be ready before starting the alert loop."""
        await self.wait_until_ready()


# Create bot instance
bot = SnowblowerBot()


def format_snowblower_advice(advisor_data: dict) -> discord.Embed:
    """
    Format snowblower advisor data as a Discord embed.
    
    Args:
        advisor_data: Dictionary containing weather and recommendation data
        
    Returns:
        Discord embed with formatted advice
    """
    # Determine embed color based on recommendation
    if advisor_data['should_blow'] and advisor_data['wind_safe']:
        color = discord.Color.red()  # Need to snowblow NOW
        title = "🚨 TIME TO SNOW BLOW NOW!"
        thumbnail_emoji = "❄️"
    elif advisor_data['should_blow'] and not advisor_data['wind_safe']:
        color = discord.Color.orange()  # Wait for better conditions
        title = "⚠️ WAIT - CONDITIONS NOT IDEAL"
        thumbnail_emoji = "💨"
    elif advisor_data['forecast_will_exceed']:
        color = discord.Color.gold()  # Forecast warning
        title = "⚠️ FORECAST ALERT"
        thumbnail_emoji = "🔮"
    else:
        color = discord.Color.green()  # All clear
        title = "✅ NO NEED TO SNOW BLOW NOW"
        thumbnail_emoji = "☀️"
    
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    
    # Add location in description with better formatting
    embed.description = f"📍 **{LOCATION_NAME}**\n*{LATITUDE}°N, {LONGITUDE}°W*"
    
    # Current Conditions - more compact and cleaner
    current_conditions = (
        f"🌡️ **{advisor_data['temperature']}°F**\n"
        f"💨 **{advisor_data['wind_speed']} mph** from **{advisor_data['wind_from']}**\n"
        f"📊 {advisor_data['wind_condition']}\n"
        f"❄️ **{advisor_data['past_accumulation']:.2f}\"** accumulated (24hr)"
    )
    embed.add_field(name="📊 Current Conditions", value=current_conditions, inline=False)
    
    # Forecast - cleaner format
    forecast_icon = "⚠️" if advisor_data['forecast_will_exceed'] else "✅"
    forecast_text = (
        f"❄️ **{advisor_data['forecast_accumulation']:.2f}\"** expected\n"
        f"💨 Peak winds: **{advisor_data['peak_wind']:.1f} mph** from **{advisor_data['forecast_wind_from']}**\n"
    )
    
    if advisor_data['forecast_will_exceed']:
        if advisor_data['hours_until_threshold']:
            forecast_text += f"{forecast_icon} Threshold in **~{advisor_data['hours_until_threshold']}hrs**"
        else:
            forecast_text += f"{forecast_icon} Will exceed **{ACCUMULATION_THRESHOLD}\"** threshold"
    else:
        forecast_text += f"{forecast_icon} Stays below **{ACCUMULATION_THRESHOLD}\"** threshold"
    
    embed.add_field(name="🔮 24-Hour Forecast", value=forecast_text, inline=False)
    
    # Recommendation - cleaner and more actionable
    if advisor_data['should_blow'] and advisor_data['wind_safe']:
        recommendation = (
            f"✅ Snow: **{advisor_data['past_accumulation']:.2f}\"** (threshold: {ACCUMULATION_THRESHOLD}\")\n"
            f"✅ Wind: **{advisor_data['wind_speed']} mph** (safe)\n\n"
            f"### 📍 Blow Direction: **{advisor_data['blow_to'].upper()}**\n"
            f"*Wind flowing {advisor_data['wind_from']} → {advisor_data['blow_to']}*"
        )
        if advisor_data['forecast_will_exceed']:
            recommendation += f"\n\n⚠️ *+{advisor_data['forecast_accumulation']:.2f}\" expected - may need to blow again*"
    elif advisor_data['should_blow'] and not advisor_data['wind_safe']:
        recommendation = (
            f"✅ Snow: **{advisor_data['past_accumulation']:.2f}\"** (threshold: {ACCUMULATION_THRESHOLD}\")\n"
            f"❌ Wind: **{advisor_data['wind_speed']} mph** (max: {MAX_WIND_SPEED} mph)\n\n"
            f"💨 *{advisor_data['wind_condition']}*\n\n"
            f"**Wait for winds < {MAX_WIND_SPEED} mph**\n"
            f"*If urgent, blow toward **{advisor_data['blow_to']}** (downwind)*"
        )
    else:
        remaining = ACCUMULATION_THRESHOLD - advisor_data['past_accumulation']
        recommendation = f"Current: **{advisor_data['past_accumulation']:.2f}\"** | Threshold: **{ACCUMULATION_THRESHOLD}\"**\n"
        recommendation += f"Need **{remaining:.2f}\"** more to trigger"
        
        if advisor_data['forecast_will_exceed']:
            recommendation += f"\n\n### ⚠️ Forecast Alert\n"
            recommendation += f"**+{advisor_data['forecast_accumulation']:.2f}\"** expected in 24hrs"
            if advisor_data['hours_until_threshold']:
                recommendation += f"\n*Likely needed in ~{advisor_data['hours_until_threshold']} hours*"
            
            if not advisor_data['forecast_wind_safe']:
                recommendation += (
                    f"\n\n💨 **Warning:** Peak winds ({advisor_data['peak_wind']:.1f} mph) may be too strong\n"
                    f"*Consider snowblowing preemptively now*"
                )
            else:
                recommendation += (
                    f"\n\n✅ Forecast conditions favorable\n"
                    f"*Recommended direction: **{advisor_data['forecast_blow_to']}***"
                )
    
    embed.add_field(name="💡 Recommendation", value=recommendation, inline=False)
    
    # Footer with settings
    embed.set_footer(
        text=f"Threshold: {ACCUMULATION_THRESHOLD}\" | Max Wind: {MAX_WIND_SPEED} mph",
        icon_url="https://em-content.zobj.net/thumbs/160/twitter/348/snowflake_2744-fe0f.png"
    )
    
    return embed


def get_advisor_data() -> dict:
    """
    Get snowblower advice data from the SnowblowerAdvisor.
    
    Returns:
        Dictionary with all relevant data for Discord display
    """
    advisor = SnowblowerAdvisor(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        accumulation_threshold_inches=ACCUMULATION_THRESHOLD,
        max_wind_speed_mph=MAX_WIND_SPEED
    )
    
    # Get weather data
    data = advisor.get_weather_data()
    current = data.get('current', {})
    hourly = data.get('hourly', {})
    
    # Extract current data
    temp = current.get('temperature_2m', 'N/A')
    wind_speed = current.get('wind_speed_10m', 0)
    wind_direction = current.get('wind_direction_10m', 0)
    current_snowfall = current.get('snowfall', 0)
    
    # Calculate past accumulation
    from datetime import datetime as dt, timezone
    times = hourly.get('time', [])
    hourly_snowfall = hourly.get('snowfall', [])
    now = dt.now(timezone.utc)
    current_index = 0
    for i, time_str in enumerate(times):
        time_obj = dt.fromisoformat(time_str.replace('Z', '+00:00'))
        if time_obj.replace(tzinfo=timezone.utc) <= now:
            current_index = i
    
    past_24_start = max(0, current_index - 24)
    past_24_snow = hourly_snowfall[past_24_start:current_index + 1]
    
    should_blow, past_accumulation = advisor.should_snowblow(current_snowfall, past_24_snow)
    
    # Get wind analysis
    wind_from, blow_to = advisor.get_recommended_blow_direction(wind_direction)
    wind_safe, wind_condition = advisor.is_wind_safe_for_snowblowing(wind_speed)
    
    # Get forecast
    forecast = advisor.get_forecast_analysis(hourly)
    forecast_wind_from, forecast_blow_to = advisor.get_recommended_blow_direction(forecast['avg_wind_direction'])
    forecast_wind_safe, _ = advisor.is_wind_safe_for_snowblowing(forecast['peak_wind'])
    
    return {
        'temperature': temp,
        'wind_speed': wind_speed,
        'wind_from': wind_from,
        'blow_to': blow_to,
        'wind_safe': wind_safe,
        'wind_condition': wind_condition,
        'past_accumulation': past_accumulation,
        'should_blow': should_blow,
        'forecast_accumulation': forecast['forecast_accumulation'],
        'peak_wind': forecast['peak_wind'],
        'forecast_wind_from': forecast_wind_from,
        'forecast_blow_to': forecast_blow_to,
        'forecast_wind_safe': forecast_wind_safe,
        'forecast_will_exceed': forecast['will_exceed_threshold'],
        'hours_until_threshold': forecast['hours_until_threshold']
    }


@bot.tree.command(name="snowblower", description="Get snowblowing advice based on current and forecasted conditions")
async def snowblower(interaction: discord.Interaction):
    """Slash command to get snowblower advice."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    guild = interaction.guild.name if interaction.guild else "DM"
    logger.info(f'Command /snowblower invoked by {user} in {guild}')
    
    await interaction.response.defer(thinking=True)
    
    try:
        logger.info('Fetching weather data...')
        # Get advice data
        advice_data = get_advisor_data()
        logger.info(f'Weather data retrieved: {advice_data["past_accumulation"]:.2f}" accumulated, {advice_data["wind_speed"]} mph wind')
        
        # Create embed
        embed = format_snowblower_advice(advice_data)
        
        # Send response
        await interaction.followup.send(embed=embed)
        logger.info(f'Successfully sent snowblower advice to {user}')
        
    except Exception as e:
        logger.error(f'Error processing /snowblower command: {str(e)}', exc_info=True)
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to fetch weather data: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)
        logger.info(f'Sent error response to {user}')


@bot.tree.command(name="snowblower-config", description="Show current snowblower bot configuration")
async def snowblower_config(interaction: discord.Interaction):
    """Show bot configuration."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    guild = interaction.guild.name if interaction.guild else "DM"
    logger.info(f'Command /snowblower-config invoked by {user} in {guild}')
    
    embed = discord.Embed(
        title="⚙️ Snowblower Bot Configuration",
        color=discord.Color.blue()
    )
    
    config_text = (
        f"**Location:** {LOCATION_NAME}\n"
        f"**Coordinates:** {LATITUDE}°N, {LONGITUDE}°W\n"
        f"**Accumulation Threshold:** {ACCUMULATION_THRESHOLD} inches\n"
        f"**Max Wind Speed:** {MAX_WIND_SPEED} mph"
    )
    
    embed.add_field(name="Settings", value=config_text, inline=False)
    embed.set_footer(text="Configure via environment variables")
    
    await interaction.response.send_message(embed=embed)
    logger.info(f'Sent configuration info to {user}')


@bot.tree.command(name="alert-subscribe", description="Subscribe to snowblower alerts in this channel")
async def alert_subscribe(interaction: discord.Interaction):
    """Subscribe to alerts when snowblowing threshold is reached."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    guild = interaction.guild.name if interaction.guild else "DM"
    logger.info(f'Command /alert-subscribe invoked by {user} in {guild}')
    
    # Create unique key for this subscription
    alert_key = f"{interaction.channel_id}_{interaction.user.id}"
    
    # Check if already subscribed
    if alert_key in bot.alerts:
        embed = discord.Embed(
            title="ℹ️ Already Subscribed",
            description=f"You're already subscribed to alerts in this channel!\n\nYou'll be notified when:\n• Snow accumulation reaches **{ACCUMULATION_THRESHOLD}\"**\n• Wind conditions are safe (< **{MAX_WIND_SPEED} mph**)",
            color=discord.Color.blue()
        )
    else:
        # Add subscription
        bot.alerts[alert_key] = {
            'channel_id': interaction.channel_id,
            'user_id': interaction.user.id,
            'subscribed_at': datetime.now().isoformat()
        }
        save_alerts(bot.alerts)
        
        embed = discord.Embed(
            title="✅ Alert Subscription Activated",
            description=f"{interaction.user.mention} will be notified in this channel when:\n• Snow accumulation reaches **{ACCUMULATION_THRESHOLD}\"**\n• Wind conditions are safe (< **{MAX_WIND_SPEED} mph**)\n\nAlerts are checked every 15 minutes.",
            color=discord.Color.green()
        )
        logger.info(f'User {interaction.user.id} subscribed to alerts in channel {interaction.channel_id}')
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="alert-unsubscribe", description="Unsubscribe from snowblower alerts in this channel")
async def alert_unsubscribe(interaction: discord.Interaction):
    """Unsubscribe from alerts in this channel."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    guild = interaction.guild.name if interaction.guild else "DM"
    logger.info(f'Command /alert-unsubscribe invoked by {user} in {guild}')
    
    # Create unique key for this subscription
    alert_key = f"{interaction.channel_id}_{interaction.user.id}"
    
    # Check if subscribed
    if alert_key in bot.alerts:
        del bot.alerts[alert_key]
        save_alerts(bot.alerts)
        
        # Also clear any alert state
        state_key = f"{interaction.channel_id}_{interaction.user.id}"
        if state_key in bot.last_alert_state:
            del bot.last_alert_state[state_key]
        
        embed = discord.Embed(
            title="✅ Unsubscribed",
            description="You will no longer receive snowblower alerts in this channel.",
            color=discord.Color.green()
        )
        logger.info(f'User {interaction.user.id} unsubscribed from alerts in channel {interaction.channel_id}')
    else:
        embed = discord.Embed(
            title="ℹ️ Not Subscribed",
            description="You don't have an active alert subscription in this channel.",
            color=discord.Color.blue()
        )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="alert-status", description="Check your alert subscription status")
async def alert_status(interaction: discord.Interaction):
    """Check alert subscription status."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    guild = interaction.guild.name if interaction.guild else "DM"
    logger.info(f'Command /alert-status invoked by {user} in {guild}')
    
    # Find all subscriptions for this user
    user_alerts = {k: v for k, v in bot.alerts.items() if v['user_id'] == interaction.user.id}
    
    if not user_alerts:
        embed = discord.Embed(
            title="📋 Alert Status",
            description="You have no active alert subscriptions.\n\nUse `/alert-subscribe` to get notified when snowblowing conditions are met!",
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="📋 Your Alert Subscriptions",
            description=f"You have **{len(user_alerts)}** active subscription(s):",
            color=discord.Color.green()
        )
        
        for alert_key, alert_info in user_alerts.items():
            channel = bot.get_channel(alert_info['channel_id'])
            channel_name = channel.name if channel else f"Channel ID: {alert_info['channel_id']}"
            subscribed_at = datetime.fromisoformat(alert_info['subscribed_at']).strftime('%Y-%m-%d %H:%M')
            
            embed.add_field(
                name=f"#{channel_name}",
                value=f"Subscribed: {subscribed_at}",
                inline=False
            )
        
        embed.set_footer(text=f"Threshold: {ACCUMULATION_THRESHOLD}\" | Max Wind: {MAX_WIND_SPEED} mph")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


def main():
    """Run the Discord bot."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your Discord bot token.")
        return
    
    logger.info("="*60)
    logger.info("Starting Snowblower Discord Bot")
    logger.info("="*60)
    logger.info(f"Configuration:")
    logger.info(f"  Location: {LOCATION_NAME}")
    logger.info(f"  Coordinates: {LATITUDE}°N, {LONGITUDE}°W")
    logger.info(f"  Accumulation Threshold: {ACCUMULATION_THRESHOLD} inches")
    logger.info(f"  Max Wind Speed: {MAX_WIND_SPEED} mph")
    logger.info("="*60)
    logger.info("Connecting to Discord...")
    
    try:
        bot.run(DISCORD_TOKEN, log_handler=None)  # Use our custom logging
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
