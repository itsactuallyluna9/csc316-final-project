import obsws_python as obs

client = obs.ReqClient(host="localhost", port="4455", password="password")

def record():
    client.start_record()

def stop():
    client.stop_record()

def directory():
    return client.get_record_directory()





