import os
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import threading

# Intent configuration
intents = discord.Intents.default()
intents.message_content = True  # Required for some commands

class DiscordBot:
    def __init__(self, battery_monitor):
        self.monitor = battery_monitor
        self.token = os.getenv('DISCORD_BOT_TOKEN')
        self.bot = commands.Bot(command_prefix='/', intents=intents)
        self._loop = None
        self._thread = None
        
        # Register commands
        self.setup_commands()

    def setup_commands(self):
        @self.bot.event
        async def on_ready():
            print(f'Discord Bot connected as {self.bot.user}')

        @self.bot.command(name='battery')
        async def battery_status(ctx):
            """Get current battery status"""
            # Get battery info from monitor
            percent, plugged, device, device_id, extra_info = self.monitor._get_battery_info()
            
            # Formatting the response
            status_emoji = "⚡" if plugged else "🔋"
            status_text = "Charging" if plugged else "Discharging"
            
            # Start creating the embed
            embed = discord.Embed(
                title=f"{status_emoji} Battery Status: {device.capitalize()}",
                color=discord.Color.green() if percent > 20 else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Level", value=f"{percent:.0f}%", inline=True)
            embed.add_field(name="Status", value=status_text, inline=True)
            
            # Add extra info if available
            if extra_info:
                if 'health' in extra_info:
                    embed.add_field(name="Health", value=extra_info['health'], inline=True)
                if 'temperature' in extra_info:
                    temp = extra_info['temperature'] / 10.0
                    embed.add_field(name="Temperature", value=f"{temp:.1f}°C", inline=True)
            
            # Charging details
            if plugged and self.monitor._start_time:
                charging_duration = datetime.now() - self.monitor._start_time
                hours, remainder = divmod(charging_duration.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
                
                embed.add_field(name="Charging Time", value=duration_str, inline=False)
                embed.add_field(name="Started At", value=self.monitor._start_time.strftime('%H:%M:%S'), inline=True)
                
                # Calculate rate
                if self.monitor._start_percent is not None:
                    gained = percent - self.monitor._start_percent
                    if gained > 0:
                        rate = gained / (charging_duration.total_seconds() / 60)
                        embed.add_field(name="Avg Rate", value=f"{rate:.2f}%/min", inline=True)

            # Estimated time
            est_time = self.monitor._estimate_charge_time(percent, plugged)
            if est_time:
                target = "100%" if percent >= self.monitor.threshold_percent else f"{self.monitor.threshold_percent}%"
                embed.add_field(name=f"Est. to {target}", value=est_time, inline=False)

            await ctx.send(embed=embed)
            
        @self.bot.command(name='stats')
        async def stats(ctx):
            """Get detailed technical stats"""
            percent, plugged, device, device_id, extra_info = self.monitor._get_battery_info()
            
            embed = discord.Embed(
                title=f"📊 Technical Stats: {device.capitalize()}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Voltage", value=f"{extra_info.get('voltage', 0)/1000:.2f} V" if extra_info and 'voltage' in extra_info else "N/A", inline=True)
            embed.add_field(name="Temperature", value=f"{extra_info.get('temperature', 0)/10:.1f} °C" if extra_info and 'temperature' in extra_info else "N/A", inline=True)
            embed.add_field(name="Technology", value=extra_info.get('technology', 'Unknown') if extra_info else "Unknown", inline=True)
            
            # Charging stats from predictor if available
            if self.monitor.predictor:
                stats = self.monitor.predictor.get_charging_statistics('laptop', device_id)
                if stats:
                    embed.add_field(name="Charge Cycles", value=str(stats.get('total_cycles', 0)), inline=True)
                    embed.add_field(name="Avg Charge Rate", value=f"{stats.get('avg_charge_rate', 0):.2f}%/min", inline=True)
                    embed.add_field(name="Fastest Rate", value=f"{stats.get('fastest_charge_rate', 0):.2f}%/min", inline=True)

            await ctx.send(embed=embed)

        @self.bot.command(name='set')
        async def set_threshold(ctx, threshold: int):
            """Set battery alert threshold"""
            if 1 <= threshold <= 100:
                self.monitor.update_threshold(threshold)
                await ctx.send(f"✅ Threshold updated to **{threshold}%**")
            else:
                await ctx.send("❌ Please provide a value between 1 and 100.")

        @self.bot.command(name='predict')
        async def predict(ctx):
            """Get ML-based charge prediction"""
            percent, plugged, _, device_id, _ = self.monitor._get_battery_info()
            
            if not plugged:
                await ctx.send("⚠️ Device is not charging. Prediction requires charging state.")
                return
            
            prediction = self.monitor.get_ai_charge_prediction(device_id)
            if prediction and prediction.get('estimated_minutes'):
                minutes = prediction['estimated_minutes']
                confidence = prediction.get('confidence', 0)
                
                embed = discord.Embed(
                    title="🔮 AI Charge Prediction",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Time to 100%", value=f"{int(minutes)} minutes", inline=True)
                embed.add_field(name="Confidence", value=f"{confidence*100:.0f}%", inline=True)
                embed.add_field(name="Completion Time", value=(datetime.now() + timedelta(minutes=minutes)).strftime('%H:%M:%S'), inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("⚠️ Not enough data for AI prediction yet.")

        @self.bot.command(name='insights')
        async def insights(ctx):
            """Get AI health insights"""
            percent, _, _, device_id, _ = self.monitor._get_battery_info()
            report = self.monitor.get_ai_insights(device_id)
            
            if not report:
                await ctx.send("⚠️ AI module not initialized or no data available.")
                return
                
            embed = discord.Embed(
                title="🧠 AI Battery Insights",
                color=discord.Color.gold()
            )
            
            # Lifespan
            lifespan = report.get('lifespan_prediction', {})
            if lifespan.get('estimated_months'):
                embed.add_field(name="Predicted Lifespan", value=f"{lifespan['estimated_months']:.1f} months", inline=False)
            
            # Recommendations
            for insight in report.get('insights', [])[:3]:  # Top 3 insights
                icon = "🔴" if insight['priority'] == 'high' else "🟡" if insight['priority'] == 'medium' else "🟢"
                embed.add_field(
                    name=f"{icon} Recommendation",
                    value=insight['recommendation'],
                    inline=False
                )
            
            # Usage Patterns
            patterns = report.get('usage_patterns', {})
            if patterns.get('peak_usage_hours'):
                hours = ", ".join([f"{h}:00" for h in patterns['peak_usage_hours']])
                embed.add_field(name="Peak Usage Hours", value=hours, inline=True)
                
            await ctx.send(embed=embed)

        @self.bot.command(name='batterydischarge')
        async def battery_discharge(ctx):
            """Get discharge information"""
            percent, plugged, _, _, extra_info = self.monitor._get_battery_info()
            
            if plugged:
                await ctx.send(f"⚠️ Device is currently **Charging** at {percent:.0f}%. Unplug to see discharge info.")
                return

            embed = discord.Embed(
                title="📉 Discharge Status",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Current Level", value=f"{percent:.0f}%", inline=True)
            
            if extra_info and 'time_left_seconds' in extra_info:
                seconds_left = extra_info['time_left_seconds']
                hours, remainder = divmod(seconds_left, 3600)
                minutes, _ = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m"
                
                completion_time = datetime.now() + timedelta(seconds=seconds_left)
                
                embed.add_field(name="Time Remaining", value=time_str, inline=True)
                embed.add_field(name="Estimated Empty", value=completion_time.strftime('%H:%M:%S'), inline=False)
            else:
                embed.add_field(name="Time Remaining", value="Calculating...", inline=True)
            
            await ctx.send(embed=embed)

        @self.bot.command(name='setalertchannel')
        async def set_alert_channel(ctx):
            """Set the current channel for battery alerts"""
            self.monitor.config_manager.set_value('discord_channel_id', ctx.channel.id)
            self.monitor.config_manager.save_config()
            await ctx.send(f"✅ Battery alerts will now be sent to {ctx.channel.mention}")

            await self.send_alert("🔔 This is a test alert!", mention=True)

    async def send_alert(self, message, mention=True):
        """Send an alert to the configured channel"""
        if not self.monitor.config_manager:
            return

        channel_id = self.monitor.config_manager.get_value('discord_channel_id')
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if channel:
            if mention:
                message = f"@everyone {message}"
            try:
                await channel.send(message)
            except Exception as e:
                print(f"Failed to send Discord alert: {e}")

    def start(self):
        """Start the bot in a separate thread"""
        if not self.token:
            print("Discord Bot Token not found. Bot disabled.")
            return

        def run_bot():
            # Create a new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self.bot.start(self.token))
            except Exception as e:
                print(f"Error running Discord bot: {e}")
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=run_bot, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the bot"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.bot.close(), self._loop)
