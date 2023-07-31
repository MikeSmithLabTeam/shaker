import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import moviepy.editor as mp
from scipy.io.wavfile import read as wavread


def magnitude_hexatic(dataframe,framenumber):
    '''
    Extracts the hexatic order from a pandas dataframe.
    Calculates the magnitude of the order.

    Inputs:
    dataframe : pandas dataframe 

    Outputs : 
    order : array of magnitudes of heaxtic_order param
    '''
    framedata = dataframe.loc[[framenumber]]
    mag_hexatic = framedata[["hexatic_order_abs"]]
    
    return mag_hexatic

def video_to_duty(video_file_path):
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
    clip = mp.VideoFileClip(video_file_path)
    clip.audio.write_audiofile("audio_out.wav") #write audio file from .MP4
    rate, data = wavread("audio_out.wav")   #read audio file
    audio_array = data[:,0] #discard channel information
    
    ft = np.abs(np.fft.fft(audio_array, n=len(audio_array))) #fourier transform audio signal
    freq = np.fft.fftfreq(len(audio_array), 1/rate)
    peak = int(abs(freq[np.argmax(ft)]))    #find peak freq.
    duty = (peak - 1000) / 15   #duty cycle conversion
    return duty


path = "videos/2023_07_27_pm/set_2/"
framenumber = 2
data_filename_1 = path+"19950023.hdf5"
data_filename_2 = path+"19950029.hdf5"
data_filename_3 = path+"19950036.hdf5"
data_filename_4 = path+"19950044.hdf5"

video_file_1 = path+"19950023.MP4"
video_file_2 = path+"19950029.MP4"
video_file_3 = path+"19950036.MP4"
video_file_4 = path+"19950044.MP4"

data_frame_1 = pd.read_hdf(data_filename_1) #read in .hdf5 file
data_frame_2 = pd.read_hdf(data_filename_2)
data_frame_3 = pd.read_hdf(data_filename_3)
data_frame_4 = pd.read_hdf(data_filename_4)

data_frame_1.index.name='index' 
data_frame_2.index.name="index"
data_frame_3.index.name="index"
data_frame_4.index.name="index"

duty_1 = video_to_duty(video_file_1) /10   #calc duty from audio freq
duty_2 = video_to_duty(video_file_2) /10
duty_3 = video_to_duty(video_file_3) /10
duty_4 = video_to_duty(video_file_4) /10

order_1 = magnitude_hexatic(data_frame_1, framenumber)  #extract magnitude of hexatic order param from dataframe
order_2 = magnitude_hexatic(data_frame_2, framenumber)
order_3 = magnitude_hexatic(data_frame_3, framenumber)
order_4 = magnitude_hexatic(data_frame_4, framenumber)

fig, ((ax1,ax2),(ax3,ax4)) = plt.subplots(2,2, sharey=True)    #plot distributions of 3 selected videos

ax1.set_title("Distribution of |$\Psi_6$|")
ax1.hist(order_1, bins=100)
ax1.set_ylabel("Count")
ax1.text(0,225,"Duty Cycle:{:10.1f}".format(duty_1)+"%")

ax2.hist(order_2, bins=100)
ax2.text(0,225,"Duty Cycle:{:10.1f}".format(duty_2)+"%")

ax3.hist(order_3, bins=100)
ax3.set_xlabel("|$\Psi_6$|")
ax3.set_ylabel("Count")
ax3.text(0,225,"Duty Cycle:{:10.1f}".format(duty_3)+"%")

ax4.hist(order_4, bins=100)
ax4.set_xlabel("|$\Psi_6$|")
ax4.text(0,225,"Duty Cycle:{:10.1f}".format(duty_4)+"%")

plt.show()
