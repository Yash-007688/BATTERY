"""
Machine Learning predictor for battery charge time estimation
"""
import os
import pickle
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures


class BatteryPredictor:
    """ML-based battery charge time predictor"""
    
    def __init__(self, db_manager=None, model_path: str = None):
        self.db_manager = db_manager
        
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), 'battery_model.pkl')
        self.model_path = model_path
        
        # Models for different scenarios
        self.laptop_model = None
        self.phone_model = None
        
        # Polynomial features for better curve fitting
        self.poly_features = PolynomialFeatures(degree=2)
        
        # Training data cache
        self.laptop_training_data = []
        self.phone_training_data = []
        
        # Load existing models if available
        self.load_models()
    
    def load_models(self):
        """Load saved models from disk"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.laptop_model = data.get('laptop_model')
                    self.phone_model = data.get('phone_model')
                    print("ML models loaded successfully")
            except Exception as e:
                print(f"Error loading models: {e}")
    
    def save_models(self):
        """Save models to disk"""
        try:
            data = {
                'laptop_model': self.laptop_model,
                'phone_model': self.phone_model
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(data, f)
            print("ML models saved successfully")
        except Exception as e:
            print(f"Error saving models: {e}")
    
    def train_from_history(self, device_type: str = 'laptop', device_id: str = None):
        """Train model from historical charge cycles"""
        if not self.db_manager:
            print("Database manager not configured")
            return False
        
        try:
            # Get completed charge cycles
            if device_id:
                cycles = self.db_manager.get_charge_history(device_id, limit=100)
            else:
                # Get all cycles for device type
                cycles = []
                # This would need a method to get all devices of a type
            
            if len(cycles) < 5:
                print(f"Not enough data to train {device_type} model (need at least 5 cycles)")
                return False
            
            # Prepare training data
            X = []  # Features: [start_percentage, target_percentage, avg_delta_1m]
            y = []  # Target: duration in minutes
            
            for cycle in cycles:
                if cycle.avg_delta_1m and cycle.duration_seconds:
                    X.append([
                        cycle.start_percentage,
                        cycle.target_percentage,
                        cycle.avg_delta_1m
                    ])
                    y.append(cycle.duration_seconds / 60.0)  # Convert to minutes
            
            if len(X) < 5:
                print(f"Not enough valid data to train {device_type} model")
                return False
            
            # Train model
            X = np.array(X)
            y = np.array(y)
            
            # Use polynomial features for better fitting
            X_poly = self.poly_features.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Save model
            if device_type == 'laptop':
                self.laptop_model = model
            else:
                self.phone_model = model
            
            self.save_models()
            
            print(f"Trained {device_type} model with {len(X)} samples")
            return True
            
        except Exception as e:
            print(f"Error training model: {e}")
            return False
    
    def predict_charge_time(self, device_type: str, current_percentage: float,
                          target_percentage: float, recent_delta_1m: float = None) -> Tuple[Optional[float], float]:
        """
        Predict time to reach target percentage
        Returns: (predicted_minutes, confidence_score)
        """
        model = self.laptop_model if device_type == 'laptop' else self.phone_model
        
        if model is None:
            # Fallback to simple linear estimation
            return self._simple_prediction(current_percentage, target_percentage, recent_delta_1m)
        
        try:
            # Use recent delta if available, otherwise use a default
            if recent_delta_1m is None:
                recent_delta_1m = 1.0  # Default 1% per minute
            
            # Prepare features
            X = np.array([[current_percentage, target_percentage, recent_delta_1m]])
            X_poly = self.poly_features.transform(X)
            
            # Predict
            predicted_minutes = model.predict(X_poly)[0]
            
            # Calculate confidence based on how much training data we have
            confidence = min(0.9, 0.5 + (len(self.laptop_training_data) / 100.0))
            
            return max(0, predicted_minutes), confidence
            
        except Exception as e:
            print(f"Error in prediction: {e}")
            return self._simple_prediction(current_percentage, target_percentage, recent_delta_1m)
    
    def _simple_prediction(self, current_percentage: float, target_percentage: float,
                          recent_delta_1m: float = None) -> Tuple[Optional[float], float]:
        """Simple linear prediction as fallback"""
        if current_percentage >= target_percentage:
            return 0.0, 1.0
        
        remaining = target_percentage - current_percentage
        
        if recent_delta_1m and recent_delta_1m > 0:
            # Use recent charging rate
            minutes = remaining / recent_delta_1m
            return minutes, 0.6
        
        # Default assumption: 1% per minute
        return remaining, 0.3
    
    def update_with_reading(self, device_type: str, percentage: float,
                          delta_1m: float = None):
        """Update training data with new reading"""
        data = {
            'timestamp': datetime.now(),
            'percentage': percentage,
            'delta_1m': delta_1m
        }
        
        if device_type == 'laptop':
            self.laptop_training_data.append(data)
            # Keep only recent data (last 1000 readings)
            if len(self.laptop_training_data) > 1000:
                self.laptop_training_data.pop(0)
        else:
            self.phone_training_data.append(data)
            if len(self.phone_training_data) > 1000:
                self.phone_training_data.pop(0)
    
    def get_adaptive_poll_interval(self, device_type: str, current_percentage: float,
                                   target_percentage: float, base_interval: int = 30) -> int:
        """
        Calculate adaptive polling interval
        Poll more frequently when near threshold
        """
        if current_percentage >= target_percentage:
            return base_interval
        
        remaining = target_percentage - current_percentage
        
        if remaining <= 2:
            # Very close - poll every 10 seconds
            return 10
        elif remaining <= 5:
            # Close - poll every 15 seconds
            return 15
        elif remaining <= 10:
            # Moderately close - poll every 20 seconds
            return 20
        else:
            # Far away - use base interval
            return base_interval
    
    def get_charging_statistics(self, device_type: str, device_id: str = None) -> dict:
        """Get charging statistics from historical data"""
        if not self.db_manager:
            return {}
        
        try:
            cycles = self.db_manager.get_charge_history(device_id, limit=50)
            
            if not cycles:
                return {}
            
            durations = [c.duration_seconds / 60.0 for c in cycles if c.duration_seconds]
            avg_deltas = [c.avg_delta_1m for c in cycles if c.avg_delta_1m]
            
            stats = {
                'total_cycles': len(cycles),
                'avg_duration_minutes': np.mean(durations) if durations else 0,
                'min_duration_minutes': np.min(durations) if durations else 0,
                'max_duration_minutes': np.max(durations) if durations else 0,
                'avg_charge_rate': np.mean(avg_deltas) if avg_deltas else 0,
                'fastest_charge_rate': np.max(avg_deltas) if avg_deltas else 0,
                'slowest_charge_rate': np.min(avg_deltas) if avg_deltas else 0
            }
            
            return stats
            
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}


class BatteryHealthAnalyzer:
    """Analyze battery health and provide recommendations"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
    
    def calculate_health_score(self, device_type: str, device_id: str = None,
                              design_capacity: int = None, 
                              full_charge_capacity: int = None) -> Tuple[float, str]:
        """
        Calculate battery health score (0-100)
        Returns: (score, status_text)
        """
        if design_capacity and full_charge_capacity:
            # Calculate based on capacity degradation
            health_percentage = (full_charge_capacity / design_capacity) * 100
            
            if health_percentage >= 90:
                return health_percentage, "Excellent"
            elif health_percentage >= 80:
                return health_percentage, "Good"
            elif health_percentage >= 60:
                return health_percentage, "Fair"
            elif health_percentage >= 40:
                return health_percentage, "Poor"
            else:
                return health_percentage, "Critical"
        
        # Fallback: analyze from charge cycles
        if self.db_manager and device_id:
            cycles = self.db_manager.get_charge_history(device_id, limit=20)
            
            if len(cycles) >= 10:
                # Analyze degradation trend
                recent_rates = [c.avg_delta_1m for c in cycles[:5] if c.avg_delta_1m]
                older_rates = [c.avg_delta_1m for c in cycles[10:15] if c.avg_delta_1m]
                
                if recent_rates and older_rates:
                    recent_avg = np.mean(recent_rates)
                    older_avg = np.mean(older_rates)
                    
                    # If charging rate has decreased significantly, health is degrading
                    degradation = ((older_avg - recent_avg) / older_avg) * 100
                    
                    health_score = max(0, 100 - degradation * 2)
                    
                    if health_score >= 85:
                        return health_score, "Good"
                    elif health_score >= 70:
                        return health_score, "Fair"
                    else:
                        return health_score, "Degraded"
        
        return 100.0, "Unknown"
    
    def get_recommendations(self, health_score: float, charge_cycles: int = None) -> List[str]:
        """Get battery health recommendations"""
        recommendations = []
        
        if health_score < 80:
            recommendations.append("⚠️ Battery health is degraded. Consider battery replacement.")
        
        if health_score < 60:
            recommendations.append("🔴 Battery health is poor. Replacement recommended soon.")
        
        if charge_cycles and charge_cycles > 500:
            recommendations.append("ℹ️ Battery has completed many charge cycles. Monitor health closely.")
        
        # General recommendations
        recommendations.extend([
            "💡 Keep battery between 20-80% for optimal lifespan",
            "🌡️ Avoid extreme temperatures",
            "🔌 Unplug when fully charged",
            "⚡ Use original charger when possible"
        ])
        
        return recommendations
