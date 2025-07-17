#!/usr/bin/env python3
"""
ONVIF Camera Control Example
Demonstrates basic ONVIF operations including device discovery,
media profile management, and PTZ control.

Requirements:
pip install onvif-zeep
"""

from onvif import ONVIFCamera
import time
import sys

class ONVIFController:
    def __init__(self, ip, port, username, password):
        """
        Initialize ONVIF camera connection

        Args:
            ip (str): Camera IP address
            port (int): ONVIF port (usually 80 or 8080)
            username (str): Camera username
            password (str): Camera password
        """
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.camera = None
        self.media_service = None
        self.ptz_service = None
        self.profiles = []

    def connect(self):
        """Establish connection to ONVIF camera"""
        try:
            # Create ONVIF camera object
            self.camera = ONVIFCamera(
                self.ip,
                self.port,
                self.username,
                self.password
            )

            # Get media service
            self.media_service = self.camera.create_media_service()

            # Get PTZ service (if available)
            try:
                self.ptz_service = self.camera.create_ptz_service()
            except Exception as e:
                print(f"PTZ service not available: {e}")

            print(f"Successfully connected to camera at {self.ip}:{self.port}")
            return True

        except Exception as e:
            print(f"Failed to connect to camera: {e}")
            return False

    def get_device_info(self):
        """Get basic device information"""
        try:
            device_service = self.camera.create_devicemgmt_service()
            device_info = device_service.GetDeviceInformation()

            print("\n=== Device Information ===")
            print(f"Manufacturer: {device_info.Manufacturer}")
            print(f"Model: {device_info.Model}")
            print(f"Firmware Version: {device_info.FirmwareVersion}")
            print(f"Serial Number: {device_info.SerialNumber}")
            print(f"Hardware ID: {device_info.HardwareId}")

            return device_info

        except Exception as e:
            print(f"Error getting device info: {e}")
            return None

    def get_capabilities(self):
        """Get device capabilities"""
        try:
            device_service = self.camera.create_devicemgmt_service()
            capabilities = device_service.GetCapabilities()

            print("\n=== Device Capabilities ===")
            if hasattr(capabilities, 'Media') and capabilities.Media:
                print(f"Media Service: {capabilities.Media.XAddr}")
            if hasattr(capabilities, 'PTZ') and capabilities.PTZ:
                print(f"PTZ Service: {capabilities.PTZ.XAddr}")
            if hasattr(capabilities, 'Events') and capabilities.Events:
                print(f"Events Service: {capabilities.Events.XAddr}")

            return capabilities

        except Exception as e:
            print(f"Error getting capabilities: {e}")
            return None

    def get_profiles(self):
        """Get available media profiles"""
        try:
            self.profiles = self.media_service.GetProfiles()

            print("\n=== Media Profiles ===")
            for i, profile in enumerate(self.profiles):
                print(f"Profile {i+1}:")
                print(f"  Name: {profile.Name}")
                print(f"  Token: {profile.token}")

                # Video configuration
                if hasattr(profile, 'VideoEncoderConfiguration') and profile.VideoEncoderConfiguration:
                    video_config = profile.VideoEncoderConfiguration
                    print(f"  Video Encoding: {video_config.Encoding}")
                    print(f"  Resolution: {video_config.Resolution.Width}x{video_config.Resolution.Height}")
                    print(f"  Frame Rate: {video_config.RateControl.FrameRateLimit}")
                    print(f"  Bitrate: {video_config.RateControl.BitrateLimit}")

                # Audio configuration
                if hasattr(profile, 'AudioEncoderConfiguration') and profile.AudioEncoderConfiguration:
                    audio_config = profile.AudioEncoderConfiguration
                    print(f"  Audio Encoding: {audio_config.Encoding}")
                    print(f"  Sample Rate: {audio_config.SampleRate}")

                print()

            return self.profiles

        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []

    def get_stream_uri(self, profile_index=0):
        """Get RTSP stream URI for a profile"""
        try:
            if not self.profiles:
                self.get_profiles()

            if profile_index >= len(self.profiles):
                print(f"Profile index {profile_index} out of range")
                return None

            profile = self.profiles[profile_index]

            # Create stream setup request
            request = self.media_service.create_type('GetStreamUri')
            request.ProfileToken = profile.token
            request.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }

            response = self.media_service.GetStreamUri(request)
            stream_uri = response.Uri

            print(f"\n=== Stream URI ===")
            print(f"Profile: {profile.Name}")
            print(f"Stream URI: {stream_uri}")

            return stream_uri

        except Exception as e:
            print(f"Error getting stream URI: {e}")
            return None

    def ptz_control(self, pan=0, tilt=0, zoom=0, profile_index=0):
        """Control PTZ (Pan/Tilt/Zoom) if available"""
        if not self.ptz_service:
            print("PTZ service not available")
            return False

        try:
            if not self.profiles:
                self.get_profiles()

            if profile_index >= len(self.profiles):
                print(f"Profile index {profile_index} out of range")
                return False

            profile = self.profiles[profile_index]

            # Create PTZ request
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = profile.token
            request.Velocity = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }

            # Start PTZ movement
            self.ptz_service.ContinuousMove(request)
            print(f"PTZ command sent: Pan={pan}, Tilt={tilt}, Zoom={zoom}")

            # Stop after 2 seconds
            time.sleep(2)
            stop_request = self.ptz_service.create_type('Stop')
            stop_request.ProfileToken = profile.token
            self.ptz_service.Stop(stop_request)
            print("PTZ movement stopped")

            return True

        except Exception as e:
            print(f"Error controlling PTZ: {e}")
            return False

    def get_ptz_presets(self, profile_index=0):
        """Get available PTZ presets"""
        if not self.ptz_service:
            print("PTZ service not available")
            return []

        try:
            if not self.profiles:
                self.get_profiles()

            if profile_index >= len(self.profiles):
                print(f"Profile index {profile_index} out of range")
                return []

            profile = self.profiles[profile_index]

            request = self.ptz_service.create_type('GetPresets')
            request.ProfileToken = profile.token

            presets = self.ptz_service.GetPresets(request)

            print("\n=== PTZ Presets ===")
            for preset in presets:
                print(f"Preset: {preset.Name} (Token: {preset.token})")

            return presets

        except Exception as e:
            print(f"Error getting PTZ presets: {e}")
            return []

    def go_to_preset(self, preset_token, profile_index=0):
        """Move to a specific PTZ preset"""
        if not self.ptz_service:
            print("PTZ service not available")
            return False

        try:
            if not self.profiles:
                self.get_profiles()

            profile = self.profiles[profile_index]

            request = self.ptz_service.create_type('GotoPreset')
            request.ProfileToken = profile.token
            request.PresetToken = preset_token

            self.ptz_service.GotoPreset(request)
            print(f"Moving to preset: {preset_token}")

            return True

        except Exception as e:
            print(f"Error going to preset: {e}")
            return False


def main():
    """Example usage"""
    # Camera configuration
    CAMERA_IP = "192.168.0.252"  # Replace with your camera IP
    CAMERA_PORT = 2020           # Replace with your camera port
    USERNAME = "username"        # Replace with your username
    PASSWORD = "password"        # Replace with your password

    # Create ONVIF controller
    controller = ONVIFController(CAMERA_IP, CAMERA_PORT, USERNAME, PASSWORD)

    # Connect to camera
    if not controller.connect():
        print("Failed to connect to camera")
        sys.exit(1)

    # Get device information
    controller.get_device_info()

    # Get capabilities
    controller.get_capabilities()

    # Get media profiles
    controller.get_profiles()

    # Get stream URI
    stream_uri = controller.get_stream_uri()
    if stream_uri:
        print(f"\nYou can view the stream using VLC or similar: {stream_uri}")

    # PTZ operations (if available)
    controller.get_ptz_presets()

    # Example PTZ movement (pan right slowly)
    print("\nTesting PTZ movement...")
    controller.ptz_control(pan=0.5, tilt=0, zoom=0)

    print("\nONVIF operations completed successfully!")


if __name__ == "__main__":
    main()
