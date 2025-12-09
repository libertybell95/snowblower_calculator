#!/usr/bin/env python3
"""
Snowblower Advisor
------------------
Helps you decide when to snow blow and which direction to blow based on:
- Snow accumulation threshold
- Wind direction (to avoid blowing snow back onto driveway)
"""

import requests
import sys
from datetime import datetime as dt, timezone
from typing import Dict, Tuple, Optional


class SnowblowerAdvisor:
    """Advises on snowblowing decisions based on weather conditions."""
    
    def __init__(self, latitude: float, longitude: float, 
                 accumulation_threshold_inches: float = 2.0,
                 max_wind_speed_mph: float = 25.0):
        """
        Initialize the advisor.
        
        Args:
            latitude: Your location's latitude
            longitude: Your location's longitude
            accumulation_threshold_inches: Minimum snow depth to trigger snowblowing
            max_wind_speed_mph: Maximum safe wind speed for snowblowing
        """
        self.latitude = latitude
        self.longitude = longitude
        self.accumulation_threshold = accumulation_threshold_inches
        self.max_wind_speed = max_wind_speed_mph
        
    def get_weather_data(self) -> Dict:
        """
        Fetch current weather data from Open-Meteo API (free, no API key needed).
        
        Returns:
            Dictionary with weather data
        """
        # Using Open-Meteo API - free and no API key required
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", 
                       "snowfall"],
            "hourly": ["snowfall", "wind_speed_10m", "wind_direction_10m", "temperature_2m"],
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
            "forecast_days": 3,
            "past_days": 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            sys.exit(1)
    
    def get_direction_from_degrees(self, degrees: float) -> str:
        """
        Convert wind direction in degrees to cardinal direction.
        
        Args:
            degrees: Wind direction in degrees (0-360)
            
        Returns:
            Cardinal direction (N, NE, E, SE, S, SW, W, NW)
        """
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = int((degrees + 22.5) / 45) % 8
        return directions[index]
    
    def get_recommended_blow_direction(self, wind_direction_degrees: float) -> Tuple[str, str]:
        """
        Determine the best direction to blow snow based on wind.
        Snow should be blown downwind to avoid it blowing back.
        
        Args:
            wind_direction_degrees: Direction wind is coming FROM (meteorological convention)
            
        Returns:
            Tuple of (wind_from_direction, recommended_blow_direction)
        """
        wind_from = self.get_direction_from_degrees(wind_direction_degrees)
        
        # Wind blows FROM the reported direction TO the opposite direction
        # We want to blow snow WITH the wind (downwind)
        blow_to_degrees = (wind_direction_degrees + 180) % 360
        blow_to = self.get_direction_from_degrees(blow_to_degrees)
        
        return wind_from, blow_to
    
    def should_snowblow(self, current_snowfall: float, hourly_snowfall: list) -> Tuple[bool, float]:
        """
        Determine if snowblowing is needed based on accumulation.
        
        Args:
            current_snowfall: Current snowfall rate
            hourly_snowfall: List of hourly snowfall amounts
            
        Returns:
            Tuple of (should_blow, total_accumulation)
        """
        # Sum up recent snowfall (last 24 hours)
        total_accumulation = sum(s for s in hourly_snowfall if s is not None)
        
        should_blow = total_accumulation >= self.accumulation_threshold
        return should_blow, total_accumulation
    
    def is_wind_safe_for_snowblowing(self, wind_speed: float) -> Tuple[bool, str]:
        """
        Determine if wind conditions are safe for snowblowing.
        
        Args:
            wind_speed: Current wind speed in mph
            
        Returns:
            Tuple of (is_safe, condition_description)
        """
        if wind_speed <= 10:
            return True, "Excellent - calm conditions"
        elif wind_speed <= 15:
            return True, "Good - light winds"
        elif wind_speed <= self.max_wind_speed:
            return True, "Fair - moderate winds, exercise caution"
        elif wind_speed <= 35:
            return False, "Too windy - snow will blow back, wait for calmer conditions"
        else:
            return False, "Dangerous - high winds, do not snowblow"
    
    def get_forecast_analysis(self, hourly_data: Dict) -> Dict:
        """
        Analyze the next 24 hours forecast for snowfall.
        
        Args:
            hourly_data: Hourly forecast data from API
            
        Returns:
            Dictionary with forecast analysis
        """
        times = hourly_data.get('time', [])
        snowfall = hourly_data.get('snowfall', [])
        wind_speed = hourly_data.get('wind_speed_10m', [])
        wind_direction = hourly_data.get('wind_direction_10m', [])
        
        # Find current time index
        now = dt.now(timezone.utc)
        current_index = 0
        for i, time_str in enumerate(times):
            time_obj = dt.fromisoformat(time_str.replace('Z', '+00:00'))
            if time_obj.replace(tzinfo=timezone.utc) <= now:
                current_index = i
            else:
                break
        
        # Get next 24 hours (current_index to current_index + 24)
        next_24_hours_snow = snowfall[current_index:current_index + 24]
        next_24_hours_wind = wind_speed[current_index:current_index + 24]
        next_24_hours_wind_dir = wind_direction[current_index:current_index + 24]
        
        # Calculate forecast accumulation
        forecast_accumulation = sum(s for s in next_24_hours_snow if s is not None)
        
        # Find peak wind and average wind direction
        peak_wind = max((w for w in next_24_hours_wind if w is not None), default=0)
        avg_wind_dir = sum(w for w in next_24_hours_wind_dir if w is not None) / len([w for w in next_24_hours_wind_dir if w is not None]) if next_24_hours_wind_dir else 0
        
        # Find when accumulation will exceed threshold (if at all)
        cumulative = 0
        hours_until_threshold = None
        for i, snow in enumerate(next_24_hours_snow):
            if snow is not None:
                cumulative += snow
                if cumulative >= self.accumulation_threshold and hours_until_threshold is None:
                    hours_until_threshold = i
        
        return {
            'forecast_accumulation': forecast_accumulation,
            'peak_wind': peak_wind,
            'avg_wind_direction': avg_wind_dir,
            'hours_until_threshold': hours_until_threshold,
            'will_exceed_threshold': forecast_accumulation >= self.accumulation_threshold
        }
    
    def get_advice(self) -> None:
        """Get and display snowblowing advice."""
        print("=" * 60)
        print("SNOWBLOWER ADVISOR")
        print("=" * 60)
        print(f"Location: {self.latitude}°N, {self.longitude}°W")
        print(f"Accumulation Threshold: {self.accumulation_threshold} inches")
        print(f"Time: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        # Get weather data
        data = self.get_weather_data()
        
        current = data.get('current', {})
        hourly = data.get('hourly', {})
        
        # Extract relevant data
        temp = current.get('temperature_2m', 'N/A')
        wind_speed = current.get('wind_speed_10m', 0)
        wind_direction = current.get('wind_direction_10m', 0)
        current_snowfall = current.get('snowfall', 0)
        hourly_snowfall = hourly.get('snowfall', [])
        
        # Calculate past 24hr accumulation (historical data)
        times = hourly.get('time', [])
        now = dt.now(timezone.utc)
        current_index = 0
        for i, time_str in enumerate(times):
            time_obj = dt.fromisoformat(time_str.replace('Z', '+00:00'))
            if time_obj.replace(tzinfo=timezone.utc) <= now:
                current_index = i
        
        # Get last 24 hours for historical accumulation
        past_24_start = max(0, current_index - 24)
        past_24_snow = hourly_snowfall[past_24_start:current_index + 1]
        
        # Determine if snowblowing is needed based on past accumulation
        should_blow, total_accumulation = self.should_snowblow(
            current_snowfall, past_24_snow
        )
        
        # Get forecast for next 24 hours
        forecast = self.get_forecast_analysis(hourly)
        
        # Get wind direction advice
        wind_from, blow_to = self.get_recommended_blow_direction(wind_direction)
        
        # Check wind conditions
        wind_safe, wind_condition = self.is_wind_safe_for_snowblowing(wind_speed)
        
        # Display weather conditions
        print("CURRENT CONDITIONS:")
        print(f"Temperature: {temp}°F")
        print(f"Wind: {wind_speed} mph from {wind_from} ({wind_direction}°)")
        print(f"Wind Condition: {wind_condition}")
        print(f"Snow Accumulation (past 24hr): {total_accumulation:.2f} inches")
        print("-" * 60)
        
        # Display forecast
        print("24-HOUR FORECAST:")
        forecast_wind_from, forecast_blow_to = self.get_recommended_blow_direction(forecast['avg_wind_direction'])
        print(f"Expected Snowfall: {forecast['forecast_accumulation']:.2f} inches")
        print(f"Peak Wind Speed: {forecast['peak_wind']:.1f} mph")
        print(f"Avg Wind Direction: {forecast_wind_from}")
        
        if forecast['will_exceed_threshold']:
            if forecast['hours_until_threshold'] is not None:
                print(f"⚠️  Will exceed threshold in ~{forecast['hours_until_threshold']} hours")
            else:
                print(f"⚠️  Will exceed {self.accumulation_threshold}\" threshold")
        else:
            print(f"✓ Will stay below {self.accumulation_threshold}\" threshold")
        print("-" * 60)
        
        # Display recommendation
        if should_blow and wind_safe:
            print("🚨 RECOMMENDATION: TIME TO SNOW BLOW NOW! 🚨")
            print(f"\n✓ Snow accumulation ({total_accumulation:.2f}\") exceeds threshold ({self.accumulation_threshold}\")")
            print(f"✓ Wind conditions are safe ({wind_speed} mph)")
            print(f"\n📍 BLOW DIRECTION: Blow snow toward the {blow_to}")
            print(f"   (Wind is blowing from {wind_from} to {blow_to})")
            print(f"   This will help prevent snow from blowing back onto your driveway.")
            
            # Add forecast context
            if forecast['will_exceed_threshold']:
                print(f"\n⚠️  Note: Additional {forecast['forecast_accumulation']:.2f}\" expected in next 24hrs")
                print(f"   You may need to snow blow again soon.")
        elif should_blow and not wind_safe:
            print("⚠️  WAIT - CONDITIONS NOT IDEAL")
            print(f"\n✓ Snow accumulation ({total_accumulation:.2f}\") exceeds threshold ({self.accumulation_threshold}\")")
            print(f"✗ Wind too strong: {wind_speed} mph (max recommended: {self.max_wind_speed} mph)")
            print(f"\n💨 {wind_condition}")
            print(f"\nSuggestion: Wait for winds to calm below {self.max_wind_speed} mph.")
            print(f"If you must snowblow now, blow toward the {blow_to} (downwind).")
        else:
            print("✓ NO NEED TO SNOW BLOW NOW")
            print(f"\n  Snow accumulation ({total_accumulation:.2f}\") is below threshold ({self.accumulation_threshold}\")")
            remaining = self.accumulation_threshold - total_accumulation
            print(f"  You need {remaining:.2f} more inches before snowblowing is recommended.")
            if not wind_safe:
                print(f"\n  Additionally, current winds ({wind_speed} mph) are too strong for safe snowblowing.")
            
            # Add forecast warning
            if forecast['will_exceed_threshold']:
                print(f"\n⚠️  FORECAST ALERT: Expected to exceed threshold in next 24 hours")
                print(f"   Forecasted accumulation: {forecast['forecast_accumulation']:.2f}\"")
                if forecast['hours_until_threshold'] is not None:
                    print(f"   Will likely need snowblowing in ~{forecast['hours_until_threshold']} hours")
                    
                    # Check forecast wind conditions
                    forecast_wind_safe, _ = self.is_wind_safe_for_snowblowing(forecast['peak_wind'])
                    if not forecast_wind_safe:
                        print(f"   ⚠️  Peak winds ({forecast['peak_wind']:.1f} mph) may be too strong later")
                        print(f"   Consider snowblowing preemptively if current conditions allow")
                    else:
                        print(f"   Forecast wind conditions look favorable (peak: {forecast['peak_wind']:.1f} mph)")
                        print(f"   Recommended direction: toward the {forecast_blow_to}")
        
        print("=" * 60)


def main():
    """Main entry point."""
    # Configuration - UPDATE THESE VALUES FOR YOUR LOCATION
    LATITUDE = 46.780404848922245    # Horace, ND
    LONGITUDE = -96.89542777279159
    ACCUMULATION_THRESHOLD = 2.0  # inches
    MAX_WIND_SPEED = 25.0  # mph - above this, snowblowing becomes difficult/unsafe
    
    print("\nFetching weather data...")
    advisor = SnowblowerAdvisor(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        accumulation_threshold_inches=ACCUMULATION_THRESHOLD,
        max_wind_speed_mph=MAX_WIND_SPEED
    )
    
    advisor.get_advice()


if __name__ == "__main__":
    main()
