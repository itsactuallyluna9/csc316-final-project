import obsws_python as obs

class OBSBridge:
    def __init__(self, host='localhost', port=4455, password='password'):
        self.client = obs.ReqClient(host=host, port=port, password=password)
    
    def start_record(self):
        self.client.start_record()
    
    def stop_record(self):
        self.client.stop_record()
    
    @property
    def get_record_directory(self):
        settings = self.client.get_record_directory()
        return settings.record_directory
    
    @property
    def is_recording(self):
        status = self.client.get_record_status()
        return status.output_active

