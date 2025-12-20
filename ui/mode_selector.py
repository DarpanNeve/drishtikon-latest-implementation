def get_user_mode(priority_audio):
    priority_audio.request_play(
        "Say 1 for reading, 2 for object detection, 3 for navigation",
        AudioPriority.SYSTEM
    )
    # temporary: keyboard input
    return input("Enter mode (1/2/3): ").strip()
