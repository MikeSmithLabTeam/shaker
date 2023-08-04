import numpy as np
import matplotlib.pyplot as plt

'''
This script loads in acceleration data, calculates the mean and st. deviation and plots as a function of duty cycle.
Also compares measured data to data from James's thesis.
Plots measued data, James's data, James's data * sqrt(2)
'''


#load in acc data + duty cycles
acc_1 = np.loadtxt("shaker_acc_calibration/acceleration_data1.txt", dtype=float)
acc_2 = np.loadtxt("shaker_acc_calibration/acceleration_data2.txt", dtype=float)
acc_3 = np.loadtxt("shaker_acc_calibration/acceleration_data3.txt", dtype=float)
acc_4 = np.loadtxt("shaker_acc_calibration/acceleration_data4.txt", dtype=float)
acc_5 = np.loadtxt("shaker_acc_calibration/acceleration_data5.txt", dtype=float)
duty_cycle = np.loadtxt("shaker_acc_calibration/duty_cycle_data.txt", dtype=float)

#stack data columns
acc_data = np.stack((acc_1, acc_2, acc_3, acc_4, acc_5), axis=1)
mean_acc_data = np.mean(acc_data, axis=1)   #calc mean
std_acc_data = np.std(acc_data, axis=1)     #calc st dev

j_acc = np.array([0.15, 0.3, 0.55, 1.3, 2.3, 3.5, 4.2, 4.8])    #data taken from James thesis
j_duty = np.array([20,30,40,50,60,70,80,90])

duty_cycle = duty_cycle / 10    #converting to percentage

#plotting
fig, ax = plt.figure(1), plt.axes()
ax.errorbar(duty_cycle, mean_acc_data, yerr=std_acc_data,fmt=".", ecolor="b", capsize=5, label="Measured data") #errorbar plot.

ax.plot(j_duty, j_acc, linestyle="-", marker=".", color="r", label="James's Thesis data")      #plot of James's data
ax.plot(j_duty, np.sqrt(2)*j_acc, linestyle="-", marker=".", color="k", label="James's Thesis data x sqrt(2)")     #plot of James's data * root (2) 

ax.set_xlabel("Duty Cycle")
ax.set_ylabel("Peak z-acceleration ($\Gamma$)")
plt.xticks()
plt.yticks()
ax.legend()
ax.grid()
plt.show()
