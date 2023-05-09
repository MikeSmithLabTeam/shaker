import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_surface(x, y, cost):
    fig = plt.figure(1)
    ax = fig.add_subplot(projection='3d')
    ax.scatter(x, y, cost, marker='o')
    


def generate_xy(x0, y0, noise=1):
    """Whilst the true COM value of system is (x0,y0). Noise
    means the measured value differs ==> (x,y)"""
    x=x0+np.random.normal(loc=0.0, scale=noise, size=10)
    y=y0+np.random.normal(loc=0.0, scale=noise, size=10)
    return x,y

def cost(xc, yc, x, y):
    """The measured cost"""
    return np.sum(((xc-x)**2 + (yc-y)**2)**0.5)/np.size(x)

def noise_toobig_dxdy(xvals, yvals, xc, yc):
    """Check that the measurement of the displacement of centres is meaningful 
    relative to noise"""
    if ~np.any(xvals):
        return True
    
    x_av = np.mean(xvals)
    y_av = np.mean(yvals)
    dx_noise = np.std(xvals)
    dy_noise = np.std(yvals)

    if cost(xc, yc, x_av, y_av) > (dx_noise**2 + dy_noise**2):
        return False
    else:
        return True
    

def adjust_motors(xc, yc, xvals, yvals, x_0, y_0, weight):
    """Move motors to move x nearer to xc etc. x_0, y_0 is motor position"""
    xav = np.mean(xvals)
    yav = np.mean(yvals)

    dx = weight*(xc-xav)
    dy = weight*(yc-yav)
    return x_0+dx, y_0+dy



if __name__ == '__main__':
    
    xc = -1
    yc = 9

    x0, y0 = 100, 200

    x0_vals = []
    y0_vals = []
    cost_vals = []
    
    min_dist = 0.001

    for i in range(100):
        print(i)
        xvals=np.array([])
        yvals=np.array([])
        while noise_toobig_dxdy(xvals, yvals, xc, yc):
            x,y=generate_xy(x0, y0)
            xvals = np.append(xvals, x)
            yvals = np.append(yvals, y)
            x0, y0=adjust_motors(xc, yc, xvals, yvals, x0, y0, 0.1)
            x0_vals.append(x0)
            y0_vals.append(y0)
            cost_vals.append(cost(xc,yc,x0,y0))
            print(x0-xc)
            
            if cost_vals[-1] < min_dist:
                break
        
        print(x0_vals[-1])
        print(y0_vals[-1])
        print(cost_vals[-1])
        if cost_vals[-1] < min_dist:
                break
        plot_surface(x0_vals, y0_vals, cost_vals)
    plt.show()    
    




    