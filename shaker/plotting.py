import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from matplotlib import gridspec
from matplotlib.image import imread
import cv2
from IPython.display import display, clear_output


def draw_img_axes(img):
    """Draws x and y axes on an image."""
    # Draw axes
    sz = np.shape(img)
    img = cv2.arrowedLine(img, (int(
        0.05*sz[1]), int(0.95*sz[0])), (int(0.25*sz[1]), int(0.95*sz[0])), (0, 0, 255), 3)
    img = cv2.arrowedLine(img, (int(
        0.05*sz[1]), int(0.95*sz[0])), (int(0.05*sz[1]), int(0.75*sz[0])), (0, 0, 255), 3)
    img = cv2.putText(img, "X", (int(
        0.275*sz[1]), int(0.95*sz[0])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    img = cv2.putText(img, "Y", (int(
        0.05*sz[1]), int(0.725*sz[0])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return img

def update_plot(fig, ax, track_levelling):
    x = range(len(track_levelling))
    ax.errorbar(x[-1], track_levelling[-1][-2], yerr=track_levelling[-1][-1],
                        fmt='o', ecolor='black', elinewidth=1, markerfacecolor='red', markeredgecolor='black')
    ax.set_title('Levelling progress plot')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Cost')
    display(fig)
    clear_output(wait=True)


def plot_levelling(folder, tracking_filename, img_filename):
    """Takes a track_levelling file and plots the data in 2D and 3D. The first three columns of the file are assumed to be x, y, and z coordinates. The first subplot is a scatter plot of the z coordinates against the row number. The second subplot is a 3D surface plot of the x, y, and z coordinates.
    folder should end in a /
    """
    track_levelling = np.loadtxt(folder + tracking_filename, delimiter=',')

    # Create the figure and 2D subplots
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 2])
    fig = plt.figure(figsize=(8, 8))
    ax0 = plt.subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])#, projection='3d')

    # Convert the first three columns of track_levelling to a numpy array
    data = np.array(track_levelling)

    # Split the data into x, y, and z components
    x_motor = data[:, 0]
    y_motor = data[:, 1]
    cost = data[:, 2]
    fluctuations = data[:, 3]

    # Create a scatter plot in the upper subplot
    ax0.errorbar(np.arange(0, np.size(cost)), cost, yerr=fluctuations, fmt='o',
                 ecolor='black', elinewidth=1, markerfacecolor='red', markeredgecolor='black')
    ax0.set_title('Progress of levelling')
    ax0.set_xlabel('Step number')
    ax0.set_ylabel('Cost')

    # Create a grid of x and y values
    xi = np.linspace(min(x_motor), max(x_motor), 10000)
    yi = np.linspace(min(y_motor), max(y_motor), 10000)
    xi, yi = np.meshgrid(xi, yi)
    # Interpolate z values on this grid
    cost_i = griddata((x_motor, y_motor), cost, (xi, yi), method='cubic')
    
    # Find the indices of the minimum value in the interpolated grid
    min_indices = np.unravel_index(np.argmin(cost_i), cost_i.shape)

    # Use these indices to find the corresponding values in xi and yi
    xi_min = xi[min_indices]
    yi_min = yi[min_indices]

    print(f"The motor values that would give the minimum value of the cost are {xi_min} and {yi_min}, respectively.")

    # Create a contour plot
    # change cmap to any colormap you like
    contour = ax1.contourf(xi, yi, cost_i, cmap='viridis')
    fig.colorbar(contour, ax=ax1, orientation='vertical')



    # Plot the original data points on top of the contour plot
    ax1.scatter(x_motor, y_motor, color='r', edgecolor='k', marker='o',s=5)
    ax1.scatter(xi_min, yi_min, color='b',edgecolor='k', marker='o', s=10)

    ax1.set_title('Levelling progress plot')
    ax1.set_xlabel('X_motor')
    ax1.set_ylabel('Y_motor')

    fig2, ax_img = plt.subplots()

    img = imread(folder + img_filename)
    ax_img.imshow(img)

    # display(fig)
    # clear_output(wait=True)
    plt.show()
