"use client";

import { DayWeather } from "@/lib/api";

interface WeatherBadgeProps {
  weather: DayWeather;
  compact?: boolean;
}

const WEATHER_ICONS: Record<string, string> = {
  Clear: "☀️",
  Clouds: "⛅",
  Rain: "🌧️",
  Drizzle: "🌦️",
  Thunderstorm: "⛈️",
  Snow: "❄️",
  Mist: "🌫️",
  Fog: "🌫️",
  Haze: "🌫️",
};

const SEVERITY_STYLES: Record<string, string> = {
  great: "border-weather-great/30 bg-weather-great/10 text-weather-great",
  okay: "border-weather-okay/30 bg-weather-okay/10 text-weather-okay",
  indoor: "border-weather-indoor/30 bg-weather-indoor/10 text-weather-indoor",
};

export default function WeatherBadge({ weather, compact = false }: WeatherBadgeProps) {
  const icon = WEATHER_ICONS[weather.condition] || "🌤️";
  const styles = SEVERITY_STYLES[weather.severity] || SEVERITY_STYLES.great;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${styles}`}
        title={weather.summary}
      >
        {icon} {Math.round(weather.temp_max)}°
      </span>
    );
  }

  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border ${styles}`}>
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="text-sm font-medium">
          {Math.round(weather.temp_min)}° – {Math.round(weather.temp_max)}°C
        </div>
        <div className="text-xs opacity-80">{weather.summary}</div>
      </div>
      {weather.rain_probability > 0.2 && (
        <div className="ml-auto text-xs opacity-70">
          💧 {Math.round(weather.rain_probability * 100)}%
        </div>
      )}
    </div>
  );
}
