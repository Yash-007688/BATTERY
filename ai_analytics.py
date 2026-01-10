"""
AI-powered analytics for Battery Monitor
Provides predictive analytics, anomaly detection, and smart recommendations
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error
import joblib
import json
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from database import DatabaseManager
from ml_predictor import BatteryPredictor


@dataclass
class BatteryInsight:
    """Data class for AI-generated battery insights"""
    recommendation: str
    confidence: float
    priority: str  # 'high', 'medium', 'low'
    explanation: str
    timestamp: datetime


class AIBatteryAnalyzer:
    """AI-powered battery analysis and recommendation system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.model_path = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.model_path, exist_ok=True)
        
        # Initialize models
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.predictor = LinearRegression()
        self.scaler = StandardScaler()
        self.clusterer = KMeans(n_clusters=3, random_state=42)
        
        # Load existing models if available
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models if they exist"""
        try:
            anomaly_model_path = os.path.join(self.model_path, 'anomaly_model.pkl')
            if os.path.exists(anomaly_model_path):
                self.anomaly_detector = joblib.load(anomaly_model_path)
            
            predictor_model_path = os.path.join(self.model_path, 'predictor_model.pkl')
            if os.path.exists(predictor_model_path):
                self.predictor = joblib.load(predictor_model_path)
            
            scaler_path = os.path.join(self.model_path, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
        except:
            # If loading fails, continue with default models
            pass
    
    def _save_models(self):
        """Save trained models"""
        try:
            joblib.dump(self.anomaly_detector, os.path.join(self.model_path, 'anomaly_model.pkl'))
            joblib.dump(self.predictor, os.path.join(self.model_path, 'predictor_model.pkl'))
            joblib.dump(self.scaler, os.path.join(self.model_path, 'scaler.pkl'))
        except Exception as e:
            print(f"Error saving models: {e}")
    
    def get_historical_data(self, device_id: str, days: int = 30) -> pd.DataFrame:
        """Get historical battery data for analysis"""
        # Get data from database
        readings = self.db_manager.get_recent_readings(device_id, hours=days*24)
        
        if not readings:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for reading in readings:
            data.append({
                'timestamp': reading.timestamp,
                'percentage': reading.percentage,
                'voltage': reading.voltage,
                'temperature': reading.temperature,
                'is_charging': reading.is_charging
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['minute_of_day'] = df['timestamp'].dt.hour * 60 + df['timestamp'].dt.minute
        
        return df
    
    def detect_anomalies(self, device_id: str) -> List[Dict]:
        """Detect anomalous battery behavior patterns"""
        df = self.get_historical_data(device_id)
        
        if df.empty or len(df) < 10:
            return []
        
        # Prepare features for anomaly detection
        features = df[['percentage', 'voltage', 'temperature', 'hour', 'day_of_week']].dropna()
        
        if len(features) < 10:
            return []
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Detect anomalies
        anomalies = self.anomaly_detector.fit_predict(scaled_features)
        
        # Get anomalous readings
        anomalous_indices = np.where(anomalies == -1)[0]
        anomalous_readings = []
        
        for idx in anomalous_indices:
            if idx < len(df):
                anomalous_readings.append({
                    'timestamp': df.iloc[idx]['timestamp'].isoformat(),
                    'percentage': df.iloc[idx]['percentage'],
                    'voltage': df.iloc[idx]['voltage'],
                    'temperature': df.iloc[idx]['temperature'],
                    'reason': 'Unusual battery behavior pattern detected'
                })
        
        return anomalous_readings
    
    def predict_battery_lifespan(self, device_id: str) -> Dict:
        """Predict remaining battery lifespan"""
        df = self.get_historical_data(device_id, days=90)  # Use 3 months of data
        
        if df.empty:
            return {
                'prediction': 'Insufficient data for lifespan prediction',
                'confidence': 0.0,
                'estimated_months': None
            }
        
        # Calculate degradation rate
        if len(df) >= 2:
            first_reading = df.iloc[0]['percentage']
            last_reading = df.iloc[-1]['percentage']
            
            # Calculate degradation rate per day
            days = (df.iloc[-1]['timestamp'] - df.iloc[0]['timestamp']).days
            if days > 0:
                degradation_rate = (first_reading - last_reading) / days
                
                # Estimate remaining lifespan (assuming battery becomes unusable at 80% of original capacity)
                current_capacity = last_reading
                remaining_capacity = current_capacity - 80  # Assuming 80% is unusable threshold
                estimated_days = remaining_capacity / max(degradation_rate, 0.01)  # Avoid division by zero
                
                return {
                    'prediction': f'Estimated {estimated_days/30:.1f} months remaining before significant degradation',
                    'confidence': min(0.8, len(df) / 100),  # Confidence based on data amount
                    'estimated_months': estimated_days / 30
                }
        
        return {
            'prediction': 'Insufficient data for accurate prediction',
            'confidence': 0.3,
            'estimated_months': None
        }
    
    def analyze_usage_patterns(self, device_id: str) -> Dict:
        """Analyze user's device usage patterns"""
        df = self.get_historical_data(device_id, days=30)
        
        if df.empty:
            return {'message': 'Insufficient data for pattern analysis'}
        
        # Calculate average usage patterns
        charging_df = df[df['is_charging'] == 1]
        discharging_df = df[df['is_charging'] == 0]
        
        # Peak usage hours
        peak_hours = df.groupby('hour').size().sort_values(ascending=False).head(3)
        
        # Average charging/discharging rates
        charging_rates = []
        discharging_rates = []
        
        for i in range(len(df) - 1):
            time_diff = (df.iloc[i+1]['timestamp'] - df.iloc[i]['timestamp']).total_seconds() / 3600  # hours
            percent_diff = df.iloc[i+1]['percentage'] - df.iloc[i]['percentage']
            
            if time_diff > 0:
                rate = percent_diff / time_diff
                if df.iloc[i]['is_charging']:
                    charging_rates.append(rate)
                else:
                    discharging_rates.append(rate)
        
        return {
            'peak_usage_hours': peak_hours.index.tolist(),
            'avg_charging_rate': np.mean(charging_rates) if charging_rates else 0,
            'avg_discharging_rate': np.mean(discharging_rates) if discharging_rates else 0,
            'charging_frequency': len(charging_df) / len(df) * 100 if len(df) > 0 else 0,
            'most_common_percentage': df['percentage'].mode().iloc[0] if not df['percentage'].empty else None
        }
    
    def generate_smart_recommendations(self, device_id: str) -> List[BatteryInsight]:
        """Generate AI-powered battery recommendations"""
        insights = []
        
        # Anomaly detection
        anomalies = self.detect_anomalies(device_id)
        if anomalies:
            insights.append(BatteryInsight(
                recommendation="Unusual battery behavior detected",
                confidence=0.8,
                priority="high",
                explanation=f"We detected {len(anomalies)} unusual patterns in your battery behavior. Consider checking your device's power settings.",
                timestamp=datetime.now()
            ))
        
        # Lifespan prediction
        lifespan_pred = self.predict_battery_lifespan(device_id)
        if lifespan_pred['estimated_months']:
            months = lifespan_pred['estimated_months']
            if months < 6:
                priority = "high"
                explanation = "Your battery may need replacement soon based on degradation patterns."
            elif months < 12:
                priority = "medium"
                explanation = "Your battery shows signs of degradation. Consider replacement in the next few months."
            else:
                priority = "low"
                explanation = "Your battery appears to be in good condition based on current patterns."
            
            insights.append(BatteryInsight(
                recommendation=f"Battery lifespan: ~{months:.1f} months remaining",
                confidence=lifespan_pred['confidence'],
                priority=priority,
                explanation=explanation,
                timestamp=datetime.now()
            ))
        
        # Usage pattern analysis
        patterns = self.analyze_usage_patterns(device_id)
        if 'peak_usage_hours' in patterns:
            peak_hours = patterns['peak_usage_hours']
            if peak_hours:
                insights.append(BatteryInsight(
                    recommendation=f"Peak usage at hours: {peak_hours[:2]}",
                    confidence=0.7,
                    priority="medium",
                    explanation=f"Your device is most active during these hours. Consider optimizing charging schedules around these times.",
                    timestamp=datetime.now()
                ))
        
        # Charging efficiency
        if 'avg_charging_rate' in patterns and patterns['avg_charging_rate'] > 0:
            rate = patterns['avg_charging_rate']
            if rate < 2:  # Slow charging
                insights.append(BatteryInsight(
                    recommendation="Slow charging detected",
                    confidence=0.6,
                    priority="medium",
                    explanation="Your device charges slowly. This could indicate battery degradation or charging issues.",
                    timestamp=datetime.now()
                ))
        
        return insights
    
    def adaptive_threshold_adjustment(self, device_id: str) -> int:
        """Suggest optimal threshold based on usage patterns"""
        patterns = self.analyze_usage_patterns(device_id)
        
        if 'peak_usage_hours' in patterns and patterns['peak_usage_hours']:
            # If user is typically active during certain hours, set threshold to ensure battery doesn't drain
            peak_hours = patterns['peak_usage_hours']
            avg_discharging_rate = patterns.get('avg_discharging_rate', -0.5)
            
            # If discharging is fast, suggest higher threshold
            if avg_discharging_rate < -1:  # Fast discharge
                return 90
            elif avg_discharging_rate < -0.5:  # Moderate discharge
                return 85
            else:  # Slow discharge
                return 80
        else:
            return 80  # Default threshold
    
    def train_models(self):
        """Train AI models with available data"""
        # This would be called periodically to update models with new data
        print("Training AI models with latest data...")
        
        # For now, just save the current models
        self._save_models()
        
        return True


