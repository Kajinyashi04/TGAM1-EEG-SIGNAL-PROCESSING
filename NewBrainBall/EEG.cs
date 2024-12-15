using System;
using System.IO.Ports;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using MathNet.Numerics;
using MathNet.Numerics.IntegralTransforms;
using MathNet.Filtering.Butterworth;
using LiveCharts;
using LiveCharts.Wpf;
using System.Windows;

namespace EEGAnalysis
{
    class ThinkGear
    {
        private SerialPort _serialPort;
        public Dictionary<string, int> Data { get; private set; }

        public ThinkGear(string portName, int baudRate = 57600)
        {
            _serialPort = new SerialPort(portName, baudRate);
            _serialPort.Open();
            Data = new Dictionary<string, int>();
        }

        public void FetchData()
        {
            Data.Clear();

            while (true)
            {
                byte[] syncBytes = new byte[2];
                _serialPort.Read(syncBytes, 0, 2);

                if (syncBytes[0] == 0xAA && syncBytes[1] == 0xAA)
                {
                    int payloadLength = _serialPort.ReadByte();
                    byte[] payload = new byte[payloadLength];
                    _serialPort.Read(payload, 0, payloadLength);

                    int checksum = payload.Sum(b => b) & 0xFF;
                    checksum = ~checksum & 0xFF;

                    int receivedChecksum = _serialPort.ReadByte();
                    if (checksum == receivedChecksum)
                    {
                        ParsePayload(payload);
                        break;
                    }
                    else
                    {
                        Console.WriteLine("ERROR: Checksum mismatch!");
                    }
                }
            }
        }

        private void ParsePayload(byte[] payload)
        {
            for (int i = 0; i < payload.Length; i++)
            {
                if (payload[i] == 0x80) // EEG raw value
                {
                    int msb = payload[++i];
                    int lsb = payload[++i];
                    int rawValue = (msb << 8) | lsb;
                    if (rawValue > 32768) rawValue -= 65536;
                    Data["eeg_raw"] = rawValue;
                }
            }
        }

        public void Close()
        {
            _serialPort.Close();
        }
    }

    class Program
    {
        const int BUFFER_SIZE = 512;
        const int SAMPLING_RATE = 512;

        static readonly Dictionary<string, (double, double)> FrequencyBands = new()
        {
            { "Delta", (0.5, 4) },
            { "Theta", (4, 8) },
            { "Alpha", (8, 12) },
            { "Beta", (12, 30) },
            { "Gamma", (30, 50) }
        };

        static void Main(string[] args)
        {
            ThinkGear eegDevice = new ThinkGear("COM9");
            var eegBuffer = new Queue<double>(new double[BUFFER_SIZE]);
            var timestamps = new Queue<double>(new double[BUFFER_SIZE]);
            double startTime = DateTime.Now.Subtract(DateTime.MinValue.AddYears(1969)).TotalSeconds;

            using StreamWriter csvWriter = new StreamWriter("eeg_data_with_fft.csv");
            csvWriter.WriteLine("Time (s),EEG Raw Value,Delta,Theta,Alpha,Beta,Gamma");

            Butterworth bandpassFilter = new Butterworth();

            try
            {
                while (true)
                {
                    eegDevice.FetchData();
                    if (eegDevice.Data.ContainsKey("eeg_raw"))
                    {
                        double currentTime = DateTime.Now.Subtract(DateTime.MinValue.AddYears(1969)).TotalSeconds - startTime;
                        double rawValue = eegDevice.Data["eeg_raw"];

                        if (eegBuffer.Count == BUFFER_SIZE) eegBuffer.Dequeue();
                        eegBuffer.Enqueue(rawValue);
                        
                        if (timestamps.Count == BUFFER_SIZE) timestamps.Dequeue();
                        timestamps.Enqueue(currentTime);

                        if (eegBuffer.Count == BUFFER_SIZE)
                        {
                            double[] rawSignal = eegBuffer.ToArray();
                            double[] filteredSignal = bandpassFilter.Filter(rawSignal, 0.5 / (SAMPLING_RATE / 2), 50 / (SAMPLING_RATE / 2));

                            Complex[] fftResult = filteredSignal.Select(val => new Complex(val, 0)).ToArray();
                            Fourier.Forward(fftResult, FourierOptions.NoScaling);

                            double[] powerSpectrum = fftResult.Take(BUFFER_SIZE / 2).Select(c => c.Magnitude * c.Magnitude).ToArray();
                            double[] frequencies = Enumerable.Range(0, BUFFER_SIZE / 2).Select(i => i * SAMPLING_RATE / BUFFER_SIZE).ToArray();

                            Dictionary<string, double> powerBands = FrequencyBands.ToDictionary(
                                band => band.Key,
                                band => frequencies
                                    .Where(f => f >= band.Value.Item1 && f < band.Value.Item2)
                                    .Sum(f => powerSpectrum[Array.IndexOf(frequencies, f)])
                            );

                            csvWriter.WriteLine($"{currentTime},{rawValue},{powerBands["Delta"]},{powerBands["Theta"]},{powerBands["Alpha"]},{powerBands["Beta"]},{powerBands["Gamma"]}");
                            
                            Console.Clear();
                            Console.WriteLine("EEG Raw Value: " + rawValue);
                            foreach (var band in powerBands)
                                Console.WriteLine($"{band.Key}: {band.Value}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error: " + ex.Message);
            }
            finally
            {
                eegDevice.Close();
            }
        }
    }
}
