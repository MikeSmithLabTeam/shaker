import filehandling
import numpy as np
import pandas as pd
import os
from tqdm import tqdm
import matplotlib.pyplot as plt
import moviepy.editor as mp
from scipy.io.wavfile import read as wavread


def hexatic(dataframe,framenumber):
    '''
    Extracts the hexatic order from a pandas dataframe.
    Calculates the magnitude of the order.

    Inputs:
    dataframe : pandas dataframe 

    Outputs : 
    order : array of magnitudes of heaxtic_order param
    '''
    framedata = dataframe.loc[[framenumber]]
    hexatic = framedata[["hexatic_order_abs"]]
    return hexatic

def particle_number(dataframe, framenumber):
    '''
    Extracts the number of particles from a pandas dataframe.
    Inputs:
    dataframe : pandas dataframe 

    Outputs : 
    order : number of particles
    '''
    framedata = dataframe.loc[[framenumber]]
    particles = framedata[["particle"]]
    particle_num = np.max(particles)
    return particle_num

def video_to_duty(video_filepath):
    '''
    Returns duty cycle from audio of .MP4 file
    Extracts audio information from .MP4 file using scipy.io.wavfile and stores
    audio information in a numpy array.
    Extracts duty cycle information from a numpy array of audio information.
    Input:
    video_file_path : a file path to an .MP4 file
    
    Returns:
    duty : duty cycle (as a percentage)

    '''
    clip = mp.VideoFileClip(video_filepath)
    clip.audio.write_audiofile("audio_out.wav") #write audio file from .MP4
    rate, data = wavread("audio_out.wav")   #read audio file
    audio_array = data[:,0] #discard channel information
    
    ft = np.abs(np.fft.fft(audio_array, n=len(audio_array))) #fourier transform audio signal
    freq = np.fft.fftfreq(len(audio_array), 1/rate)
    peak = abs(freq[np.argmax(ft)])    #find peak freq.
    #peak = int(abs(freq[np.argmax(ft)]))    #find peak freq.
    duty = (peak - 1000) / 15   #duty cycle conversion
    return duty

if __name__ == '__main__':

    path = "videos/2023_07_28_hysteresis/rate_2/set_1h/" #create file directory and select files
    acc_file = "acceleration_data_1h.txt"
    data_file = "data_1h.txt"

    directory = filehandling.open_directory(path)
    files = filehandling.get_directory_filenames(directory+"/*.hdf5")
    acceleration_data = np.loadtxt(path+acc_file, dtype=float)    #load in acc data

    dutys = []  #initalise empty arrays and params
    global_orders = []
    area_fractions = []
    framenumber = 0
    PARTICLE_PIXEL = 1197
    TRAY_PIXEL_SIZE = 3741194

    if True:
        for file in tqdm(files):
            #asign filename and filepath
            filename = os.path.splitext(os.path.split(file)[1])[0]
            filepath = path+filename+".hdf5"
            dataframe = pd.read_hdf(filepath)   #read .hdf5 file
            
            dataframe.index.name='index'    #set dataframe index to "index"

            order = hexatic(dataframe, framenumber)   #extract mag of hexatic order param from dataframe
            global_order = np.mean(order)   #calc global order param (mean of local param)
            global_orders.append(global_order)    #append to array
            
            duty = video_to_duty(path+filename+".MP4")  #calculate duty from freq of audio signal
            dutys.append(duty)          #append to array

            particles = particle_number(dataframe, framenumber) #find number of particles
            area_fraction = (particles * PARTICLE_PIXEL) / TRAY_PIXEL_SIZE   #calculate area fraction of particles
            area_fractions.append(area_fraction)
            
        global_orders = np.transpose(np.array([global_orders]))   #create columns of data in numpy arrays
        dutys = np.transpose(np.array([dutys]))
        area_fractions = np.transpose(np.array([area_fractions]))

        data = np.hstack((global_orders,dutys, area_fractions)) #stack global order params and duty data
        np.savetxt(path+data_file, data)    #save .txt file of counts and duty
    '''
        fig, (ax1,ax2) = plt.subplots(2,1, sharey=False)    #plotting
        ax1.plot(dutys, global_orders, ".")
        ax1.set_xlabel("Duty Cycle, %")
        ax1.set_ylabel("|$\Psi_6$|")

        ax2.plot(acceleration_data[1:], global_orders[1:], ".")
        ax2.set_xlabel("$\Gamma$")
        ax2.set_ylabel("|$\Psi_6$|")
        plt.show()
    '''