class AIProductivityEnhancer:
    """AI-powered productivity enhancements for battery monitoring"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.analyzer = AIBatteryAnalyzer(db_manager)
    
    def generate_daily_battery_report(self, device_id: str) -> Dict:
        """Generate AI-powered daily battery report"""
        insights = self.analyzer.generate_smart_recommendations(device_id)
        patterns = self.analyzer.analyze_usage_patterns(device_id)
        lifespan_pred = self.analyzer.predict_battery_lifespan(device_id)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'device_id': device_id,
            'insights': [
                {
                    'recommendation': insight.recommendation,
                    'confidence': insight.confidence,
                    'priority': insight.priority,
                    'explanation': insight.explanation
                }
                for insight in insights
            ],
            'usage_patterns': patterns,
            'lifespan_prediction': lifespan_pred,
            'adaptive_threshold_suggestion': self.analyzer.adaptive_threshold_adjustment(device_id)
        }
    
    def predict_charge_time(self, device_id: str, target_percentage: int = 100) -> Dict:
        """AI-enhanced charge time prediction"""
        df = self.analyzer.get_historical_data(device_id)
        
        if df.empty:
            return {
                'prediction': 'Insufficient data for prediction',
                'confidence': 0.0,
                'estimated_minutes': None
            }
        
        # Get current charging data
        charging_df = df[df['is_charging'] == 1]
        if len(charging_df) < 3:
            return {
                'prediction': 'Not enough charging data',
                'confidence': 0.0,
                'estimated_minutes': None
            }
        
        # Calculate current charging rate
        current_percentage = df.iloc[-1]['percentage']
        if current_percentage >= target_percentage:
            return {
                'prediction': 'Already at target percentage',
                'confidence': 1.0,
                'estimated_minutes': 0
            }
        
        # Use recent charging data to predict
        recent_charging = charging_df.tail(10)  # Use last 10 readings
        if len(recent_charging) < 2:
            return {
                'prediction': 'Insufficient recent charging data',
                'confidence': 0.3,
                'estimated_minutes': None
            }
        
        # Calculate average charging rate from recent data
        time_diffs = []
        percent_diffs = []
        
        for i in range(1, len(recent_charging)):
            time_diff = (recent_charging.iloc[i]['timestamp'] - 
                        recent_charging.iloc[i-1]['timestamp']).total_seconds() / 60  # minutes
            percent_diff = (recent_charging.iloc[i]['percentage'] - 
                           recent_charging.iloc[i-1]['percentage'])
            
            if time_diff > 0 and percent_diff > 0:
                time_diffs.append(time_diff)
                percent_diffs.append(percent_diff)
        
        if time_diffs and percent_diffs:
            avg_rate = np.mean([p/t for p, t in zip(percent_diffs, time_diffs) if t > 0])
            remaining_percent = target_percentage - current_percentage
            
            if avg_rate > 0:
                estimated_minutes = remaining_percent / avg_rate
                confidence = min(0.9, len(time_diffs) / 20)  # Confidence based on data points
                
                return {
                    'prediction': f'Estimated {estimated_minutes:.0f} minutes to reach {target_percentage}%',
                    'confidence': confidence,
                    'estimated_minutes': estimated_minutes
                }
        
        return {
            'prediction': 'Unable to predict charge time',
            'confidence': 0.2,
            'estimated_minutes': None
        }
    
    def smart_notification_filter(self, device_id: str, notification_type: str, 
                                  battery_percentage: float) -> Tuple[bool, float]:
        """AI-powered notification filtering based on importance"""
        patterns = self.analyzer.analyze_usage_patterns(device_id)
        
        # Base confidence on usage patterns
        confidence = 0.7
        
        # Adjust based on time of day
        current_hour = datetime.now().hour
        peak_hours = patterns.get('peak_usage_hours', [])
        
        # If it's peak usage time and battery is low, increase importance
        if current_hour in peak_hours and battery_percentage < 20:
            return True, min(0.9, confidence + 0.2)
        
        # If it's not peak usage time and battery is high, decrease importance
        if current_hour not in peak_hours and battery_percentage > 80:
            return False, max(0.3, confidence - 0.4)
        
        # Default behavior
        return True, confidence