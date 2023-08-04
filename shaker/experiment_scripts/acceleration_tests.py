import numpy as np
import matplotlib.pyplot as plt

duty = np.array([400,450,500,550,600,650,700,300,350,400,450,600,650,700,700,750,750,800,800])
peak_z = np.array([0.9,1.4,1.97,2.63,3.33,4.04,4.72,0.37,0.62,0.92,1.42,3.33,4.02,4.72,4.7,5.34,5.36,5.89,5.88])
peak_z_calc = np.array([0.71,1.16,1.85,2.44,3.41,3.97,4.54,0.170,0.256,0.738,1.36,3.12,3.97,4.49,4.49,5.00,5.05,5.56,5.56])
y = 0.0128 * duty - 4.5

fig, (ax) = plt.subplots()
ax.plot(duty, peak_z, "r^", label="RPi Pico")
ax.plot(duty, peak_z_calc, "bo", label="Amplitude")
ax.plot(duty, y, "k-", label="trendline")
ax.set_xlabel("Duty Cycle")
ax.set_ylabel("Dimensionless acceleration ($\Gamma$)")
ax.legend()
ax.grid()
plt.show()


'''
Measurements with both the RPi Pico accelerometer and using the amplitude measurement tool both yield consistent results.
Suggests \Gamma~4 accurate for phase transition measurement.
'''