#!/usr/bin/env python3
"""
Raspberry Pi Camera RTSP Streamer
Captures video from Pi Camera V2 and streams via RTSP using FFmpeg
Run this on your Raspberry Pi 3
"""

import subprocess
import time
import signal
import sys
from picamera2 import Picamera2
import threading
import logging

# --- Configuration ---
RTSP_PORT = 8554
STREAM_NAME = "stream"
RESOLUTION = (1280, 720)  # 720p for good balance of quality/bandwidth
FRAMERATE = 15  # Lower framerate for Pi 3 performance
BITRATE = "2M"  # 2 Mbps bitrate
GOP_SIZE = 30  # Keyframe interval

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTSPStreamer:
    def __init__(self):
        self.camera = None
        self.ffmpeg_process = None
        self.running = False
        
    def setup_camera(self):
        """Initialize and configure the Pi Camera"""
        try:
            self.camera = Picamera2()
            
            # Configure camera for streaming
            config = self.camera.create_video_configuration(
                main={"size": RESOLUTION, "format": "RGB888"},
                controls={"FrameRate": FRAMERATE}
            )
            self.camera.configure(config)
            
            logger.info(f"✅ Camera configured: {RESOLUTION[0]}x{RESOLUTION[1]} @ {FRAMERATE}fps")
            return True
            
        except Exception as e:
            logger.error(f"❌ Camera setup failed: {e}")
            return False
    
    def start_ffmpeg_rtsp_server(self):
        """Start FFmpeg RTSP server process"""
        try:
            # FFmpeg command to create RTSP server
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{RESOLUTION[0]}x{RESOLUTION[1]}',
                '-r', str(FRAMERATE),
                '-i', '-',  # Read from stdin (pipe)
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Fast encoding for Pi 3
                '-tune', 'zerolatency',  # Low latency
                '-b:v', BITRATE,
                '-g', str(GOP_SIZE),
                '-keyint_min', str(GOP_SIZE),
                '-sc_threshold', '0',
                '-f', 'rtsp',
                f'rtsp://0.0.0.0:{RTSP_PORT}/{STREAM_NAME}'
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"🎥 RTSP server started on port {RTSP_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"❌ FFmpeg RTSP server failed: {e}")
            return False
    
    def stream_frames(self):
        """Capture and stream frames to FFmpeg"""
        try:
            self.camera.start()
            logger.info("📹 Camera streaming started")
            
            frame_count = 0
            start_time = time.time()
            
            while self.running:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Send frame to FFmpeg via pipe
                try:
                    self.ffmpeg_process.stdin.write(frame.tobytes())
                    self.ffmpeg_process.stdin.flush()
                    
                    frame_count += 1
                    
                    # Log stats every 100 frames
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        actual_fps = frame_count / elapsed
                        logger.info(f"📊 Streamed {frame_count} frames, FPS: {actual_fps:.1f}")
                        
                except BrokenPipeError:
                    logger.error("❌ FFmpeg pipe broken")
                    break
                    
                # Small delay to prevent overwhelming the Pi
                time.sleep(1.0 / FRAMERATE)
                
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
        finally:
            if self.camera:
                self.camera.stop()
    
    def start(self):
        """Start the RTSP streaming service"""
        logger.info("🚀 Starting RTSP Camera Streamer...")
        
        # Setup camera
        if not self.setup_camera():
            return False
            
        # Start FFmpeg RTSP server
        if not self.start_ffmpeg_rtsp_server():
            return False
            
        # Get local IP for display
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            logger.info(f"🌐 RTSP Stream URL: rtsp://{local_ip}:{RTSP_PORT}/{STREAM_NAME}")
            logger.info(f"🔗 Connect your YOLO detector to: rtsp://{local_ip}:{RTSP_PORT}/{STREAM_NAME}")
            
        except Exception:
            logger.info(f"🌐 RTSP Stream URL: rtsp://<YOUR_PI_IP>:{RTSP_PORT}/{STREAM_NAME}")
        
        # Start streaming
        self.running = True
        try:
            self.stream_frames()
        except KeyboardInterrupt:
            logger.info("⏹️  Streaming stopped by user")
        finally:
            self.stop()
            
        return True
    
    def stop(self):
        """Stop streaming and cleanup"""
        logger.info("🛑 Stopping RTSP streamer...")
        self.running = False
        
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                logger.info("📷 Camera stopped")
            except Exception as e:
                logger.error(f"Camera stop error: {e}")
        
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
                logger.info("🎬 FFmpeg process terminated")
            except Exception as e:
                logger.error(f"FFmpeg stop error: {e}")
                self.ffmpeg_process.kill()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("🛑 Received interrupt signal")
    sys.exit(0)

def main():
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check dependencies
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ FFmpeg not found! Install with: sudo apt install ffmpeg")
        return False
    
    # Start streamer
    streamer = RTSPStreamer()
    return streamer.start()

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("❌ Failed to start RTSP streamer")
        sys.exit(1)