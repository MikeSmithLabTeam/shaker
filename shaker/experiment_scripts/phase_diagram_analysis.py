import numpy as np
import matplotlib.pyplot as plt
import filehandling

path="videos/08_03_area_f_0.6235/"

def order_mid(ydata):
    '''
    Calculates the middle of the global order parameter data
    '''
    global_order_mid = (max(ydata)-min(ydata)) / 2 + min(ydata)
    return global_order_mid

#load in acc data + duty cycles + counts 
data1 = np.loadtxt(path+"data_1.txt", dtype=float)
data2 = np.loadtxt(path+"data_2.txt", dtype=float)
data3 = np.loadtxt(path+"data_3.txt", dtype=float)
#data4 = np.loadtxt(path+"data_4.txt", dtype=float)
#data5 = np.loadtxt(path+"data_5.txt", dtype=float)

acc_1 = np.loadtxt(path+"acceleration_data_1.txt", dtype=float)
acc_2 = np.loadtxt(path+"acceleration_data_2.txt", dtype=float)
acc_3 = np.loadtxt(path+"acceleration_data_3.txt", dtype=float)
#acc_4 = np.loadtxt(path+"acceleration_data_4.txt", dtype=float)
#acc_5 = np.loadtxt(path+"acceleration_data_5.txt", dtype=float)

#stack data columns
order_data = np.stack((data1[:,0], data2[:,0], data3[:,0]), axis=1)
acc_data = np.stack((acc_1, acc_2, acc_3), axis=1)
duty_data = np.stack((data1[:,1], data2[:,1], data3[:,1]), axis=1)

#calc mean and std
mean_order = np.mean(order_data, axis=1)
std_order = np.std(order_data, axis=1)
mean_duty = np.mean(duty_data, axis=1)
std_duty = np.std(duty_data, axis=1)
mean_acc = np.mean(acc_data, axis=1)
std_acc = np.std(acc_data, axis=1)

#plotting
fig, (ax1) = plt.subplots(1,1, figsize=(12,8), sharey=False)
ax1.errorbar(mean_acc[1:], mean_order[1:], yerr=std_order[1:], fmt="b^", ecolor="k", capsize=1, label="data")
ax1.set_xlabel("Acceleration $\Gamma$", fontsize=20)
ax1.set_ylabel("|$\Psi_6$|", fontsize=20)

midpoint_order = order_mid(mean_order[1:])

fit_xdata = ax1.lines[0].get_xdata()    #find x data of fit
fit_ydata = ax1.lines[0].get_ydata()    #find y data of fit 
x_interp = round(np.interp(midpoint_order, fit_ydata, fit_xdata), 4)    #interpolate points to find $\Gamma$ at avg global order param.
ax1.plot(x_interp, midpoint_order, "go", label="$\Gamma$ at avg $|\Psi_6|$")

print("$\Gamma$=", x_interp)
print("midpoint of order= ", midpoint_order)
data = np.vstack((mean_order,std_order, mean_acc,std_acc)) #stack global order params and acc data
np.savetxt("order_acc_0.6235.txt", data)    #save .txt file of orders and acc

plt.xticks(fontsize=18)
plt.yticks(fontsize=18)
plt.legend()
plt.show()

