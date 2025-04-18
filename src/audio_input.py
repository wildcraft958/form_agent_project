import pyaudio

class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        # Auto-detect input device
        input_device_index = None
        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:
                input_device_index = i
                break
        
        if input_device_index is None:
            raise Exception("No audio input devices found")

        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            input_device_index=input_device_index
        )
