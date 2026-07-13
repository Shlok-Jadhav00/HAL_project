import json
import os

filepath = r'e:\AEIA\gui\analysis_panel.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to load settings inside run()
settings_load_code = '''
            settings_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config', 'settings.json'
            )
            settings = {}
            if os.path.exists(settings_path):
                import json
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            det_cfg = settings.get('detection', {})
            stat_cfg = settings.get('statistics', {})
'''

# Find insertion point
insert_idx = content.find('            df = self.session_data')
content = content[:insert_idx] + settings_load_code + '\n' + content[insert_idx:]

# Update compute_statistics call
stat_call = '''            stats = compute_statistics(
                df_clean, measurement_types,
                correlation_threshold=stat_cfg.get('correlation_threshold', 0.7),
                trend_window_fraction=stat_cfg.get('trend_window_fraction_of_dataset', 0.1),
                trend_window_min=stat_cfg.get('trend_window_min_samples', 3),
                trend_window_max=stat_cfg.get('trend_window_max_samples', 20),
                trend_stability_multiplier=stat_cfg.get('trend_stability_std_multiplier', 0.5),
                trend_minimum_slope_magnitude=stat_cfg.get('trend_minimum_slope_magnitude', 0.01)
            )'''
content = content.replace('            stats = compute_statistics(df_clean, measurement_types)', stat_call)

# Update detect_anomalies call
anom_call = '''            anomalies = detect_anomalies(
                df_clean, measurement_types,
                zscore_threshold=det_cfg.get('zscore_threshold', 3.0),
                iqr_multiplier=det_cfg.get('iqr_multiplier', 1.5),
                if_contamination=det_cfg.get('isolation_forest_contamination', 0.05),
                if_n_estimators=det_cfg.get('isolation_forest_n_estimators', 100),
                if_random_state=det_cfg.get('isolation_forest_random_state', 42)
            )'''
content = content.replace('            anomalies = detect_anomalies(df_clean, measurement_types)', anom_call)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated gui/analysis_panel.py')
