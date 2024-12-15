import serial
import time
import matplotlib.pyplot as plt
import numpy as np
import csv
from collections import deque
from scipy.fft import fft
from scipy.signal import butter, lfilter

class ThinkGear:
    def __init__(self, port, baudrate=57600):
        self.ser = serial.Serial(port, baudrate)
        self.data = {}

    def fetch_data(self):
        self.data = {}
        while True:
            self.ser.read_until(b'\xaa\xaa')
            payload = []
            checksum = 0
            packet_length = self.ser.read(1)
            payload_length = packet_length[0]
            for i in range(payload_length):
                packet_code = self.ser.read(1)
                tempPacket = packet_code[0]
                payload.append(packet_code)
                checksum += tempPacket
            checksum = ~checksum & 0xff
            check = self.ser.read(1)
            if checksum == check[0]:
                break
            else:
                print('ERROR: Checksum mismatch!')

        i = 0
        while i < payload_length:
            packet = payload[i]
            if packet == b'\x80':  # EEG raw value
                i += 1
                i += 1
                val0 = payload[i]
                i += 1
                val1 = payload[i]
                raw_value = val0[0] * 256 + val1[0]
                if raw_value > 32768:
                    raw_value -= 65536
                self.data['eeg_raw'] = raw_value
            else:
                pass
            i += 1

    def close(self):
        self.ser.close()

def bandpass_filter(data, lowcut, highcut, fs, order=5):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, data)

# Initialize the ThinkGear device
eeg_device = ThinkGear('COM9')

# Configuration
BUFFER_SIZE = 512  # Increased buffer size for better frequency resolution
SAMPLING_RATE = 512  # Sampling rate in Hz

# Buffers for EEG data
eeg_buffer = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
timestamps = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Brainwave frequency bands (in Hz)
FREQ_BANDS = {
    "Delta": (0.5, 4),
    "Theta": (4, 8),
    "Alpha": (8, 12),
    "Beta": (12, 30),
    "Gamma": (30, 50)
}

# Prepare for visualization
plt.ion()  # Interactive mode on
fig, (ax_raw, ax_fft) = plt.subplots(2, 1, figsize=(10, 8))

start_time = time.time()

# Open a CSV file to write the data
with open('eeg_data_with_fft.csv', mode='w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['Time (s)', 'EEG Raw Value', 'Delta', 'Theta', 'Alpha', 'Beta', 'Gamma'])

    try:
        while True:
            eeg_device.fetch_data()
            data = eeg_device.data

            if 'eeg_raw' in data:
                # Append raw data to buffer
                current_time = time.time() - start_time
                eeg_buffer.append(data['eeg_raw'])
                timestamps.append(current_time)

                # Perform FFT when buffer is full
                if len(eeg_buffer) == BUFFER_SIZE:
                    raw_signal = np.array(eeg_buffer)

                    # Apply bandpass filter to clean the signal
                    filtered_signal = bandpass_filter(raw_signal, 0.5, 50, SAMPLING_RATE)

                    # Normalize FFT result
                    fft_result = np.abs(fft(filtered_signal))[:BUFFER_SIZE // 2] / BUFFER_SIZE
                    freqs = np.fft.fftfreq(BUFFER_SIZE, d=1 / SAMPLING_RATE)[:BUFFER_SIZE // 2]

                    # Calculate power in each frequency band
                    power_bands = {band: 0 for band in FREQ_BANDS}
                    for band, (low, high) in FREQ_BANDS.items():
                        indices = np.where((freqs >= low) & (freqs < high))
                        power_bands[band] = np.sum(fft_result[indices] ** 2)  # Square the amplitude

                    # Write data to CSV
                    csv_writer.writerow([
                        current_time, data['eeg_raw'], power_bands['Delta'], power_bands['Theta'],
                        power_bands['Alpha'], power_bands['Beta'], power_bands['Gamma']
                    ])

                    # Update plots
                    ax_raw.clear()
                    ax_raw.plot(timestamps, eeg_buffer, label='EEG Raw Value')
                    ax_raw.set_ylim(-300, 300)
                    ax_raw.set_xlabel('Time (seconds)')
                    ax_raw.set_ylabel('EEG Raw Value')
                    ax_raw.set_title('Real-Time EEG Data')
                    ax_raw.legend()

                    ax_fft.clear()
                    ax_fft.bar(power_bands.keys(), power_bands.values(), color=['blue', 'green', 'orange', 'red', 'purple'])
                    ax_fft.set_ylim(0, max(power_bands.values()) * 1.2)  # Scale y-axis
                    ax_fft.set_xlabel('Frequency Bands')
                    ax_fft.set_ylabel('Power')
                    ax_fft.set_title('Brainwave Frequency Analysis')

                    plt.pause(0.01)  # Pause to update the plot

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        eeg_device.close()
        plt.ioff()  # Turn off interactive mode
        plt.show()  # Show the final plot
