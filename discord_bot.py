#!/usr/bin/env python3
"""
Discord Snowblower Bot
----------------------
Discord bot that provides snowblowing advice via slash commands.
Uses the SnowblowerAdvisor class to fetch weather data and provide recommendations.
"""

import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from snowblower_advisor import SnowblowerAdvisor
from typing import Optional
import logging
from datetime import datetime

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


class SnowblowerBot(commands.Bot):
    """Discord bot for snowblowing advice."""
    
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix='/', intents=intents)
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info('Syncing slash commands with Discord...')
        await self.tree.sync()
        logger.info('Slash commands synced successfully')
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Bot connected as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')
        for guild in self.guilds:
            logger.info(f'  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})')
        logger.info('Bot is ready to receive commands')


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
