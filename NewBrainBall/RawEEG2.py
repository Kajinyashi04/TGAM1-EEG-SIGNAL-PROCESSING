import serial
import time
import matplotlib.pyplot as plt
import numpy as np
import csv

class ThinkGear:
    def __init__(self, port, baudrate=57600):
        self.ser = serial.Serial(port, baudrate)
        self.data = {}

    def fetch_data(self):
        self.data = {}  # Reset values
        while True:
            self.ser.read_until(b'\xaa\xaa')  # Wait for sync bytes
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
            if packet == b'\x80':  # Raw EEG value
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

# Initialize the ThinkGear device
eeg_device = ThinkGear('COM9')

# Prepare for visualization
plt.ion()  # Interactive mode on
fig, ax = plt.subplots()
xdata = []
ydata = []
start_time = time.time()

# Open a CSV file to write the data
with open('eeg_data.csv', mode='w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['Time (s)', 'EEG Raw Value'])  # Write header

    try:
        while True:
            eeg_device.fetch_data()
            data = eeg_device.data

            if 'eeg_raw' in data:
                current_time = time.time() - start_time
                xdata.append(current_time)
                ydata.append(data['eeg_raw'])

                # Write the time and EEG raw value to the CSV file
                csv_writer.writerow([current_time, data['eeg_raw']])

                # Update the plot
                ax.clear()
                ax.plot(xdata, ydata, label='EEG Raw Value')
                ax.set_ylim(-200, 200)  # Set y-axis limits based on expected EEG values
                ax.set_xlabel('Time (seconds)')
                ax.set_ylabel('EEG Raw Value')
                ax.set_title('Real-time EEG Data')
                ax.legend()
                plt.pause(0.01)  # Pause to update the plot

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        eeg_device.close()
        plt.ioff()  # Turn off interactive mode
        plt.show()  # Show the final plot