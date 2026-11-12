"""Input discovery shared by the recorder and the training GUI."""


def input_devices(query_devices=None) -> list[dict]:
    if query_devices is None:
        import sounddevice

        query_devices = sounddevice.query_devices
    return [
        {"id": index, "name": device["name"],
         "channels": int(device["max_input_channels"]),
         "sample_rate": int(device["default_samplerate"])}
        for index, device in enumerate(query_devices())
        if device["max_input_channels"] > 0
    ]
