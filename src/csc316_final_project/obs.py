import obsws_python as obs

class OBSBridge:
    def __init__(self, host='localhost', port=4455, password='password', record_every_n=5):
        self.client = obs.ReqClient(host=host, port=port, password=password)
        self.record_every_n = record_every_n
    
    def start_record(self, episode_num=None):
        if episode_num is not None and (episode_num+1) % self.record_every_n == 0 and not self.is_recording:
            self.client.start_record()
    
    def stop_record(self):
        if self.is_recording:
            self.client.stop_record()
    
    @property
    def get_record_directory(self):
        settings = self.client.get_record_directory()
        return settings.record_directory
    
    @property
    def status(self):
        try:
            status = self.client.get_record_status()
            if status.output_active:
                return 1 # recording
            else:
                return 2 # not recording
        except Exception:
            return 3 # not connected
    
    @property
    def is_recording(self):
        status = self.client.get_record_status()
        return status.output_active

