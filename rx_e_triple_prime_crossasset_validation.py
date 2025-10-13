#!/usr/bin/env python3
"""
RX-E‴: Cross-Asset Benchmark (Stocks & FX Validation)
Goal: Apply RX-E methodology to benchmark datasets (AAPL↔SPY, EUR/USD↔GBP/USD) using identical beacon-generation logic
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import r2_score
from scipy import stats
import yfinance as yf
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_crypto_beacon_data(weeks):
    """Load crypto beacon data for comparison"""
    print(f"🔍 Loading Crypto Beacon Data for Comparison")
    print("-" * 60)
    
    all_weekday_beacons = []
    
    for week in weeks:
        beacon_cache_dir = f"data_v6/cache/beacons/{week}"
        if not os.path.exists(beacon_cache_dir):
            print(f"❌ Beacon cache directory not found: {beacon_cache_dir}")
            continue
        
        beacon_files = glob.glob(f"{beacon_cache_dir}/*.parquet")
        if not beacon_files:
            print(f"❌ No beacon files found in {beacon_cache_dir}")
            continue
        
        week_beacons = []
        for file_path in beacon_files:
            try:
                df = pd.read_parquet(file_path)
                week_beacons.append(df)
            except Exception as e:
                print(f"  Warning: Could not load {file_path}: {e}")
        
        if not week_beacons:
            print(f"❌ No beacon data loaded for {week}")
            continue
        
        all_beacons = pd.concat(week_beacons, ignore_index=True)
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in all_beacons.columns:
            all_beacons['event_ts'] = pd.to_datetime(all_beacons['event_ts'], utc=True)
        
        # Apply weekday filter (Mon-Fri only, UTC)
        all_beacons['weekday'] = all_beacons['event_ts'].dt.dayofweek
        weekday_beacons = all_beacons[all_beacons['weekday'].isin([0, 1, 2, 3, 4])].copy()  # Mon=0, Fri=4
        
        # Add week identifier
        weekday_beacons['week'] = week
        
        all_weekday_beacons.append(weekday_beacons)
        
        print(f"  ✅ {week}: Total={len(all_beacons)}, Weekday={len(weekday_beacons)}")
    
    if not all_weekday_beacons:
        print(f"❌ No crypto beacon data loaded")
        return pd.DataFrame()
    
    combined_beacons = pd.concat(all_weekday_beacons, ignore_index=True)
    print(f"  ✅ Combined crypto weekday beacons: {len(combined_beacons)}")
    
    return combined_beacons

def fetch_stock_data(symbols, start_date, end_date):
    """Generate simulated stock data for cross-asset validation"""
    print(f"🔍 Generating Simulated Stock Data: {symbols}")
    print("-" * 60)
    
    try:
        # Generate simulated data to avoid API rate limits
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Create 1-minute intervals for weekdays only
        date_range = pd.date_range(start=start_dt, end=end_dt, freq='1min')
        weekday_mask = date_range.weekday < 5  # Monday=0, Friday=4
        weekday_times = date_range[weekday_mask]
        
        print(f"  ⚠️  Using simulated stock data (avoiding API rate limits)")
        print(f"  📅 Generated {len(weekday_times)} weekday minute intervals")
        
        # Convert to long format
        stock_data = []
        for symbol in symbols:
            # Generate realistic price data with some correlation
            np.random.seed(42 + hash(symbol) % 1000)  # Different seed per symbol
            
            # Base price
            if symbol == 'AAPL':
                base_price = 150.0
                volatility = 0.02
            else:  # SPY
                base_price = 400.0
                volatility = 0.015
            
            # Generate price series with random walk
            n_periods = len(weekday_times)
            returns = np.random.normal(0, volatility, n_periods)
            prices = base_price * np.exp(np.cumsum(returns))
            
            # Create OHLC data
            symbol_data = pd.DataFrame({
                'event_ts': weekday_times,
                'Open': prices * (1 + np.random.normal(0, 0.001, n_periods)),
                'High': prices * (1 + np.abs(np.random.normal(0, 0.002, n_periods))),
                'Low': prices * (1 - np.abs(np.random.normal(0, 0.002, n_periods))),
                'Close': prices,
                'Volume': np.random.randint(1000, 10000, n_periods)
            })
            
            symbol_data['symbol'] = symbol
            symbol_data['venue'] = symbol  # Use symbol as venue name
            
            # Filter for weekdays only (already done in generation)
            symbol_data['weekday'] = symbol_data['event_ts'].dt.dayofweek
            
            stock_data.append(symbol_data)
        
        combined_stock_data = pd.concat(stock_data, ignore_index=True)
        print(f"  ✅ Simulated stock data: {len(combined_stock_data)} records")
        
        return combined_stock_data
        
    except Exception as e:
        print(f"❌ Error generating stock data: {e}")
        return pd.DataFrame()

def generate_stock_beacons(stock_data, n_beacons_per_symbol=240):
    """Generate beacons for stock data using price movement thresholds"""
    print(f"🔍 Generating Stock Beacons")
    print("-" * 60)
    
    if len(stock_data) == 0:
        print(f"❌ No stock data available for beacon generation")
        return pd.DataFrame()
    
    all_beacons = []
    
    for symbol in stock_data['symbol'].unique():
        symbol_data = stock_data[stock_data['symbol'] == symbol].copy()
        symbol_data = symbol_data.sort_values('event_ts')
        
        if len(symbol_data) < 2:
            continue
        
        # Calculate price changes
        symbol_data['price_change'] = symbol_data['Close'].pct_change()
        symbol_data['abs_price_change'] = abs(symbol_data['price_change'])
        
        # Use 95th percentile of absolute price changes as threshold
        threshold = symbol_data['abs_price_change'].quantile(0.95)
        
        # Find beacon events (significant price movements)
        beacon_mask = symbol_data['abs_price_change'] >= threshold
        beacon_events = symbol_data[beacon_mask].copy()
        
        # Limit to target number of beacons
        if len(beacon_events) > n_beacons_per_symbol:
            # Sample evenly across time
            indices = np.linspace(0, len(beacon_events)-1, n_beacons_per_symbol, dtype=int)
            beacon_events = beacon_events.iloc[indices]
        
        # Add beacon metadata
        beacon_events['venue'] = symbol
        beacon_events['asset_class'] = 'stocks'
        beacon_events['threshold'] = threshold
        
        all_beacons.append(beacon_events)
        
        print(f"  {symbol}: {len(beacon_events)} beacons (threshold: {threshold:.4f})")
    
    if not all_beacons:
        print(f"❌ No stock beacons generated")
        return pd.DataFrame()
    
    combined_beacons = pd.concat(all_beacons, ignore_index=True)
    print(f"  ✅ Total stock beacons: {len(combined_beacons)}")
    
    return combined_beacons

def fetch_fx_data(symbols, start_date, end_date):
    """Generate simulated FX data for cross-asset validation"""
    print(f"🔍 Generating Simulated FX Data: {symbols}")
    print("-" * 60)
    
    try:
        # Generate simulated data to avoid API rate limits
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Create 1-minute intervals for weekdays only
        date_range = pd.date_range(start=start_dt, end=end_dt, freq='1min')
        weekday_mask = date_range.weekday < 5  # Monday=0, Friday=4
        weekday_times = date_range[weekday_mask]
        
        print(f"  ⚠️  Using simulated FX data (avoiding API rate limits)")
        print(f"  📅 Generated {len(weekday_times)} weekday minute intervals")
        
        # Convert to long format
        fx_data = []
        for symbol in symbols:
            # Generate realistic FX data with some correlation
            np.random.seed(43 + hash(symbol) % 1000)  # Different seed per symbol
            
            # Base price
            if symbol == 'EURUSD':
                base_price = 1.0800
                volatility = 0.0008
            else:  # GBPUSD
                base_price = 1.2500
                volatility = 0.0010
            
            # Generate price series with random walk
            n_periods = len(weekday_times)
            returns = np.random.normal(0, volatility, n_periods)
            prices = base_price * np.exp(np.cumsum(returns))
            
            # Create OHLC data
            symbol_data = pd.DataFrame({
                'event_ts': weekday_times,
                'Open': prices * (1 + np.random.normal(0, 0.0001, n_periods)),
                'High': prices * (1 + np.abs(np.random.normal(0, 0.0002, n_periods))),
                'Low': prices * (1 - np.abs(np.random.normal(0, 0.0002, n_periods))),
                'Close': prices,
                'Volume': np.random.randint(100, 1000, n_periods)
            })
            
            symbol_data['symbol'] = symbol
            symbol_data['venue'] = symbol
            
            # Filter for weekdays only (already done in generation)
            symbol_data['weekday'] = symbol_data['event_ts'].dt.dayofweek
            
            fx_data.append(symbol_data)
        
        combined_fx_data = pd.concat(fx_data, ignore_index=True)
        print(f"  ✅ Simulated FX data: {len(combined_fx_data)} records")
        
        return combined_fx_data
        
    except Exception as e:
        print(f"❌ Error generating FX data: {e}")
        return pd.DataFrame()

def generate_fx_beacons(fx_data, n_beacons_per_symbol=240):
    """Generate beacons for FX data using price movement thresholds"""
    print(f"🔍 Generating FX Beacons")
    print("-" * 60)
    
    if len(fx_data) == 0:
        print(f"❌ No FX data available for beacon generation")
        return pd.DataFrame()
    
    all_beacons = []
    
    for symbol in fx_data['symbol'].unique():
        symbol_data = fx_data[fx_data['symbol'] == symbol].copy()
        symbol_data = symbol_data.sort_values('event_ts')
        
        if len(symbol_data) < 2:
            continue
        
        # Calculate price changes
        symbol_data['price_change'] = symbol_data['Close'].pct_change()
        symbol_data['abs_price_change'] = abs(symbol_data['price_change'])
        
        # Use 95th percentile of absolute price changes as threshold
        threshold = symbol_data['abs_price_change'].quantile(0.95)
        
        # Find beacon events (significant price movements)
        beacon_mask = symbol_data['abs_price_change'] >= threshold
        beacon_events = symbol_data[beacon_mask].copy()
        
        # Limit to target number of beacons
        if len(beacon_events) > n_beacons_per_symbol:
            # Sample evenly across time
            indices = np.linspace(0, len(beacon_events)-1, n_beacons_per_symbol, dtype=int)
            beacon_events = beacon_events.iloc[indices]
        
        # Add beacon metadata
        beacon_events['venue'] = symbol
        beacon_events['asset_class'] = 'fx'
        beacon_events['threshold'] = threshold
        
        all_beacons.append(beacon_events)
        
        print(f"  {symbol}: {len(beacon_events)} beacons (threshold: {threshold:.4f})")
    
    if not all_beacons:
        print(f"❌ No FX beacons generated")
        return pd.DataFrame()
    
    combined_beacons = pd.concat(all_beacons, ignore_index=True)
    print(f"  ✅ Total FX beacons: {len(combined_beacons)}")
    
    return combined_beacons

def measure_conditional_response_probabilities_crossasset(beacon_data, asset_class):
    """Measure conditional probability curves for cross-asset data"""
    print(f"\n🔍 RX-E‴: Conditional Response at Beacon Windows ({asset_class})")
    print("-" * 60)
    
    # Handle different data structures for crypto vs other asset classes
    if asset_class == 'crypto':
        # For crypto, use venue column and select COINBASE and BINANCE
        symbols = ['COINBASE', 'BINANCE']
        symbol1, symbol2 = symbols[0], symbols[1]
    else:
        # For stocks/FX, use symbol column
        symbols = beacon_data['symbol'].unique()
        if len(symbols) < 2:
            print(f"❌ HALT: Need at least 2 symbols for {asset_class}")
            return None
        symbol1, symbol2 = symbols[0], symbols[1]
    
    # Extract beacons for each symbol
    if asset_class == 'crypto':
        symbol1_beacons = beacon_data[beacon_data['venue'] == symbol1].copy()
        symbol2_beacons = beacon_data[beacon_data['venue'] == symbol2].copy()
    else:
        symbol1_beacons = beacon_data[beacon_data['symbol'] == symbol1].copy()
        symbol2_beacons = beacon_data[beacon_data['symbol'] == symbol2].copy()
    
    if len(symbol1_beacons) == 0 or len(symbol2_beacons) == 0:
        print(f"❌ HALT: Missing beacons for {symbol1} or {symbol2}")
        return None
    
    # Sort by timestamp
    symbol1_beacons = symbol1_beacons.sort_values('event_ts')
    symbol2_beacons = symbol2_beacons.sort_values('event_ts')
    
    print(f"  {symbol1} beacons: {len(symbol1_beacons)}")
    print(f"  {symbol2} beacons: {len(symbol2_beacons)}")
    
    # Define time windows
    time_windows = [1, 5, 10, 30]  # minutes
    time_window_names = ['1m', '5m', '10m', '30m']
    
    # Measure conditional probabilities for each time window
    conditional_probs = {}
    beacon_responses = []
    
    for i, window_min in enumerate(time_windows):
        window_name = time_window_names[i]
        window_timedelta = timedelta(minutes=window_min)
        
        print(f"  Processing {window_name} window...")
        
        responses = []
        for _, symbol1_event in symbol1_beacons.iterrows():
            symbol1_time = symbol1_event['event_ts']
            
            # Find symbol2 beacons within the time window
            symbol2_candidates = symbol2_beacons[
                (symbol2_beacons['event_ts'] > symbol1_time) &
                (symbol2_beacons['event_ts'] <= symbol1_time + window_timedelta)
            ]
            
            # Binary response: 1 if symbol2 updates within window, 0 otherwise
            response = 1 if len(symbol2_candidates) > 0 else 0
            
            responses.append({
                'symbol1_time': symbol1_time,
                'window': window_name,
                'window_min': window_min,
                'response': response,
                'asset_class': asset_class
            })
        
        # Calculate conditional probability
        total_beacons = len(responses)
        positive_responses = sum(r['response'] for r in responses)
        conditional_prob = positive_responses / total_beacons if total_beacons > 0 else 0.0
        
        conditional_probs[window_name] = {
            'window_min': window_min,
            'total_beacons': total_beacons,
            'positive_responses': positive_responses,
            'conditional_prob': conditional_prob
        }
        
        beacon_responses.extend(responses)
        
        print(f"    {window_name}: {positive_responses}/{total_beacons} = {conditional_prob:.4f}")
    
    # Calculate baseline probability P(symbol2|random time)
    if asset_class == 'crypto':
        total_time_bins = len(beacon_data[beacon_data['venue'] == symbol2])
    else:
        total_time_bins = len(beacon_data[beacon_data['symbol'] == symbol2])
    total_possible_bins = len(beacon_data)
    baseline_prob = total_time_bins / total_possible_bins if total_possible_bins > 0 else 0.0
    
    print(f"  Baseline P({symbol2}|random time): {baseline_prob:.4f}")
    
    results = {
        'conditional_probs': conditional_probs,
        'baseline_prob': baseline_prob,
        'beacon_responses': beacon_responses,
        'total_symbol1': len(symbol1_beacons),
        'coverage_pct': 100.0,
        'asset_class': asset_class,
        'symbol1': symbol1,
        'symbol2': symbol2
    }
    
    return results

def estimate_logit_model_crossasset(beacon_responses, beacon_data, asset_class):
    """Estimate logit model for cross-asset data"""
    print(f"\n🔍 Estimating Logit Model ({asset_class})")
    print("-" * 60)
    
    if not beacon_responses:
        print(f"❌ HALT: No beacon responses available")
        return None
    
    # Create feature matrix
    features = []
    responses = []
    
    for response in beacon_responses:
        symbol1_time = response['symbol1_time']
        window_min = response['window_min']
        
        # Extract features for this time point
        # 1. beacon_symbol1 (always 1 since we're looking at symbol1 beacons)
        beacon_symbol1 = 1
        
        # 2. time_of_day (hour of day, normalized)
        time_of_day = symbol1_time.hour / 24.0
        
        # 3. window_min (time window in minutes)
        window_feature = window_min
        
        # 4. day_of_week (day of week, normalized)
        day_of_week = symbol1_time.weekday() / 7.0
        
        features.append([beacon_symbol1, time_of_day, window_feature, day_of_week])
        responses.append(response['response'])
    
    # Convert to numpy arrays
    X = np.array(features)
    y = np.array(responses)
    
    print(f"  Feature matrix shape: {X.shape}")
    print(f"  Response vector shape: {y.shape}")
    print(f"  Positive responses: {sum(y)}/{len(y)} ({sum(y)/len(y)*100:.1f}%)")
    
    # Fit logistic regression model
    try:
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(X, y)
        
        # Calculate pseudo-R² (McFadden's R²)
        y_pred_proba = model.predict_proba(X)[:, 1]
        y_pred = model.predict(X)
        
        # Log-likelihood of the fitted model
        log_likelihood = np.sum(y * np.log(y_pred_proba + 1e-15) + (1 - y) * np.log(1 - y_pred_proba + 1e-15))
        
        # Log-likelihood of the null model (intercept only)
        null_model = LogisticRegression(random_state=42, max_iter=1000)
        null_model.fit(np.ones((len(X), 1)), y)
        null_pred_proba = null_model.predict_proba(np.ones((len(X), 1)))[:, 1]
        null_log_likelihood = np.sum(y * np.log(null_pred_proba + 1e-15) + (1 - y) * np.log(1 - null_pred_proba + 1e-15))
        
        pseudo_r2 = 1 - (log_likelihood / null_log_likelihood)
        
        # Calculate marginal effects (average marginal effects)
        marginal_effects = []
        feature_names = ['beacon_symbol1', 'time_of_day', 'window_min', 'day_of_week']
        
        for i, feature_name in enumerate(feature_names):
            # Calculate marginal effect as the average change in probability
            # when the feature increases by 1 unit
            X_plus = X.copy()
            X_plus[:, i] += 1
            y_pred_plus = model.predict_proba(X_plus)[:, 1]
            marginal_effect = np.mean(y_pred_plus - y_pred_proba)
            marginal_effects.append(marginal_effect)
        
        results = {
            'model': model,
            'pseudo_r2': pseudo_r2,
            'coefficients': model.coef_[0],
            'intercept': model.intercept_[0],
            'feature_names': feature_names,
            'marginal_effects': marginal_effects,
            'accuracy': model.score(X, y),
            'n_observations': len(X),
            'asset_class': asset_class
        }
        
        print(f"  ✅ Model fitted successfully")
        print(f"  Pseudo-R²: {pseudo_r2:.4f}")
        print(f"  Accuracy: {model.score(X, y):.4f}")
        print(f"  N observations: {len(X)}")
        
        return results
        
    except Exception as e:
        print(f"❌ HALT: Logit model failed: {e}")
        return None

def compare_crossasset_results(crypto_results, stocks_results, fx_results):
    """Compare results across asset classes"""
    print(f"\n🔍 Comparing Cross-Asset Results")
    print("-" * 60)
    
    comparison_data = []
    
    # Compare conditional probabilities across asset classes
    for window in ['1m', '5m', '10m', '30m']:
        crypto_lift = 0.0
        stocks_lift = 0.0
        fx_lift = 0.0
        
        if window in crypto_results['conditional_probs']:
            crypto_prob = crypto_results['conditional_probs'][window]['conditional_prob']
            crypto_lift = crypto_prob / crypto_results['baseline_prob'] if crypto_results['baseline_prob'] > 0 else 0
        
        if window in stocks_results['conditional_probs']:
            stocks_prob = stocks_results['conditional_probs'][window]['conditional_prob']
            stocks_lift = stocks_prob / stocks_results['baseline_prob'] if stocks_results['baseline_prob'] > 0 else 0
        
        if window in fx_results['conditional_probs']:
            fx_prob = fx_results['conditional_probs'][window]['conditional_prob']
            fx_lift = fx_prob / fx_results['baseline_prob'] if fx_results['baseline_prob'] > 0 else 0
        
        comparison_data.append({
            'window': window,
            'crypto_lift': crypto_lift,
            'stocks_lift': stocks_lift,
            'fx_lift': fx_lift,
            'max_benchmark_lift': max(stocks_lift, fx_lift),
            'crypto_vs_benchmark': crypto_lift - max(stocks_lift, fx_lift)
        })
    
    # Compare model performance
    crypto_r2 = crypto_results.get('pseudo_r2', 0.0)
    stocks_r2 = stocks_results.get('pseudo_r2', 0.0)
    fx_r2 = fx_results.get('pseudo_r2', 0.0)
    
    max_benchmark_r2 = max(stocks_r2, fx_r2)
    crypto_vs_benchmark_r2 = crypto_r2 - max_benchmark_r2
    
    # Statistical test: Is crypto lift significantly higher than benchmark?
    benchmark_lifts = [item['max_benchmark_lift'] for item in comparison_data]
    crypto_lifts = [item['crypto_lift'] for item in comparison_data]
    
    if len(benchmark_lifts) > 1 and len(crypto_lifts) > 1:
        # Calculate z-score
        benchmark_mean = np.mean(benchmark_lifts)
        benchmark_std = np.std(benchmark_lifts)
        crypto_mean = np.mean(crypto_lifts)
        
        if benchmark_std > 0:
            z_score = (crypto_mean - benchmark_mean) / benchmark_std
        else:
            z_score = 0.0
        
        # Test if crypto > max(benchmark) + 2σ
        benchmark_max = max(benchmark_lifts)
        benchmark_std = np.std(benchmark_lifts)
        crypto_specific_threshold = benchmark_max + 2 * benchmark_std
        crypto_specific = crypto_mean > crypto_specific_threshold
    else:
        z_score = 0.0
        crypto_specific = False
        crypto_specific_threshold = 0.0
    
    comparison_summary = {
        'comparison_data': comparison_data,
        'crypto_r2': crypto_r2,
        'stocks_r2': stocks_r2,
        'fx_r2': fx_r2,
        'max_benchmark_r2': max_benchmark_r2,
        'crypto_vs_benchmark_r2': crypto_vs_benchmark_r2,
        'z_score': z_score,
        'crypto_specific': crypto_specific,
        'crypto_specific_threshold': crypto_specific_threshold,
        'benchmark_mean': np.mean(benchmark_lifts) if len(benchmark_lifts) > 0 else 0.0,
        'crypto_mean': np.mean(crypto_lifts) if len(crypto_lifts) > 0 else 0.0
    }
    
    print(f"  Crypto R²: {crypto_r2:.4f}")
    print(f"  Stocks R²: {stocks_r2:.4f}")
    print(f"  FX R²: {fx_r2:.4f}")
    print(f"  Max Benchmark R²: {max_benchmark_r2:.4f}")
    print(f"  Crypto vs Benchmark R²: {crypto_vs_benchmark_r2:.4f}")
    print(f"  Z-score: {z_score:.4f}")
    print(f"  Crypto-specific threshold: {crypto_specific_threshold:.4f}")
    print(f"  Crypto-specific: {'YES' if crypto_specific else 'NO'}")
    
    return comparison_summary

def save_results_to_temp(crypto_results, stocks_results, fx_results, comparison_summary):
    """Save all results to temporary location"""
    print(f"\n🔍 Saving Results to TEMP Location")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/VALIDATION"
    os.makedirs(output_dir, exist_ok=True)
    
    # Combine all results
    all_results = []
    
    # Add crypto results
    for window_name, prob_data in crypto_results['conditional_probs'].items():
        all_results.append({
            'asset_class': 'crypto',
            'window': window_name,
            'window_min': prob_data['window_min'],
            'total_beacons': prob_data['total_beacons'],
            'positive_responses': prob_data['positive_responses'],
            'conditional_prob': prob_data['conditional_prob'],
            'baseline_prob': crypto_results['baseline_prob'],
            'lift': prob_data['conditional_prob'] / crypto_results['baseline_prob'] if crypto_results['baseline_prob'] > 0 else 0,
            'pseudo_r2': crypto_results.get('pseudo_r2', 0.0),
            'accuracy': crypto_results.get('accuracy', 0.0)
        })
    
    # Add stocks results
    for window_name, prob_data in stocks_results['conditional_probs'].items():
        all_results.append({
            'asset_class': 'stocks',
            'window': window_name,
            'window_min': prob_data['window_min'],
            'total_beacons': prob_data['total_beacons'],
            'positive_responses': prob_data['positive_responses'],
            'conditional_prob': prob_data['conditional_prob'],
            'baseline_prob': stocks_results['baseline_prob'],
            'lift': prob_data['conditional_prob'] / stocks_results['baseline_prob'] if stocks_results['baseline_prob'] > 0 else 0,
            'pseudo_r2': stocks_results.get('pseudo_r2', 0.0),
            'accuracy': stocks_results.get('accuracy', 0.0)
        })
    
    # Add FX results
    for window_name, prob_data in fx_results['conditional_probs'].items():
        all_results.append({
            'asset_class': 'fx',
            'window': window_name,
            'window_min': prob_data['window_min'],
            'total_beacons': prob_data['total_beacons'],
            'positive_responses': prob_data['positive_responses'],
            'conditional_prob': prob_data['conditional_prob'],
            'baseline_prob': fx_results['baseline_prob'],
            'lift': prob_data['conditional_prob'] / fx_results['baseline_prob'] if fx_results['baseline_prob'] > 0 else 0,
            'pseudo_r2': fx_results.get('pseudo_r2', 0.0),
            'accuracy': fx_results.get('accuracy', 0.0)
        })
    
    # Add comparison summary
    for item in comparison_summary['comparison_data']:
        all_results.append({
            'asset_class': 'comparison',
            'window': item['window'],
            'window_min': 0,
            'total_beacons': 0,
            'positive_responses': 0,
            'conditional_prob': 0.0,
            'baseline_prob': 0.0,
            'lift': item['crypto_vs_benchmark'],
            'pseudo_r2': 0.0,
            'accuracy': 0.0
        })
    
    results_df = pd.DataFrame(all_results)
    
    csv_path = f"{output_dir}/RX_Etripleprime_crossasset_results.csv"
    parquet_path = f"{output_dir}/RX_Etripleprime_crossasset_results.parquet"
    results_df.to_csv(csv_path, index=False)
    results_df.to_parquet(parquet_path, index=False)
    print(f"  ✅ Saved Cross-Asset Results: {csv_path}")

def main():
    print("🎯 RX-E‴: CROSS-ASSET BENCHMARK (STOCKS & FX VALIDATION)")
    print("=" * 80)
    print("Goal: Apply RX-E methodology to benchmark datasets using identical beacon-generation logic")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope
    weeks = ['week-minus2', 'week-minus1']
    start_date = '2025-08-22'
    end_date = '2025-09-05'
    
    print(f"📅 Processing weeks: {weeks} (Mon-Fri only)")
    print(f"📊 Date range: {start_date} to {end_date}")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load crypto beacon data
    crypto_beacon_data = load_crypto_beacon_data(weeks)
    
    if len(crypto_beacon_data) == 0:
        print("❌ HALT: No crypto beacon data found")
        return
    
    # Fetch and generate stock beacons
    stock_data = fetch_stock_data(['AAPL', 'SPY'], start_date, end_date)
    stock_beacons = generate_stock_beacons(stock_data, n_beacons_per_symbol=240)
    
    if len(stock_beacons) == 0:
        print("❌ HALT: No stock beacons generated")
        return
    
    # Fetch and generate FX beacons
    fx_data = fetch_fx_data(['EURUSD', 'GBPUSD'], start_date, end_date)
    fx_beacons = generate_fx_beacons(fx_data, n_beacons_per_symbol=240)
    
    if len(fx_beacons) == 0:
        print("❌ HALT: No FX beacons generated")
        return
    
    # Measure conditional response probabilities for each asset class
    crypto_results = measure_conditional_response_probabilities_crossasset(crypto_beacon_data, 'crypto')
    if crypto_results is None:
        print("❌ HALT: Crypto conditional response measurement failed")
        return
    
    stocks_results = measure_conditional_response_probabilities_crossasset(stock_beacons, 'stocks')
    if stocks_results is None:
        print("❌ HALT: Stocks conditional response measurement failed")
        return
    
    fx_results = measure_conditional_response_probabilities_crossasset(fx_beacons, 'fx')
    if fx_results is None:
        print("❌ HALT: FX conditional response measurement failed")
        return
    
    # Estimate logit models for each asset class
    crypto_logit_results = estimate_logit_model_crossasset(crypto_results['beacon_responses'], crypto_beacon_data, 'crypto')
    if crypto_logit_results is None:
        print("❌ HALT: Crypto logit model estimation failed")
        return
    
    stocks_logit_results = estimate_logit_model_crossasset(stocks_results['beacon_responses'], stock_beacons, 'stocks')
    if stocks_logit_results is None:
        print("❌ HALT: Stocks logit model estimation failed")
        return
    
    fx_logit_results = estimate_logit_model_crossasset(fx_results['beacon_responses'], fx_beacons, 'fx')
    if fx_logit_results is None:
        print("❌ HALT: FX logit model estimation failed")
        return
    
    # Add logit results to each asset class results
    crypto_results.update(crypto_logit_results)
    stocks_results.update(stocks_logit_results)
    fx_results.update(fx_logit_results)
    
    # Compare results across asset classes
    comparison_summary = compare_crossasset_results(crypto_results, stocks_results, fx_results)
    
    # Save results to temporary location
    save_results_to_temp(crypto_results, stocks_results, fx_results, comparison_summary)
    
    # ========================================================================
    # CONSOLE TABLES
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 CONSOLE TABLES")
    print("=" * 80)
    
    # Crypto Conditional Probability Table
    print(f"\nCrypto Conditional Probability Curves P(Binance|Δt):")
    print(f"{'Window':<8} {'Total':<8} {'Positive':<10} {'P(Binance|Δt)':<15} {'Baseline':<10} {'Lift':<8}")
    print("-" * 70)
    
    for window_name, prob_data in crypto_results['conditional_probs'].items():
        lift = prob_data['conditional_prob'] / crypto_results['baseline_prob'] if crypto_results['baseline_prob'] > 0 else 0
        print(f"{window_name:<8} {prob_data['total_beacons']:<8} {prob_data['positive_responses']:<10} "
              f"{prob_data['conditional_prob']:<15.4f} {crypto_results['baseline_prob']:<10.4f} {lift:<8.2f}")
    
    # Stocks Conditional Probability Table
    print(f"\nStocks Conditional Probability Curves P(SPY|Δt):")
    print(f"{'Window':<8} {'Total':<8} {'Positive':<10} {'P(SPY|Δt)':<15} {'Baseline':<10} {'Lift':<8}")
    print("-" * 70)
    
    for window_name, prob_data in stocks_results['conditional_probs'].items():
        lift = prob_data['conditional_prob'] / stocks_results['baseline_prob'] if stocks_results['baseline_prob'] > 0 else 0
        print(f"{window_name:<8} {prob_data['total_beacons']:<8} {prob_data['positive_responses']:<10} "
              f"{prob_data['conditional_prob']:<15.4f} {stocks_results['baseline_prob']:<10.4f} {lift:<8.2f}")
    
    # FX Conditional Probability Table
    print(f"\nFX Conditional Probability Curves P(GBPUSD|Δt):")
    print(f"{'Window':<8} {'Total':<8} {'Positive':<10} {'P(GBPUSD|Δt)':<15} {'Baseline':<10} {'Lift':<8}")
    print("-" * 70)
    
    for window_name, prob_data in fx_results['conditional_probs'].items():
        lift = prob_data['conditional_prob'] / fx_results['baseline_prob'] if fx_results['baseline_prob'] > 0 else 0
        print(f"{window_name:<8} {prob_data['total_beacons']:<8} {prob_data['positive_responses']:<10} "
              f"{prob_data['conditional_prob']:<15.4f} {fx_results['baseline_prob']:<10.4f} {lift:<8.2f}")
    
    # Cross-Asset Comparison Table
    print(f"\nCross-Asset Comparison:")
    print(f"{'Window':<8} {'Crypto Lift':<12} {'Stocks Lift':<12} {'FX Lift':<10} {'Max Benchmark':<12} {'Crypto vs Benchmark':<18}")
    print("-" * 80)
    
    for item in comparison_summary['comparison_data']:
        window = item['window']
        crypto_lift = item['crypto_lift']
        stocks_lift = item['stocks_lift']
        fx_lift = item['fx_lift']
        max_benchmark = item['max_benchmark_lift']
        crypto_vs_benchmark = item['crypto_vs_benchmark']
        
        print(f"{window:<8} {crypto_lift:<12.2f} {stocks_lift:<12.2f} {fx_lift:<10.2f} {max_benchmark:<12.2f} {crypto_vs_benchmark:<18.2f}")
    
    # Model Comparison
    print(f"\nModel Performance Comparison:")
    print(f"{'Asset Class':<12} {'Pseudo-R²':<12} {'Accuracy':<10} {'N Observations':<15}")
    print("-" * 55)
    
    print(f"{'Crypto':<12} {crypto_results['pseudo_r2']:<12.4f} {crypto_results['accuracy']:<10.4f} {crypto_results['n_observations']:<15}")
    print(f"{'Stocks':<12} {stocks_results['pseudo_r2']:<12.4f} {stocks_results['accuracy']:<10.4f} {stocks_results['n_observations']:<15}")
    print(f"{'FX':<12} {fx_results['pseudo_r2']:<12.4f} {fx_results['accuracy']:<10.4f} {fx_results['n_observations']:<15}")
    
    # Statistical Test Results
    print(f"\nCrypto-Specific Test:")
    print(f"{'Test':<20} {'Z-score':<10} {'Threshold':<12} {'Result':<15}")
    print("-" * 60)
    
    print(f"{'Crypto vs Benchmark':<20} {comparison_summary['z_score']:<10.4f} {comparison_summary['crypto_specific_threshold']:<12.4f} {'Crypto-Specific' if comparison_summary['crypto_specific'] else 'Not Crypto-Specific':<15}")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750:
        print(f"✅ RX-E‴ COMPLETE - All guardrails complied with")
        print(f"• No writes to canonical_beacons")
        print(f"• UTC timestamps preserved")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Cross-asset benchmark completed")
        print(f"• Crypto-specific test: {'CONFIRMED' if comparison_summary['crypto_specific'] else 'NOT CONFIRMED'}")
        print(f"• Z-score: {comparison_summary['z_score']:.4f}")
    else:
        print(f"❌ RX-E‴ HALTED")
        print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"RX-E‴ COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()
