import pandas as pd
import numpy as np

print('Generating 50,000 row dataset...')
np.random.seed(42)
rows = 50000

df = pd.DataFrame({
    'Sample_ID': range(1, rows + 1),
    'Engine_RPM': np.random.normal(5000, 100, rows),
    'Fuel_Flow': np.random.normal(1200, 50, rows),
    'Turbine_Temp': np.random.normal(850, 15, rows),
    'Oil_Pressure': np.random.normal(45, 2, rows),
    'Vibration_Amplitude': np.random.normal(0.02, 0.005, rows)
})

# Inject some anomalies
anomaly_indices = np.random.choice(rows, 1000, replace=False)
df.loc[anomaly_indices, 'Engine_RPM'] *= 1.2
df.loc[anomaly_indices, 'Turbine_Temp'] *= 1.1

df.to_csv('e:\\AEIA\\sample_data\\benchmark_50k.csv', index=False)
print('Saved to sample_data/benchmark_50k.csv')
